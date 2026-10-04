use crate::{
    marking::StoredMarking,
    model::{Problem, Transition},
    search::Outcome,
    successors::TransitionIndex,
};
use num_bigint::BigInt;
use num_traits::{ToPrimitive, Zero};
use std::{
    cmp::Reverse,
    collections::{BTreeMap, BinaryHeap, HashSet, VecDeque},
    sync::Arc,
    time::{Duration, Instant},
};

#[derive(Clone, Debug, Default, PartialEq, Eq, Hash)]
struct SparseSummary {
    // Sorted coordinates with nonzero hurdle or effect. Read arcs retain hurdles.
    coordinates: Vec<(usize, BigInt, BigInt)>,
}
impl SparseSummary {
    fn transition(t: &Transition) -> Self {
        let mut coordinates = BTreeMap::<usize, (BigInt, BigInt)>::new();
        for &(p, w) in &t.pre {
            let (h, e) = coordinates.entry(p).or_default();
            *h += w;
            *e -= w;
        }
        for &(p, w) in &t.post {
            coordinates.entry(p).or_default().1 += w;
        }
        Self {
            coordinates: coordinates
                .into_iter()
                .filter(|(_, (h, e))| !h.is_zero() || !e.is_zero())
                .map(|(p, (h, e))| (p, h, e))
                .collect(),
        }
    }

    fn then(&self, next: &Self) -> Self {
        let mut left = self.coordinates.iter().peekable();
        let mut right = next.coordinates.iter().peekable();
        let mut coordinates = Vec::new();
        let zero = BigInt::zero();
        while left.peek().is_some() || right.peek().is_some() {
            let p = match (left.peek(), right.peek()) {
                (Some(a), Some(b)) => a.0.min(b.0),
                (Some(a), None) => a.0,
                (None, Some(b)) => b.0,
                (None, None) => unreachable!(),
            };
            let (h, e) = if left.peek().is_some_and(|a| a.0 == p) {
                let (_, h, e) = left.next().unwrap();
                (h, e)
            } else {
                (&zero, &zero)
            };
            let (k, f) = if right.peek().is_some_and(|b| b.0 == p) {
                let (_, k, f) = right.next().unwrap();
                (k, f)
            } else {
                (&zero, &zero)
            };
            let hurdle = h.clone().max(k - e);
            let effect = e + f;
            if !hurdle.is_zero() || !effect.is_zero() {
                coordinates.push((p, hurdle, effect));
            }
        }
        Self { coordinates }
    }
}

struct Region {
    hurdle: Vec<(usize, u64)>,
    bounds: Vec<i128>,
    word: Vec<usize>,
}
impl Region {
    fn new(p: &Problem, s: &SparseSummary, word: Vec<usize>) -> Option<Self> {
        let hurdle = s
            .coordinates
            .iter()
            .filter(|(_, h, _)| !h.is_zero())
            .map(|(p, h, _)| Some((*p, h.to_u64()?)))
            .collect::<Option<Vec<_>>>()?;
        let mut bounds = Vec::new();
        for c in &p.target {
            let effect: BigInt = s
                .coordinates
                .iter()
                .map(|(p, _, e)| e * c.coefficients[*p])
                .sum();
            bounds.push((BigInt::from(c.bound) - effect).to_i128()?);
        }
        Some(Self {
            hurdle,
            bounds,
            word,
        })
    }
    fn distance(&self, targets: &[SparseTarget], m: &[u64]) -> u128 {
        let mut gap = self
            .hurdle
            .iter()
            .map(|&(p, h)| u128::from(h.saturating_sub(m[p])))
            .fold(0u128, u128::saturating_add);
        for (c, &b) in targets.iter().zip(&self.bounds) {
            let Some(value) = c.coefficients.iter().try_fold(0i128, |v, &(p, a)| {
                v.checked_add(i128::from(a) * i128::from(m[p]))
            }) else {
                return u128::MAX;
            };
            let d = b.saturating_sub(value);
            gap = gap.saturating_add(if c.equality {
                d.unsigned_abs()
            } else {
                d.max(0) as u128
            });
        }
        gap
    }
}
struct SparseTarget {
    coefficients: Vec<(usize, i64)>,
    equality: bool,
}
struct Node {
    marking: Arc<StoredMarking>,
    parent: Option<(usize, usize)>,
    depth: usize,
}

