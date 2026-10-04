use serde_json::{Value, json};
use std::{
    collections::{HashSet, VecDeque},
    time::{Duration, Instant},
};
use vass_reach::{
    model::{Constraint, Problem, Transition},
    target_path_potential::{self, Preparation, Prepared},
};

fn deadline() -> Instant {
    Instant::now() + Duration::from_secs(10)
}
fn transition(pre: &[(usize, u64)], post: &[(usize, u64)]) -> Transition {
    Transition {
        name: "t".into(),
        pre: pre.to_vec(),
        post: post.to_vec(),
    }
}
fn constraint(coefficients: &[i64], bound: i64, equality: bool) -> Constraint {
    Constraint {
        coefficients: coefficients.to_vec(),
        bound,
        equality,
    }
}
fn problem(initial: &[u64], transitions: Vec<Transition>, target: Vec<Constraint>) -> Problem {
    Problem {
        places: (0..initial.len()).map(|i| format!("p{i}")).collect(),
        initial: initial.to_vec(),
        transitions,
        target,
    }
}
fn source(target: i64) -> Problem {
    problem(
        &[0],
        vec![transition(&[], &[(0, 1)])],
        vec![constraint(&[1], target, true)],
    )
}
fn reduced(p: &Problem) -> Prepared {
    match target_path_potential::prepare(p, deadline(), 1_000_000).unwrap() {
        Some(Preparation::Reduced(q)) => q,
        other => panic!("unexpected preparation {other:?}"),
    }
}

#[test]
fn unbounded_source_becomes_bounded_only_on_target_reaching_paths() {
    let p = source(2);
    let q = reduced(&p);
    assert_eq!((q.bound, q.slack), (2, 2));
    assert_eq!(q.problem.initial, [0, 2]);
    assert_eq!(q.problem.transitions[0].pre, [(1, 1)]);
    let first = q.problem.fire(&q.problem.initial, 0).unwrap().unwrap();
    let second = q.problem.fire(&first, 0).unwrap().unwrap();
    assert_eq!(second, [2, 0]);
    assert!(q.problem.accepts(&second).unwrap());
    assert!(q.problem.fire(&second, 0).unwrap().is_none());
    assert_eq!(p.fire(&[2], 0).unwrap(), Some(vec![3]));
    assert_eq!(
        q.lift_witness(&p, &[0, 0], deadline(), 10_000).unwrap(),
        (vec![0, 0], vec![2])
    );
}

#[test]
fn weighted_net_growth_and_zero_growth_keep_original_arc_order() {
    let p = problem(
        &[2, 1],
        vec![
            transition(&[(1, 1), (0, 2)], &[(0, 4), (1, 2)]),
            transition(&[(0, 2)], &[(1, 2)]),
        ],
        vec![
            constraint(&[1, 0], 4, true),
            constraint(&[0, -1], -2, false),
            constraint(&[0, 0], -3, false),
        ],
    );
    let q = reduced(&p);
    assert_eq!((q.bound, q.slack), (6, 3));
    assert_eq!(q.problem.transitions[0].pre, [(1, 1), (0, 2), (2, 3)]);
    assert_eq!(q.problem.transitions[0].post, p.transitions[0].post);
    assert_eq!(q.problem.transitions[1].pre, p.transitions[1].pre);
    for (a, b) in q.problem.target.iter().zip(&p.target) {
        assert_eq!(&a.coefficients[..2], b.coefficients);
        assert_eq!(a.coefficients[2], 0);
        assert_eq!((a.bound, a.equality), (b.bound, b.equality));
    }
    assert_eq!(
        q.lift_witness(&p, &[0], deadline(), 10_000).unwrap().1,
        [4, 2]
    );
    assert!(q.lift_witness(&p, &[1, 1], deadline(), 10_000).is_err());
}

#[test]
fn unary_upper_bounds_use_floor_and_tightest_row() {
    for (row, expected) in [
        (constraint(&[2], 5, true), 2),
        (constraint(&[-2], -5, true), 2),
        (constraint(&[-2], -5, false), 2),
        (constraint(&[i64::MIN], i64::MIN, true), 1),
        (constraint(&[-1], i64::MIN, false), 1i128 << 63),
    ] {
        let mut p = source(0);
        p.target = vec![row];
        assert_eq!(reduced(&p).bound, expected);
    }
    let mut p = source(20);
    p.target
        .extend([constraint(&[-3], -8, false), constraint(&[1], 1, false)]);
    assert_eq!(reduced(&p).bound, 2);
    for row in [constraint(&[2], -1, true), constraint(&[-2], 1, false)] {
        p.target = vec![row];
        assert!(matches!(
            target_path_potential::prepare(&p, deadline(), 10_000).unwrap(),
            Some(Preparation::Infeasible)
        ));
    }
}

