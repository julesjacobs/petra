//! Predicate-preserving quotient of counters never read by a transition.
use crate::{marking::StoredMarking, model::Problem, search::Outcome, successors::TransitionIndex};
use std::{
    collections::HashMap,
    time::{Duration, Instant},
};

#[derive(Debug, PartialEq, Eq, Hash)]
pub struct Key {
    active: StoredMarking,
    observations: Box<[i128]>,
}

impl Key {
    pub(crate) fn full(marking: &[u64]) -> Self {
        Self {
            active: StoredMarking::new(marking),
            observations: Box::new([]),
        }
    }
}

pub struct Projection {
    active: Vec<usize>,
    passive: Vec<usize>,
    // A finite cap is allowed only for a >= predicate with nonnegative
    // active coefficients and nondecreasing passive contribution.
    rows: Vec<(Vec<i64>, Option<i128>)>,
}
impl Projection {
    pub fn new(p: &Problem) -> Self {
        let mut used = vec![false; p.places.len()];
        for t in &p.transitions {
            for &(i, _) in &t.pre {
                used[i] = true;
            }
        }
        let active = (0..used.len()).filter(|&i| used[i]).collect::<Vec<_>>();
        let passive = (0..used.len()).filter(|&i| !used[i]).collect::<Vec<_>>();
        let mut rows = Vec::new();
        for c in &p.target {
            let coefficients = passive
                .iter()
                .map(|&i| c.coefficients[i])
                .collect::<Vec<_>>();
            if coefficients.iter().all(|&a| a == 0) {
                continue;
            }
            let cap = if !c.equality && c.coefficients.iter().all(|&a| a >= 0) {
                Some(i128::from(c.bound))
            } else {
                None
            };
            let row = (coefficients, cap);
            if !rows.contains(&row) {
                rows.push(row);
            }
        }
        Self {
            active,
            passive,
            rows,
        }
    }
    pub fn key(&self, m: &[u64]) -> Option<Key> {
        let active = StoredMarking::project(m, &self.active);
        let mut observations = Vec::with_capacity(self.rows.len());
        for (coefficients, cap) in &self.rows {
            let value = coefficients
                .iter()
                .zip(&self.passive)
                .try_fold(0i128, |x, (&a, &i)| {
                    x.checked_add(i128::from(a) * i128::from(m[i]))
                })?;
            observations.push(cap.map_or(value, |b| value.min(b)));
        }
        Some(Key {
            active,
            observations: observations.into_boxed_slice(),
        })
    }
}