/// Beam backward preimages guide forward exploration; every answer is replayed.
pub fn solve(p: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    let start = Instant::now();
    if timeout.is_zero() || max_states == 0 {
        return Outcome::unknown("backward", "resource limit", 0);
    }
    if p.validate().is_err() {
        return Outcome::unknown("backward", "invalid problem", 0);
    }
    let budget = timeout / 5;
    let mut targets = Vec::new();
    for c in &p.target {
        if start.elapsed() >= timeout {
            return Outcome::unknown("backward", "time limit", 0);
        }
        targets.push(SparseTarget {
            coefficients: c
                .coefficients
                .iter()
                .enumerate()
                .filter_map(|(p, &a)| (a != 0).then_some((p, a)))
                .collect(),
            equality: c.equality,
        });
    }
    let identity = SparseSummary::default();
    let mut regions = vec![Region::new(p, &identity, vec![]).unwrap()];
    let mut transitions = Vec::new();
    for t in &p.transitions {
        if start.elapsed() >= budget {
            break;
        }
        transitions.push(SparseSummary::transition(t));
    }
    let mut beam = vec![(identity.clone(), vec![])];
    let mut summaries = HashSet::from([identity]);
    for _ in 0..12 {
        let mut candidates = Vec::new();
        for (summary, word) in &beam {
            for (t, ts) in transitions.iter().enumerate() {
                if start.elapsed() >= budget || summaries.len() >= max_states {
                    break;
                }
                let s = ts.then(summary);
                if !summaries.insert(s.clone()) {
                    continue;
                }
                let mut w = vec![t];
                w.extend_from_slice(word);
                if let Some(r) = Region::new(p, &s, w.clone()) {
                    let distance = r.distance(&targets, &p.initial);
                    let position =
                        candidates.partition_point(|x: &(u128, _, _, _)| x.0 <= distance);
                    if position < 32 {
                        candidates.insert(position, (distance, s, w, r));
                        candidates.truncate(32);
                    }
                }
            }
            if start.elapsed() >= budget {
                break;
            }
        }
        beam.clear();
        for (_, s, w, r) in candidates {
            beam.push((s, w));
            regions.push(r);
        }
        if beam.is_empty() || start.elapsed() >= budget {
            break;
        }
    }
    regions.sort_by_key(|r| (r.distance(&targets, &p.initial), r.word.len()));
    regions.truncate(32);
    drop(beam);
    drop(summaries);
    drop(transitions);
    if start.elapsed() >= timeout {
        return Outcome::unknown("backward", "time limit", 0);
    }
    let index = TransitionIndex::new(p);
    let initial = Arc::new(StoredMarking::new(&p.initial));
    let mut nodes = vec![Node {
        marking: Arc::clone(&initial),
        parent: None,
        depth: 0,
    }];
    let mut seen = HashSet::from([initial]);
    let mut marking = vec![0; p.places.len()];
    let mut successors = Vec::new();
    let mut heap = BinaryHeap::from([Reverse((0u128, 0usize, 0usize))]);
    let mut fifo = VecDeque::from([0usize]);
    let mut expanded = HashSet::new();
    let mut iterations = 0usize;
    loop {
        if start.elapsed() >= timeout {
            return Outcome::unknown("backward", "time limit", nodes.len());
        }
        iterations += 1;
        let next = if iterations.is_multiple_of(16) {
            fifo.pop_front()
        } else {
            heap.pop().map(|Reverse((_, _, id))| id)
        };
        let Some(id) = next else {
            return Outcome::unknown("backward", "frontier exhausted", nodes.len());
        };
        if !expanded.insert(id) {
            continue;
        }
        nodes[id].marking.write_to(&mut marking);
        for r in &regions {
            if start.elapsed() >= timeout {
                return Outcome::unknown("backward", "time limit", nodes.len());
            }
            if r.distance(&targets, &marking) != 0 {
                continue;
            }
            let mut trace = Vec::new();
            let mut back = id;
            while let Some((prev, t)) = nodes[back].parent {
                trace.push(t);
                back = prev;
            }
            trace.reverse();
            trace.extend_from_slice(&r.word);
            if let Ok(marking) = p.check_witness(&trace) {
                return Outcome {
                    verdict: "reachable",
                    method: "backward".into(),
                    reason: "replayed forward prefix and exact backward suffix".into(),
                    states: nodes.len(),
                    trace,
                    marking: Some(marking),
                    certificate: None,
                    proof: None,
                };
            }
        }
        index.candidates(&marking, &mut successors);
        for &t in &successors {
            if start.elapsed() >= timeout {
                return Outcome::unknown("backward", "time limit", nodes.len());
            }
            let Ok(Some(m)) = p.fire(&marking, t) else {
                continue;
            };
            let stored = StoredMarking::new(&m);
            if seen.contains(&stored) {
                continue;
            }
            if nodes.len() >= max_states {
                return Outcome::unknown("backward", "state limit", nodes.len());
            }
            let distance = regions
                .iter()
                .map(|r| r.distance(&targets, &m))
                .min()
                .unwrap_or(u128::MAX);
            let child = nodes.len();
            let depth = nodes[id].depth + 1;
            let stored = Arc::new(stored);
            seen.insert(Arc::clone(&stored));
            nodes.push(Node {
                marking: stored,
                parent: Some((id, t)),
                depth,
            });
            heap.push(Reverse((distance, depth, child)));
            fifo.push_back(child);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{model::Constraint, summary::WordSummary};

    fn dense(s: &SparseSummary, places: usize) -> WordSummary {
        let mut expanded = WordSummary::identity(places);
        assert!(s.coordinates.windows(2).all(|w| w[0].0 < w[1].0));
        for (p, h, e) in &s.coordinates {
            assert!(!h.is_zero() || !e.is_zero());
            expanded.hurdle[*p] = h.clone();
            expanded.effect[*p] = e.clone();
        }
        expanded
    }

    #[test]
    fn sparse_summaries_match_dense_weighted_words() {
        let mut seed = 936719u64;
        let mut next = || {
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            seed >> 32
        };
        for _ in 0..128 {
            let mut sparse = SparseSummary::default();
            let mut expected = WordSummary::identity(7);
            for step in 0..12 {
                let mut arcs = || {
                    (0..7)
                        .filter_map(|p| {
                            let w = next() % 9;
                            (w < 3).then_some((p, w + 1))
                        })
                        .collect()
                };
                let t = Transition {
                    name: "weighted".into(),
                    pre: arcs(),
                    post: arcs(),
                };
                let single = SparseSummary::transition(&t);
                assert_eq!(dense(&single, 7), WordSummary::transition(7, &t));
                if step % 2 == 0 {
                    sparse = single.then(&sparse);
                    expected = WordSummary::transition(7, &t).then(&expected);
                } else {
                    sparse = sparse.then(&single);
                    expected = expected.then(&WordSummary::transition(7, &t));
                }
                assert_eq!(dense(&sparse, 7), expected);
            }
        }
    }

    #[test]
    fn sparse_summaries_retain_read_arcs_and_unbounded_integers() {
        let read = Transition {
            name: "read".into(),
            pre: vec![(5, u64::MAX)],
            post: vec![(5, u64::MAX)],
        };
        let s = SparseSummary::transition(&read);
        assert_eq!(
            s.coordinates,
            vec![(5, BigInt::from(u64::MAX), BigInt::zero())]
        );
        assert_eq!(s.then(&s), s);
        for (pre, post) in [(vec![], vec![(5, u64::MAX)]), (vec![(5, u64::MAX)], vec![])] {
            let t = Transition {
                name: "large".into(),
                pre,
                post,
            };
            let mut sparse = SparseSummary::transition(&t);
            let mut expected = WordSummary::transition(6, &t);
            for _ in 0..80 {
                sparse = sparse.then(&sparse);
                expected = expected.then(&expected);
                assert_eq!(dense(&sparse, 6), expected);
            }
            assert!(sparse.coordinates[0].2.to_i128().is_none());
        }
    }

    #[test]
    fn sparse_region_preserves_hurdles_and_signed_targets() {
        let t = Transition {
            name: "transfer".into(),
            pre: vec![(0, 2), (1, 1)],
            post: vec![(0, 1), (1, 2)],
        };
        let p = Problem {
            places: vec!["x".into(), "y".into()],
            initial: vec![7, 1],
            transitions: vec![t.clone()],
            target: vec![Constraint {
                coefficients: vec![-1, 1],
                bound: 0,
                equality: true,
            }],
        };
        let single = SparseSummary::transition(&t);
        let word = single.then(&single).then(&single);
        let region = Region::new(&p, &word, vec![0, 0, 0]).unwrap();
        let targets = vec![SparseTarget {
            coefficients: vec![(0, -1), (1, 1)],
            equality: true,
        }];
        for x in 0..10 {
            for y in 0..10 {
                let mut candidate = p.clone();
                candidate.initial = vec![x, y];
                assert_eq!(
                    region.distance(&targets, &candidate.initial) == 0,
                    candidate.check_witness(&region.word).is_ok()
                );
            }
        }
    }

    #[test]
    fn unreachable_and_resource_limited_cases_remain_unknown() {
        let p = Problem {
            places: vec!["x".into()],
            initial: vec![0],
            transitions: vec![Transition {
                name: "read".into(),
                pre: vec![(0, 1)],
                post: vec![(0, 2)],
            }],
            target: vec![Constraint {
                coefficients: vec![1],
                bound: 1,
                equality: true,
            }],
        };
        assert_eq!(solve(&p, Duration::from_secs(1), 100).verdict, "unknown");
        assert_eq!(solve(&p, Duration::ZERO, 100).verdict, "unknown");
        assert_eq!(solve(&p, Duration::from_secs(1), 0).verdict, "unknown");
        let mut invalid = p;
        invalid.transitions[0].pre[0].0 = 1;
        assert_eq!(
            solve(&invalid, Duration::from_secs(1), 100).verdict,
            "unknown"
        );
    }

    #[test]
    fn promising_suffix_with_machine_overflow_is_not_a_witness() {
        let p = Problem {
            places: vec!["x".into(), "y".into()],
            initial: vec![u64::MAX, 0],
            transitions: vec![Transition {
                name: "overflow".into(),
                pre: vec![],
                post: vec![(0, 1), (1, 1)],
            }],
            target: vec![Constraint {
                coefficients: vec![0, 1],
                bound: 1,
                equality: true,
            }],
        };
        assert_eq!(solve(&p, Duration::from_secs(1), 100).verdict, "unknown");
    }

    #[test]
    fn large_sparse_net_returns_original_replayed_witness() {
        let n = 10_000;
        let mut p = Problem {
            places: (0..n).map(|i| i.to_string()).collect(),
            initial: vec![0; n],
            transitions: vec![Transition {
                name: "transfer".into(),
                pre: vec![(2, 2)],
                post: vec![(n - 1, 1)],
            }],
            target: vec![Constraint {
                coefficients: vec![0; n],
                bound: 1,
                equality: true,
            }],
        };
        p.initial[2] = 2;
        p.target[0].coefficients[n - 1] = 1;
        let summary = SparseSummary::transition(&p.transitions[0]);
        assert_eq!(summary.coordinates.len(), 2);
        let out = solve(&p, Duration::from_secs(1), 100);
        assert_eq!(out.verdict, "reachable", "{}", out.reason);
        assert_eq!(out.trace, vec![0]);
        p.check_witness(&out.trace).unwrap();
    }
}