#[test]
fn missing_bounds_decreasing_transitions_and_no_growth_skip() {
    let cases = [
        problem(&[], vec![], vec![]),
        problem(&[0], vec![], vec![constraint(&[1], 2, true)]),
        problem(
            &[0],
            vec![transition(&[], &[(0, 1)])],
            vec![constraint(&[1], 2, false)],
        ),
        problem(
            &[0, 0],
            vec![transition(&[], &[(0, 1)])],
            vec![constraint(&[1, 1], 2, true)],
        ),
        problem(
            &[0, 0],
            vec![transition(&[], &[(0, 1)])],
            vec![constraint(&[-1, 0], -2, false)],
        ),
        problem(
            &[3],
            vec![transition(&[(0, 3)], &[(0, 2)])],
            vec![constraint(&[1], 2, true)],
        ),
    ];
    let proof = json!({"kind":"target-path-potential-v1","inner":{}});
    let infeasible = json!({"kind":"target-path-potential-infeasible-v1"});
    for p in cases {
        assert!(
            target_path_potential::prepare(&p, deadline(), 10_000)
                .unwrap()
                .is_none()
        );
        assert!(target_path_potential::verify_reduction(&p, &proof, deadline(), 10_000).is_err());
        assert!(
            target_path_potential::verify_infeasible(&p, &infeasible, deadline(), 10_000).is_err()
        );
    }
}

#[test]
fn infeasibility_does_not_require_a_growing_transition() {
    let proof = json!({"kind":"target-path-potential-infeasible-v1"});
    for transitions in [vec![], vec![transition(&[], &[(0, 1)])]] {
        let p = problem(&[3], transitions, vec![constraint(&[1], 2, true)]);
        assert!(matches!(
            target_path_potential::prepare(&p, deadline(), 10_000).unwrap(),
            Some(Preparation::Infeasible)
        ));
        target_path_potential::verify_infeasible(&p, &proof, deadline(), 10_000).unwrap();
        for malformed in [
            json!({"kind":"other"}),
            json!({"kind":"target-path-potential-infeasible-v1","inner":{}}),
            Value::Null,
        ] {
            assert!(
                target_path_potential::verify_infeasible(&p, &malformed, deadline(), 10_000)
                    .is_err()
            );
        }
    }
    assert!(
        target_path_potential::verify_infeasible(&source(2), &proof, deadline(), 10_000).is_err()
    );
}

#[test]
fn slack_name_is_fresh() {
    let mut p = problem(
        &[0, 0],
        vec![transition(&[], &[(0, 1)])],
        vec![constraint(&[1, 0], 2, true), constraint(&[0, 1], 0, true)],
    );
    p.places = vec!["__target_path_slack".into(), "__target_path_slack_".into()];
    assert_eq!(reduced(&p).problem.places[2], "__target_path_slack__");
}

#[test]
fn proof_reconstructs_the_net_from_the_input() {
    let p = source(2);
    let q = reduced(&p);
    let inner = json!({"kind":"placeholder"});
    let proof = q.wrap_proof(inner.clone(), deadline(), 10_000).unwrap();
    let (checked, checked_inner) =
        target_path_potential::verify_reduction(&p, &proof, deadline(), 10_000).unwrap();
    assert_eq!(checked_inner, &inner);
    assert_eq!(
        serde_json::to_value(&checked.problem).unwrap(),
        serde_json::to_value(&q.problem).unwrap()
    );
    let (changed, _) =
        target_path_potential::verify_reduction(&source(3), &proof, deadline(), 10_000).unwrap();
    assert_eq!(changed.slack, 3);
    for malformed in [
        Value::Null,
        json!([]),
        json!({"kind":"target-path-potential-v1"}),
        json!({"kind":"other","inner":{}}),
        json!({"kind":true,"inner":{}}),
        json!({"kind":"target-path-potential-v1","inner":{},"bound":2}),
        json!({"kind":"target-path-potential-v1","inner":null}),
        json!({"kind":"target-path-potential-v1","inner":[]}),
    ] {
        assert!(
            target_path_potential::verify_reduction(&p, &malformed, deadline(), 10_000).is_err()
        );
    }
    assert!(q.wrap_proof(Value::Null, deadline(), 10_000).is_err());
}

#[test]
fn malformed_input_is_rejected_before_indexing() {
    let base = source(2);
    let mut cases = Vec::new();
    let mut p = base.clone();
    p.initial.clear();
    cases.push(p);
    let mut p = base.clone();
    p.target[0].coefficients.clear();
    cases.push(p);
    for arcs in [vec![(1, 1)], vec![(0, 0)], vec![(0, 1), (0, 2)]] {
        let mut p = base.clone();
        p.transitions[0].pre = arcs.clone();
        cases.push(p);
        let mut p = base.clone();
        p.transitions[0].post = arcs;
        cases.push(p);
    }
    let proof = json!({"kind":"target-path-potential-v1","inner":{}});
    for p in cases {
        assert!(target_path_potential::prepare(&p, deadline(), 10_000).is_err());
        assert!(target_path_potential::verify_reduction(&p, &proof, deadline(), 10_000).is_err());
    }
}

