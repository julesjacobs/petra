use std::{
    collections::{HashSet, VecDeque},
    time::Duration,
};
use vass_reach::{
    model::{Constraint, Problem, Transition},
    search,
};

fn oracle(p: &Problem) -> (bool, Vec<usize>, usize) {
    let mut seen = HashSet::from([p.initial.clone()]);
    let mut queue = VecDeque::from([(p.initial.clone(), Vec::new())]);
    while let Some((marking, trace)) = queue.pop_front() {
        if p.target.iter().all(|c| {
            let value: i128 = c
                .coefficients
                .iter()
                .zip(&marking)
                .map(|(&a, &x)| i128::from(a) * i128::from(x))
                .sum();
            if c.equality {
                value == i128::from(c.bound)
            } else {
                value >= i128::from(c.bound)
            }
        }) {
            return (true, trace, seen.len());
        }
        for (t, tr) in p.transitions.iter().enumerate() {
            let mut successor = marking.clone();
            let mut enabled = true;
            for (place, value) in successor.iter_mut().enumerate() {
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
                if *value < pre {
                    enabled = false;
                    break;
                }
                *value = *value - pre + post;
            }
            if enabled && seen.insert(successor.clone()) {
                let mut path = trace.clone();
                path.push(t);
                queue.push_back((successor, path));
            }
        }
    }
    (false, vec![], seen.len())
}

fn problem(initial: Vec<u64>, transitions: Vec<Transition>, target: Vec<Constraint>) -> Problem {
    Problem {
        places: (0..initial.len()).map(|i| format!("p{i}")).collect(),
        initial,
        transitions,
        target,
    }
}

fn tr(pre: &[(usize, u64)], post: &[(usize, u64)]) -> Transition {
    Transition {
        name: "t".into(),
        pre: pre.to_vec(),
        post: post.to_vec(),
    }
}

fn exact(place: usize, value: i64, dimension: usize) -> Constraint {
    let mut coefficients = vec![0; dimension];
    coefficients[place] = 1;
    Constraint {
        coefficients,
        bound: value,
        equality: true,
    }
}

fn compare(p: &Problem) {
    p.validate().unwrap();
    let (reachable, trace, count) = oracle(p);
    for best_first in [false, true] {
        let result = search::solve(p, best_first, Duration::from_secs(10), 10_000);
        assert_eq!(
            result.verdict,
            if reachable {
                "reachable"
            } else {
                "unreachable"
            },
            "{p:?}"
        );
        if reachable {
            assert_eq!(
                p.check_witness(&result.trace).unwrap(),
                result.marking.unwrap()
            );
            if !best_first {
                assert_eq!(result.trace, trace);
                assert_eq!(result.states, count);
            }
        } else {
            assert_eq!(result.states, count);
        }
    }
}

#[test]
fn bounded_weighted_nets_match_independent_dense_bfs() {
    let mut seed = 0x951beac3u64;
    let mut random = || {
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        seed >> 32
    };
    for case in 0..96 {
        let active = 2 + case % 4;
        let dimension = active + if case % 2 == 0 { 96 } else { 0 };
        let mut initial = vec![0; dimension];
        for _ in 0..4 {
            initial[random() as usize % active] += 1;
        }
        let mut transitions = Vec::new();
        for _ in 0..12 {
            let weight = random() % 4;
            let mut arcs = || {
                let mut dense = vec![0; active];
                for _ in 0..weight {
                    dense[random() as usize % active] += 1;
                }
                dense
                    .into_iter()
                    .enumerate()
                    .filter(|&(_, w)| w != 0)
                    .collect()
            };
            transitions.push(Transition {
                name: "random".into(),
                pre: arcs(),
                post: arcs(),
            });
        }
        for goal in 0..6 {
            let mut coefficients = vec![0; dimension];
            coefficients[0] = 1;
            coefficients[active - 1] = -1;
            let target = vec![
                exact(1, goal, dimension),
                Constraint {
                    coefficients,
                    bound: -1,
                    equality: case % 3 == 0,
                },
            ];
            compare(&problem(initial.clone(), transitions.clone(), target));
        }
    }
}

#[test]
fn weighted_read_arcs_require_the_entire_preset() {
    let transitions = vec![
        tr(&[(0, 1), (1, 2)], &[(0, 1), (2, 1)]),
        tr(&[(0, 1)], &[(1, 1)]),
        tr(&[(1, 1)], &[(0, 1)]),
    ];
    compare(&problem(
        vec![1, 1, 0, 0, 0, 0],
        transitions.clone(),
        vec![exact(2, 1, 6)],
    ));
    let p = problem(vec![1, 2, 0, 0, 0, 0], transitions, vec![exact(2, 1, 6)]);
    compare(&p);
    assert_eq!(
        search::solve(&p, false, Duration::from_secs(1), 100).trace,
        vec![0]
    );
}

#[test]
fn sources_empty_nets_and_transition_order_are_preserved() {
    compare(&problem(
        vec![],
        vec![tr(&[], &[])],
        vec![Constraint {
            coefficients: vec![],
            bound: 1,
            equality: false,
        }],
    ));
    compare(&problem(vec![0; 64], vec![], vec![exact(0, 1, 64)]));
    compare(&problem(vec![0; 64], vec![], vec![]));
    let p = problem(
        vec![0; 64],
        vec![tr(&[], &[(0, 1)]), tr(&[], &[(1, 1)])],
        vec![exact(0, 1, 64)],
    );
    compare(&p);
    for best in [false, true] {
        assert_eq!(
            search::solve(&p, best, Duration::from_secs(1), 100).trace,
            vec![0]
        );
    }
}

#[test]
fn finite_exhaustion_and_limits_do_not_confuse_unknown_with_unreachable() {
    let p = problem(
        vec![1, 0],
        vec![tr(&[(0, 1)], &[(0, 1)])],
        vec![exact(1, 1, 2)],
    );
    for best in [false, true] {
        let out = search::solve(&p, best, Duration::from_secs(1), 1);
        assert_eq!(out.verdict, "unreachable");
        assert_eq!(out.states, 1);
        let mut moving = p.clone();
        moving.transitions.push(tr(&[(0, 1)], &[(1, 1)]));
        let out = search::solve(&moving, best, Duration::from_secs(1), 1);
        assert_eq!(out.verdict, "unknown");
        assert_eq!(out.reason, "state limit");
        let out = search::solve(&moving, best, Duration::ZERO, 100);
        assert_eq!(out.verdict, "unknown");
        assert_eq!(out.reason, "time limit");
    }
}

#[test]
fn counter_and_target_overflow_remain_unknown() {
    let counter = problem(
        vec![u64::MAX, 0],
        vec![tr(&[], &[(0, 1)])],
        vec![exact(1, 1, 2)],
    );
    let target = problem(
        vec![u64::MAX; 3],
        vec![],
        vec![Constraint {
            coefficients: vec![i64::MAX; 3],
            bound: 0,
            equality: true,
        }],
    );
    for best in [false, true] {
        for (p, reason) in [
            (&counter, "counter overflow"),
            (&target, "target arithmetic overflow"),
        ] {
            let out = search::solve(p, best, Duration::from_secs(1), 100);
            assert_eq!(out.verdict, "unknown");
            assert_eq!(out.reason, reason);
        }
    }
}