pub fn solve(p: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    let start = Instant::now();
    let projection = Projection::new(p);
    let index = TransitionIndex::new(p);
    let Some(key) = projection.key(&p.initial) else {
        return Outcome::unknown("quotient-bfs", "projection overflow", 0);
    };
    let mut ids = HashMap::from([(key, 0usize)]);
    let mut nodes = vec![(StoredMarking::new(&p.initial), None::<(usize, usize)>)];
    let mut marking = vec![0; p.places.len()];
    let mut candidates = Vec::new();
    let mut head = 0;
    while head < nodes.len() {
        if start.elapsed() >= timeout {
            return Outcome::unknown("quotient-bfs", "time limit", nodes.len());
        }
        nodes[head].0.write_to(&mut marking);
        let accepts = match p.accepts(&marking) {
            Ok(accepts) => accepts,
            Err(e) => return Outcome::unknown("quotient-bfs", &e.to_string(), nodes.len()),
        };
        if accepts {
            let mut trace = vec![];
            let mut i = head;
            while let Some((parent, t)) = nodes[i].1 {
                trace.push(t);
                i = parent;
            }
            trace.reverse();
            if let Ok(marking) = p.check_witness(&trace) {
                return Outcome {
                    verdict: "reachable",
                    method: "quotient-bfs".into(),
                    reason: "replayed witness from sink-counter quotient".into(),
                    states: nodes.len(),
                    trace,
                    marking: Some(marking),
                    certificate: None,
                    proof: None,
                };
            }
            return Outcome::unknown("quotient-bfs", "replay failed", nodes.len());
        }
        index.candidates(&marking, &mut candidates);
        for (candidate, &t) in candidates.iter().enumerate() {
            if candidate % 256 == 0 && start.elapsed() >= timeout {
                return Outcome::unknown("quotient-bfs", "time limit", nodes.len());
            }
            let m = match p.fire(&marking, t) {
                Ok(Some(m)) => m,
                Ok(None) => continue,
                Err(_) => return Outcome::unknown("quotient-bfs", "counter overflow", nodes.len()),
            };
            let Some(key) = projection.key(&m) else {
                return Outcome::unknown("quotient-bfs", "projection overflow", nodes.len());
            };
            if ids.contains_key(&key) {
                continue;
            }
            if nodes.len() >= max_states {
                return Outcome::unknown("quotient-bfs", "state limit", nodes.len());
            }
            ids.insert(key, nodes.len());
            nodes.push((StoredMarking::new(&m), Some((head, t))));
        }
        head += 1;
    }
    // Keep negative answers behind the proof-producing portfolio engines until
    // the standalone checker supports quotient closure certificates.
    Outcome::unknown(
        "quotient-bfs",
        "quotient exhausted; no exported closure proof",
        nodes.len(),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Constraint, Transition};
    fn net() -> Problem {
        Problem {
            places: vec!["p".into(), "a".into(), "b".into()],
            initial: vec![1, 0, 0],
            transitions: vec![Transition {
                name: "t".into(),
                pre: vec![(0, 1)],
                post: vec![(0, 1), (1, 1)],
            }],
            target: vec![Constraint {
                coefficients: vec![0, 1, -1],
                bound: 1,
                equality: false,
            }],
        }
    }
    #[test]
    fn differences_not_individual_counts() {
        let p = net();
        let q = Projection::new(&p);
        assert_eq!(q.key(&[1, 4, 3]), q.key(&[1, 2, 1]));
        assert_ne!(q.key(&[1, 4, 3]), q.key(&[1, 4, 2]));
    }
    #[test]
    fn cap_only_monotone_predicates() {
        let mut p = net();
        p.target[0].coefficients = vec![0, 1, 0];
        let q = Projection::new(&p);
        assert_eq!(q.key(&[1, 4, 0]), q.key(&[1, 9, 0]));
        p.target[0].equality = true;
        let q = Projection::new(&p);
        assert_ne!(q.key(&[1, 4, 0]), q.key(&[1, 9, 0]));
        p.target[0].equality = false;
        p.target[0].coefficients[0] = -1;
        let q = Projection::new(&p);
        assert_ne!(q.key(&[1, 4, 0]), q.key(&[1, 9, 0]));
    }
    #[test]
    fn witnesses_replay() {
        let p = net();
        let result = solve(&p, Duration::from_secs(1), 100);
        assert_eq!(result.verdict, "reachable");
        p.check_witness(&result.trace).unwrap();
    }
    #[test]
    fn compact_keys_preserve_dense_key_equivalence_and_overflow() {
        use std::collections::HashSet;
        let mut seed = 41u64;
        let mut next = || {
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            seed >> 32
        };
        for case in 0..128 {
            let n = 1 + case % 12;
            let mut p = Problem {
                places: (0..n).map(|i| format!("p{i}")).collect(),
                initial: vec![0; n],
                transitions: vec![],
                target: vec![],
            };
            for i in 0..n {
                if next() % 3 == 0 {
                    p.transitions.push(Transition {
                        name: format!("read{i}"),
                        pre: vec![(i, 1)],
                        post: vec![],
                    });
                }
            }
            for _ in 0..case % 5 {
                p.target.push(Constraint {
                    coefficients: (0..n)
                        .map(|_| match next() % 8 {
                            0 => i64::MAX,
                            1 => i64::MIN,
                            x => x as i64 - 4,
                        })
                        .collect(),
                    bound: (next() % 5) as i64 - 2,
                    equality: next() % 2 == 0,
                });
            }
            p.validate().unwrap();
            let projection = Projection::new(&p);
            let legacy = |m: &[u64]| -> Option<Vec<i128>> {
                let mut values: Vec<_> = projection
                    .active
                    .iter()
                    .map(|&i| i128::from(m[i]))
                    .collect();
                for (coefficients, cap) in &projection.rows {
                    let value = coefficients
                        .iter()
                        .zip(&projection.passive)
                        .try_fold(0i128, |sum, (&a, &i)| {
                            sum.checked_add(i128::from(a) * i128::from(m[i]))
                        })?;
                    values.push(cap.map_or(value, |b| value.min(b)));
                }
                Some(values)
            };
            let mut old_seen = HashSet::new();
            let mut new_seen = HashSet::new();
            for sample in 0..64 {
                let m: Vec<_> = (0..n)
                    .map(|_| match next() % 8 {
                        0 => u64::MAX,
                        1 => 1,
                        _ => 0,
                    })
                    .collect();
                let old = legacy(&m);
                let new = projection.key(&m);
                assert_eq!(old.is_none(), new.is_none(), "case {case}, sample {sample}");
                if let (Some(old), Some(new)) = (old, new) {
                    let mut active = vec![0; projection.active.len()];
                    new.active.write_to(&mut active);
                    let restored: Vec<_> = active
                        .into_iter()
                        .map(i128::from)
                        .chain(new.observations.iter().copied())
                        .collect();
                    assert_eq!(old, restored);
                    assert_eq!(old_seen.insert(old), new_seen.insert(new));
                }
            }
        }
    }
    fn dense_reachable(p: &Problem) -> bool {
        use std::collections::{HashSet, VecDeque};
        let mut seen = HashSet::from([p.initial.clone()]);
        let mut queue = VecDeque::from([p.initial.clone()]);
        while let Some(m) = queue.pop_front() {
            if p.target.iter().all(|c| {
                let value: i128 = c
                    .coefficients
                    .iter()
                    .zip(&m)
                    .map(|(&a, &x)| i128::from(a) * i128::from(x))
                    .sum();
                if c.equality {
                    value == i128::from(c.bound)
                } else {
                    value >= i128::from(c.bound)
                }
            }) {
                return true;
            }
            for tr in &p.transitions {
                let mut successor = m.clone();
                let mut enabled = true;
                for (place, x) in successor.iter_mut().enumerate() {
                    let pre = tr
                        .pre
                        .iter()
                        .find(|&&(i, _)| i == place)
                        .map_or(0, |&(_, w)| w);
                    let post = tr
                        .post
                        .iter()
                        .find(|&&(i, _)| i == place)
                        .map_or(0, |&(_, w)| w);
                    if *x < pre {
                        enabled = false;
                        break;
                    }
                    *x = *x - pre + post;
                }
                if enabled && seen.insert(successor.clone()) {
                    queue.push_back(successor);
                }
            }
        }
        false
    }

    #[test]
    fn quotient_matches_independent_bounded_search_with_weighted_arcs_and_signed_sinks() {
        let mut seed = 90123u64;
        let mut random = || {
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            seed >> 32
        };
        for case in 0..64 {
            let dimension = if case % 2 == 0 { 80 } else { 6 };
            let mut p = Problem {
                places: (0..dimension).map(|i| format!("p{i}")).collect(),
                initial: vec![0; dimension],
                transitions: vec![],
                target: vec![],
            };
            for _ in 0..3 {
                p.initial[random() as usize % 3] += 1;
            }
            p.initial[3] = 4;
            for t in 0..9 {
                let source = random() as usize % 3;
                let destination = random() as usize % 3;
                let weight = 1 + random() % 2;
                let mut post = vec![(destination, weight)];
                for place in [4, 5] {
                    let n = random() % 3;
                    if n > 0 {
                        post.push((place, n));
                    }
                }
                p.transitions.push(Transition {
                    name: format!("t{t}"),
                    pre: vec![(source, weight), (3, 1 + random() % 2)],
                    post,
                });
            }
            for target in 0..8 {
                let mut coefficients = vec![0; dimension];
                coefficients[4] = 1;
                coefficients[5] = if target % 3 == 0 { 1 } else { -1 };
                p.target = vec![Constraint {
                    coefficients,
                    bound: target - 2,
                    equality: target % 2 == 0,
                }];
                p.validate().unwrap();
                let expected = dense_reachable(&p);
                let result = solve(&p, Duration::from_secs(10), 10_000);
                assert_eq!(
                    result.verdict,
                    if expected { "reachable" } else { "unknown" },
                    "case {case}, target {target}"
                );
                if expected {
                    assert_eq!(
                        p.check_witness(&result.trace).unwrap(),
                        result.marking.unwrap()
                    );
                } else {
                    assert_eq!(
                        result.reason,
                        "quotient exhausted; no exported closure proof"
                    );
                }
            }
        }
    }

    #[test]
    fn source_transitions_and_signed_passive_differences_remain_visible() {
        let mut p = net();
        p.transitions = vec![
            Transition {
                name: "balanced".into(),
                pre: vec![],
                post: vec![(1, 2), (2, 2)],
            },
            Transition {
                name: "positive".into(),
                pre: vec![],
                post: vec![(1, 1)],
            },
        ];
        p.target[0].equality = true;
        p.target[0].bound = 2;
        let result = solve(&p, Duration::from_secs(1), 100);
        assert_eq!(result.verdict, "reachable");
        assert_eq!(result.trace, vec![1, 1]);
        p.check_witness(&result.trace).unwrap();
        p.transitions.pop();
        let result = solve(&p, Duration::from_secs(1), 100);
        assert_eq!(result.verdict, "unknown");
        assert_eq!(result.states, 1);
        assert_eq!(
            result.reason,
            "quotient exhausted; no exported closure proof"
        );
    }

    #[test]
    fn quotient_limits_and_overflows_stay_unknown() {
        let p = net();
        assert_eq!(solve(&p, Duration::ZERO, 100).reason, "time limit");
        assert_eq!(solve(&p, Duration::from_secs(1), 1).reason, "state limit");
        let mut counter = p.clone();
        counter.initial[1] = u64::MAX;
        counter.target[0].bound = 0;
        counter.target[0].equality = true;
        let result = solve(&counter, Duration::from_secs(1), 100);
        assert_eq!(result.verdict, "unknown");
        assert_eq!(result.reason, "counter overflow");
        let mut overflow = p;
        overflow.initial = vec![u64::MAX; 3];
        overflow.target[0].coefficients = vec![i64::MAX; 3];
        overflow.target[0].equality = true;
        let result = solve(&overflow, Duration::from_secs(1), 100);
        assert_eq!(result.verdict, "unknown");
        assert_eq!(result.reason, "projection overflow");
        overflow.transitions.push(Transition {
            name: "read-second".into(),
            pre: vec![(1, 1)],
            post: vec![(1, 1)],
        });
        let result = solve(&overflow, Duration::from_secs(1), 100);
        assert_eq!(result.verdict, "unknown");
        assert_eq!(result.reason, "target arithmetic overflow");
    }
}