#[test]
fn unrepresentable_slack_or_arc_fails_conservatively() {
    let p = problem(
        &[0, 0, 0],
        vec![transition(&[], &[(0, 1)])],
        vec![
            constraint(&[-1, 0, 0], i64::MIN, false),
            constraint(&[0, -1, 0], i64::MIN, false),
            constraint(&[0, 0, -1], i64::MIN, false),
        ],
    );
    assert!(target_path_potential::prepare(&p, deadline(), 10_000).is_err());
    let p = problem(
        &[0, 0],
        vec![transition(&[], &[(0, u64::MAX), (1, u64::MAX)])],
        vec![constraint(&[1, 0], 0, true), constraint(&[0, 1], 0, true)],
    );
    assert!(target_path_potential::prepare(&p, deadline(), 10_000).is_err());
}

#[test]
fn original_witness_checks_reject_invalid_steps_targets_and_overflow() {
    let p = source(2);
    let q = reduced(&p);
    for trace in [vec![], vec![0], vec![0, 0, 0], vec![99]] {
        assert!(q.lift_witness(&p, &trace, deadline(), 10_000).is_err());
    }
    let p = source(0);
    assert_eq!(
        reduced(&p)
            .lift_witness(&p, &[], deadline(), 10_000)
            .unwrap(),
        (vec![], vec![0])
    );
    let mut p = source(2);
    p.transitions[0].post[0].1 = u64::MAX;
    assert!(
        reduced(&p)
            .lift_witness(&p, &[0, 0], deadline(), 10_000)
            .is_err()
    );
}

#[test]
fn all_entrypoints_enforce_work_and_deadlines() {
    let p = source(2);
    let q = reduced(&p);
    let proof = q.wrap_proof(json!({}), deadline(), 10_000).unwrap();
    let infeasible = json!({"kind":"target-path-potential-infeasible-v1"});
    for (time, work) in [(deadline(), 0), (Instant::now(), 1_000_000)] {
        assert!(target_path_potential::prepare(&p, time, work).is_err());
        assert!(target_path_potential::verify_reduction(&p, &proof, time, work).is_err());
        assert!(target_path_potential::verify_infeasible(&p, &infeasible, time, work).is_err());
        assert!(q.wrap_proof(json!({}), time, work).is_err());
        assert!(q.lift_witness(&p, &[0, 0], time, work).is_err());
    }
}

fn reachable_with_mass_cap(p: &Problem, bound: u64) -> Option<Vec<usize>> {
    let mut seen = HashSet::from([p.initial.clone()]);
    let mut todo = VecDeque::from([(p.initial.clone(), vec![])]);
    while let Some((marking, trace)) = todo.pop_front() {
        if p.accepts(&marking).unwrap() {
            return Some(trace);
        }
        for t in 0..p.transitions.len() {
            if let Some(next) = p.fire(&marking, t).unwrap()
                && next.iter().sum::<u64>() <= bound
                && seen.insert(next.clone())
            {
                let mut trace = trace.clone();
                trace.push(t);
                todo.push_back((next, trace));
            }
        }
    }
    None
}

#[test]
fn exhaustive_small_monotone_nets_preserve_target_reachability() {
    let arcs = (0u32..4)
        .map(|bits| {
            (0..2)
                .filter(|i| bits & (1 << i) != 0)
                .map(|i| (i, 1))
                .collect::<Vec<_>>()
        })
        .collect::<Vec<_>>();
    let mut transitions = Vec::new();
    for pre in &arcs {
        for post in &arcs {
            if post.len() >= pre.len() {
                transitions.push(transition(pre, post));
            }
        }
    }
    for first in 0..transitions.len() {
        for second in first..transitions.len() {
            for initial_bits in 0..4 {
                for target_bits in 0..4 {
                    let initial = [initial_bits & 1, (initial_bits >> 1) & 1];
                    let target = [target_bits & 1, (target_bits >> 1) & 1];
                    let p = problem(
                        &initial,
                        vec![transitions[first].clone(), transitions[second].clone()],
                        vec![
                            constraint(&[1, 0], target[0], true),
                            constraint(&[0, 1], target[1], true),
                        ],
                    );
                    // Monotone total mass makes pruning above the exact target mass complete.
                    let bound = (target[0] + target[1]) as u64;
                    let original = reachable_with_mass_cap(&p, bound).is_some();
                    match target_path_potential::prepare(&p, deadline(), 10_000).unwrap() {
                        None => {}
                        Some(Preparation::Infeasible) => assert!(!original),
                        Some(Preparation::Reduced(q)) => {
                            assert_eq!(q.problem.initial.iter().sum::<u64>(), bound);
                            let transformed = reachable_with_mass_cap(&q.problem, bound);
                            assert_eq!(original, transformed.is_some());
                            if let Some(trace) = transformed {
                                let (lifted, marking) =
                                    q.lift_witness(&p, &trace, deadline(), 10_000).unwrap();
                                assert_eq!(p.check_witness(&lifted).unwrap(), marking);
                            }
                        }
                    }
                }
            }
        }
    }
}
