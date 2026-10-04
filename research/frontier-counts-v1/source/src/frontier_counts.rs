//! Integer count candidates refined by complete count-bounded execution graphs.
//! If no explored prefix reaches the target, any witness must first exit this
//! graph by firing an exhausted transition t. Its total count then exceeds the
//! candidate's count for t. Incomplete exploration never yields a frontier cut.
use crate::{
    linear::{self, Row, System},
    model::Problem,
    search::Outcome,
};
use num_bigint::BigInt;
use std::{
    collections::{HashSet, VecDeque},
    sync::Arc,
    time::{Duration, Instant},
};

const MAX_CELLS: usize = 16_000_000;
const MAX_MODELS: usize = 128;

struct Node {
    marking: Vec<u64>,
    remaining: Arc<Vec<u64>>,
    parent: Option<(usize, usize)>,
}

enum Exploration {
    Witness(Vec<usize>),
    Frontier(Vec<(usize, u64)>),
    Limited(&'static str),
}

fn explore(
    p: &Problem,
    counts: &[u64],
    deadline: Instant,
    max_states: usize,
    states: &mut usize,
) -> Exploration {
    let active: Vec<_> = counts
        .iter()
        .enumerate()
        .filter_map(|(i, &n)| (n > 0).then_some(i))
        .collect();
    let mut slot = vec![None; counts.len()];
    for (j, &i) in active.iter().enumerate() {
        slot[i] = Some(j);
    }
    let width = p.places.len().saturating_add(active.len()).max(1);
    let node_limit = MAX_CELLS / width;
    if *states >= max_states || node_limit == 0 || Instant::now() >= deadline {
        return Exploration::Limited("execution resource limit");
    }
    let remaining = Arc::new(active.iter().map(|&i| counts[i]).collect::<Vec<_>>());
    // Remaining counts determine the marking through the state equation.
    let mut seen = HashSet::from([remaining.clone()]);
    let mut nodes = vec![Node {
        marking: p.initial.clone(),
        remaining,
        parent: None,
    }];
    let mut queue = VecDeque::from([0]);
    let mut frontier = vec![false; counts.len()];
    *states += 1;
    while let Some(index) = queue.pop_front() {
        if Instant::now() >= deadline {
            return Exploration::Limited("execution deadline");
        }
        match p.accepts(&nodes[index].marking) {
            Ok(true) => {
                let mut trace = vec![];
                let mut cursor = index;
                while let Some((parent, t)) = nodes[cursor].parent {
                    trace.push(t);
                    cursor = parent;
                }
                trace.reverse();
                return Exploration::Witness(trace);
            }
            Ok(false) => {}
            Err(_) => return Exploration::Limited("target arithmetic overflow"),
        }
        for (t, transition) in p.transitions.iter().enumerate() {
            if t % 256 == 0 && Instant::now() >= deadline {
                return Exploration::Limited("execution deadline");
            }
            if transition
                .pre
                .iter()
                .any(|&(q, w)| nodes[index].marking[q] < w)
            {
                continue;
            }
            let Some(j) = slot[t].filter(|&j| nodes[index].remaining[j] > 0) else {
                frontier[t] = true;
                continue;
            };
            let mut remaining = nodes[index].remaining.as_ref().clone();
            remaining[j] -= 1;
            if seen.contains(&remaining) {
                continue;
            }
            if *states >= max_states || nodes.len() >= node_limit {
                return Exploration::Limited("execution state or storage limit");
            }
            let marking = match p.fire(&nodes[index].marking, t) {
                Ok(Some(marking)) => marking,
                _ => return Exploration::Limited("execution arithmetic overflow"),
            };
            let remaining = Arc::new(remaining);
            seen.insert(remaining.clone());
            queue.push_back(nodes.len());
            nodes.push(Node {
                marking,
                remaining,
                parent: Some((index, t)),
            });
            *states += 1;
        }
    }
    Exploration::Frontier(
        frontier
            .iter()
            .enumerate()
            .filter_map(|(t, &yes)| yes.then_some((t, counts[t])))
            .collect(),
    )
}

fn refine(system: &mut System, frontier: &[(usize, u64)]) {
    if frontier.iter().all(|&(_, n)| n == 0) {
        system.rows.push(Row {
            coefficients: frontier.iter().map(|&(t, _)| (t, 1.into())).collect(),
            bound: 1.into(),
        });
    } else if let [(t, n)] = frontier {
        system.rows.push(Row {
            coefficients: vec![(*t, 1.into())],
            bound: BigInt::from(*n) + 1,
        });
    } else {
        let mut selectors = vec![];
        for &(t, n) in frontier {
            let s = system.variables;
            system.variables += 1;
            selectors.push((s, 1.into()));
            system.rows.push(Row {
                coefficients: vec![(s, (-1).into())],
                bound: (-1).into(),
            });
            system.rows.push(Row {
                coefficients: vec![(t, 1.into()), (s, -(BigInt::from(n) + BigInt::from(1)))],
                bound: 0.into(),
            });
        }
        system.rows.push(Row {
            coefficients: selectors,
            bound: 1.into(),
        });
    }
}

pub fn solve(p: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    let deadline = Instant::now() + timeout;
    let method = "frontier-count-plan";
    let mut states = 0;
    let mut models = 0;
    let mut cuts = 0;
    let mut reason = "model budget";
    let mut system = linear::state_equation(p);
    for _ in 0..MAX_MODELS {
        if Instant::now() >= deadline || states >= max_states {
            reason = "resource limit";
            break;
        }
        // The cap bounds candidate discovery, including auxiliary selectors.
        let cap = max_states
            .saturating_sub(states)
            .saturating_sub(1)
            .min(i32::MAX as usize) as u32;
        let remaining = deadline.saturating_duration_since(Instant::now());
        let Some(model) = system.integer_model(Instant::now() + remaining / 2, cap) else {
            reason = "no integer candidate within limits";
            break;
        };
        models += 1;
        match explore(
            p,
            &model[..p.transitions.len()],
            deadline,
            max_states,
            &mut states,
        ) {
            Exploration::Witness(trace) => {
                if let Ok(marking) = p.check_witness(&trace) {
                    let mut out = Outcome::unknown(
                        method,
                        &format!("{models} integer models, {cuts} frontier cuts; replayed witness"),
                        states,
                    );
                    out.verdict = "reachable";
                    out.trace = trace;
                    out.marking = Some(marking);
                    return out;
                }
                reason = "witness replay failed";
                break;
            }
            Exploration::Frontier(frontier) => {
                if frontier.is_empty() {
                    reason = "closed execution graph; no negative certificate emitted";
                    break;
                }
                let entries = system
                    .rows
                    .iter()
                    .map(|r| r.coefficients.len())
                    .sum::<usize>();
                if entries.saturating_add(frontier.len().saturating_mul(4)) > MAX_CELLS {
                    reason = "constraint storage limit";
                    break;
                }
                refine(&mut system, &frontier);
                cuts += 1;
            }
            Exploration::Limited(why) => {
                reason = why;
                break;
            }
        }
    }
    Outcome::unknown(
        method,
        &format!("{models} integer models, {cuts} frontier cuts; {reason}"),
        states,
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Constraint, Transition};

    fn problem() -> Problem {
        Problem {
            places: vec!["a".into(), "goal".into()],
            initial: vec![0, 0],
            transitions: vec![
                Transition {
                    name: "make".into(),
                    pre: vec![],
                    post: vec![(0, 1)],
                },
                Transition {
                    name: "read".into(),
                    pre: vec![(0, 3)],
                    post: vec![(0, 3), (1, 1)],
                },
            ],
            target: vec![Constraint {
                coefficients: vec![0, 1],
                bound: 1,
                equality: false,
            }],
        }
    }

    #[test]
    fn refines_read_arc_obstruction_and_replays() {
        let p = problem();
        let out = solve(&p, Duration::from_secs(2), 1000);
        assert_eq!(out.verdict, "reachable", "{}", out.reason);
        assert_eq!(p.check_witness(&out.trace).unwrap(), out.marking.unwrap());
        assert!(out.reason.contains("3 frontier cuts"), "{}", out.reason);
    }

    #[test]
    fn positive_frontier_and_interrupted_closure() {
        let p = problem();
        let deadline = Instant::now() + Duration::from_secs(1);
        let mut states = 0;
        let Exploration::Frontier(frontier) = explore(&p, &[1, 1], deadline, 100, &mut states)
        else {
            panic!()
        };
        assert_eq!(frontier, vec![(0, 1)]);
        assert!(matches!(
            explore(&p, &[1, 1], deadline, 1, &mut 0),
            Exploration::Limited(_)
        ));
        assert!(matches!(
            explore(&p, &[1, 1], Instant::now(), 100, &mut 0),
            Exploration::Limited(_)
        ));
    }

    #[test]
    fn target_prefix_needs_not_consume_all_counts() {
        let p = problem();
        let Exploration::Witness(trace) = explore(
            &p,
            &[10, 10],
            Instant::now() + Duration::from_secs(1),
            1000,
            &mut 0,
        ) else {
            panic!()
        };
        assert_eq!(trace.len(), 4);
        p.check_witness(&trace).unwrap();
    }

    #[test]
    fn selector_disjunction_excludes_candidate_and_keeps_both_exits() {
        for counts in [[1, 2], [2, 2], [1, 3]] {
            let mut system = System {
                variables: 2,
                rows: vec![],
            };
            refine(&mut system, &[(0, 1), (1, 2)]);
            for (i, n) in counts.into_iter().enumerate() {
                system.rows.push(Row {
                    coefficients: vec![(i, 1.into())],
                    bound: n.into(),
                });
                system.rows.push(Row {
                    coefficients: vec![(i, (-1).into())],
                    bound: (-n).into(),
                });
            }
            let model = system.integer_model(Instant::now() + Duration::from_secs(1), 100);
            assert_eq!(model.is_some(), counts != [1, 2]);
        }
    }

    #[test]
    fn every_short_witness_crosses_the_learned_frontier() {
        let deadline = Instant::now() + Duration::from_secs(20);
        let mut checked = 0;
        for initial in 0..3 {
            for need in 1..4 {
                for produced in 0..3 {
                    for equality in [false, true] {
                        let mut p = problem();
                        p.initial[0] = initial;
                        p.transitions[1].pre[0].1 = need;
                        p.transitions[1].post[0].1 = produced;
                        if produced == 0 {
                            p.transitions[1].post.remove(0);
                        }
                        p.target[0].coefficients = vec![-1, 1];
                        p.target[0].equality = equality;
                        p.validate().unwrap();
                        for a in 0..3 {
                            for b in 0..3 {
                                let result = explore(&p, &[a, b], deadline, 1000, &mut 0);
                                let frontier = match result {
                                    Exploration::Witness(trace) => {
                                        p.check_witness(&trace).unwrap();
                                        continue;
                                    }
                                    Exploration::Frontier(frontier) => frontier,
                                    Exploration::Limited(reason) => panic!("{reason}"),
                                };
                                checked += 1;
                                let mut pending = vec![(p.initial.clone(), [0u64; 2], 0)];
                                while let Some((marking, counts, depth)) = pending.pop() {
                                    if p.accepts(&marking).unwrap() {
                                        assert!(
                                            frontier.iter().any(|&(t, n)| counts[t] > n),
                                            "missing exit for counts {counts:?}, bounds {a},{b}"
                                        );
                                    }
                                    if depth == 6 {
                                        continue;
                                    }
                                    for t in 0..2 {
                                        if let Some(next) = p.fire(&marking, t).unwrap() {
                                            let mut next_counts = counts;
                                            next_counts[t] += 1;
                                            pending.push((next, next_counts, depth + 1));
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        assert!(checked > 100);
    }

    #[test]
    fn overflow_cannot_emit_a_frontier() {
        let mut p = problem();
        p.initial[0] = u64::MAX;
        assert!(matches!(
            explore(
                &p,
                &[1, 0],
                Instant::now() + Duration::from_secs(1),
                100,
                &mut 0
            ),
            Exploration::Limited("execution arithmetic overflow")
        ));
    }
}
