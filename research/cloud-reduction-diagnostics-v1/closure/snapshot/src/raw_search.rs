//! Direct whole-query exploration without complement or disjunct splitting.
use crate::{
    marking::StoredMarking, model::Problem, raw_target::RawQuery, reduced::Prepared,
    search::Outcome,
};
use std::{
    cmp::Reverse,
    collections::{BinaryHeap, HashSet},
    time::{Duration, Instant},
};

pub fn solve(q: &RawQuery, timeout: Duration, max_states: usize, improved: bool) -> Outcome {
    let start = Instant::now();
    let deadline = start + timeout;
    let method = if improved { "raw-search" } else { "raw-bfs" };
    if let Err(e) = q.validate() {
        return Outcome::unknown(method, &e.to_string(), 0);
    }
    let original = q.net();
    let prepared = if improved {
        Prepared::new(&original, &q.target.response_places, deadline)
    } else {
        if Instant::now() >= deadline {
            return Outcome::unknown(method, "time limit", 0);
        }
        Ok(Prepared::identity(&original))
    };
    let prepared = match prepared {
        Ok(prepared) => prepared,
        Err(_) if Instant::now() >= deadline => return Outcome::unknown(method, "time limit", 0),
        Err(_) => Prepared::identity(&original),
    };
    solve_prepared(q, &original, &prepared, deadline, max_states, improved)
}

pub(crate) fn solve_prepared(
    q: &RawQuery,
    original: &Problem,
    prepared: &Prepared,
    deadline: Instant,
    max_states: usize,
    improved: bool,
) -> Outcome {
    let method = if improved { "raw-search" } else { "raw-bfs" };
    if Instant::now() >= deadline {
        return Outcome::unknown(method, "time limit", 0);
    }
    let net = &prepared.net;
    let transitions = crate::successors::TransitionIndex::new(net);
    let mut candidates = Vec::new();
    let mut nodes = vec![(
        StoredMarking::new(&net.initial),
        None::<(usize, usize)>,
        false,
        0usize,
    )];
    let mut seen = HashSet::from([StoredMarking::new(&net.initial)]);
    let mut m = net.initial.clone();
    let mut serial_cache = HashSet::<Vec<u64>>::new();
    let mut heap = BinaryHeap::from([Reverse((0u64, 0usize, 0usize))]);
    let mut fifo = 0;
    let mut iteration = 0;
    loop {
        if Instant::now() >= deadline {
            return Outcome::unknown(method, "time limit", nodes.len());
        }
        while fifo < nodes.len() && nodes[fifo].2 {
            fifo += 1;
        }
        if fifo == nodes.len() {
            return Outcome::unknown(
                method,
                "finite exploration exhausted; no raw closure certificate",
                nodes.len(),
            );
        }
        let id = if improved && iteration % 4 != 0 {
            loop {
                match heap.pop() {
                    Some(Reverse((_, _, i))) if !nodes[i].2 => break i,
                    Some(_) => {}
                    None => break fifo,
                }
            }
        } else {
            fifo
        };
        iteration += 1;
        nodes[id].2 = true;
        nodes[id].0.write_to(&mut m);
        if q.target.zero_places.iter().all(|&i| m[i] == 0) {
            let responses = q
                .target
                .response_places
                .iter()
                .map(|&i| m[i])
                .collect::<Vec<_>>();
            if !serial_cache.contains(&responses) {
                match q.accepts(&m, deadline, max_states.saturating_mul(10)) {
                    Ok(true) => {
                        let mut path = vec![];
                        let mut pos = id;
                        while let Some((parent, t)) = nodes[pos].1 {
                            path.push(t);
                            pos = parent;
                        }
                        path.reverse();
                        let trace = prepared.lift(&path);
                        let marking = match original.check_witness(&trace) {
                            Ok(m) => m,
                            Err(e) => {
                                return Outcome::unknown(
                                    method,
                                    &format!("lift replay failed: {e}"),
                                    nodes.len(),
                                );
                            }
                        };
                        match q.accepts(&marking, deadline, max_states.saturating_mul(10)) {
                            Ok(true) if Instant::now() < deadline => {
                                return Outcome {
                                    verdict: "reachable",
                                    method: method.into(),
                                    reason: "raw target and lifted trace checked".into(),
                                    states: nodes.len(),
                                    trace,
                                    marking: Some(marking),
                                    certificate: None,
                                    proof: None,
                                };
                            }
                            _ => {
                                return Outcome::unknown(
                                    method,
                                    "raw witness check limited or failed",
                                    nodes.len(),
                                );
                            }
                        }
                    }
                    Ok(false) => {
                        serial_cache.insert(responses);
                    }
                    Err(e) => {
                        return Outcome::unknown(method, &format!("membership: {e}"), nodes.len());
                    }
                }
            }
        }
        transitions.candidates(&m, &mut candidates);
        for &t in &candidates {
            if Instant::now() >= deadline {
                return Outcome::unknown(method, "time limit", nodes.len());
            }
            let next = match net.fire(&m, t) {
                Ok(Some(n)) => n,
                Ok(None) => continue,
                Err(e) => return Outcome::unknown(method, &e.to_string(), nodes.len()),
            };
            let stored = StoredMarking::new(&next);
            if seen.contains(&stored) {
                continue;
            }
            if nodes.len() >= max_states {
                return Outcome::unknown(method, "state limit", nodes.len());
            }
            let id2 = nodes.len();
            let depth = nodes[id].3 + 1;
            let pending = q
                .target
                .zero_places
                .iter()
                .fold(0u64, |sum, &i| sum.saturating_add(next[i]));
            if improved {
                heap.push(Reverse((pending, depth, id2)));
            }
            seen.insert(stored.clone());
            nodes.push((stored, Some((id, t)), false, depth));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Transition;
    use crate::raw_target::{LinearSet, RawTarget};
    #[test]
    fn raw_witness_requires_nonmembership() {
        let q = RawQuery {
            format: "ser-raw-v1".into(),
            places: vec!["r".into()],
            initial: vec![0],
            transitions: vec![Transition {
                name: "emit".into(),
                pre: vec![],
                post: vec![(0, 1)],
            }],
            target: RawTarget {
                excluded_automaton: None,
                kind: "completed-outside-semilinear".into(),
                zero_places: vec![],
                response_places: vec![0],
                excluded_semilinear: vec![LinearSet {
                    base: vec![],
                    periods: vec![vec![(0, 2)]],
                }],
            },
        };
        for optimized in [false, true] {
            let result = solve(&q, Duration::from_secs(1), 100, optimized);
            assert_eq!(result.verdict, "reachable");
            assert_eq!(result.marking, Some(vec![1]));
        }
    }
    #[test]
    fn resource_limit_is_not_a_negative() {
        let q = RawQuery {
            format: "ser-raw-v1".into(),
            places: vec!["r".into()],
            initial: vec![0],
            transitions: vec![],
            target: RawTarget {
                excluded_automaton: None,
                kind: "completed-outside-semilinear".into(),
                zero_places: vec![],
                response_places: vec![0],
                excluded_semilinear: vec![LinearSet {
                    base: vec![],
                    periods: vec![],
                }],
            },
        };
        assert_eq!(solve(&q, Duration::ZERO, 100, true).verdict, "unknown");
        assert_eq!(
            solve(&q, Duration::from_secs(1), 100, true).verdict,
            "unknown"
        );
    }
}
