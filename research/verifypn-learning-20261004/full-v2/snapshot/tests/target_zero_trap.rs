use serde_json::{Value, json};
use std::{
    collections::{HashSet, VecDeque},
    time::{Duration, Instant},
};
use vass_reach::{
    model::{Constraint, Problem, Transition},
    target_zero_trap::{self, Preparation, Prepared},
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
fn reduced(p: &Problem) -> Prepared {
    match target_zero_trap::prepare(p, deadline(), 1_000_000).unwrap() {
        Preparation::Reduced(p) => p,
        Preparation::Marked { trap } => panic!("unexpected marked trap {trap:?}"),
    }
}
fn equal_problem(a: &Problem, b: &Problem) {
    assert_eq!(
        serde_json::to_value(a).unwrap(),
        serde_json::to_value(b).unwrap()
    );
}

#[test]
fn weighted_selfloops_sources_and_empty_posts() {
    let p = problem(
        &[0, 0, 0, 0],
        vec![
            transition(&[(0, 2)], &[(0, 1)]),
            transition(&[], &[(0, 3)]),
            transition(&[(1, 1)], &[]),
            transition(&[(2, 1)], &[(1, 2)]),
            transition(&[(3, 2)], &[(3, 1), (2, 1)]),
            transition(&[], &[]),
        ],
        vec![constraint(&[1, 1, 1, 1], 0, true)],
    );
    let q = reduced(&p);
    assert_eq!(q.trap, [0, 3]);
    assert_eq!(q.places, [1, 2]);
    assert_eq!(q.transitions, [2, 3, 5]);
    assert_eq!(q.problem.transitions[0].pre, [(0, 1)]);
    assert_eq!(q.problem.transitions[1].post, [(0, 2)]);
    assert_eq!(q.problem.target[0].coefficients, [1, 1]);
}

#[test]
fn forced_zero_facts_respect_sign_and_relation() {
    let cases = [
        (constraint(&[2, 3, 0], 0, true), vec![0, 1]),
        (constraint(&[-2, -3, 0], 0, true), vec![0, 1]),
        (constraint(&[-2, -3, 0], 0, false), vec![0, 1]),
        (constraint(&[2, 3, 0], 0, false), vec![]),
        (constraint(&[2, -3, 0], 0, true), vec![]),
        (constraint(&[2, -3, 0], 0, false), vec![]),
        (constraint(&[-2, -3, 0], -1, false), vec![]),
        (constraint(&[0, 0, 0], 0, true), vec![]),
        (constraint(&[i64::MIN, 0, 0], 0, false), vec![0]),
    ];
    for (target, expected) in cases {
        assert_eq!(
            reduced(&problem(&[0, 0, 0], vec![], vec![target])).trap,
            expected
        );
    }
    let p = problem(
        &[0, 0],
        vec![],
        vec![constraint(&[1, 0], 0, true), constraint(&[0, -1], 0, false)],
    );
    assert_eq!(reduced(&p).trap, [0, 1]);
}

#[test]
fn projection_preserves_constant_constraints_and_order() {
    let p = problem(
        &[0, 1],
        vec![],
        vec![
            constraint(&[-1, 0], 0, false),
            constraint(&[7, 0], 1, false),
            constraint(&[0, 1], 1, true),
            constraint(&[0, 0], -2, true),
        ],
    );
    let q = reduced(&p);
    assert_eq!(q.places, [1]);
    assert_eq!(q.problem.target.len(), 4);
    for (new, old) in q.problem.target.iter().zip(&p.target) {
        assert_eq!(new.coefficients, [old.coefficients[1]]);
        assert_eq!(new.bound, old.bound);
        assert_eq!(new.equality, old.equality);
    }
    assert!(!q.problem.accepts(&[1]).unwrap());
}

#[test]
fn marked_trap_certificate_requires_initial_token() {
    let mut p = problem(
        &[1],
        vec![transition(&[(0, 2)], &[(0, 1)])],
        vec![constraint(&[-1], 0, false)],
    );
    let Preparation::Marked { trap } = target_zero_trap::prepare(&p, deadline(), 10_000).unwrap()
    else {
        panic!()
    };
    assert_eq!(trap, [0]);
    let proof = json!({"kind":"target-zero-trap-marked-v1","trap":trap});
    target_zero_trap::verify_marked(&p, &proof, deadline(), 10_000).unwrap();
    assert!(
        target_zero_trap::verify_reduction(
            &p,
            &json!({"kind":"target-zero-trap-v1","trap":[0],"inner":{}}),
            deadline(),
            10_000
        )
        .is_err()
    );
    p.initial[0] = 0;
    assert!(target_zero_trap::verify_marked(&p, &proof, deadline(), 10_000).is_err());
    assert!(
        target_zero_trap::verify_marked(
            &p,
            &json!({"kind":"target-zero-trap-marked-v1","trap":[]}),
            deadline(),
            10_000
        )
        .is_err()
    );
}

#[test]
fn checker_accepts_nonmaximal_traps_and_reconstructs_maps() {
    let p = problem(
        &[0, 0, 1],
        vec![transition(&[], &[(0, 1)]), transition(&[(2, 1)], &[(1, 1)])],
        vec![constraint(&[-1, -1, 0], 0, false)],
    );
    assert_eq!(reduced(&p).trap, [0, 1]);
    let proof = json!({"kind":"target-zero-trap-v1","trap":[],"inner":{"kind":"placeholder"}});
    let (q, inner) = target_zero_trap::verify_reduction(&p, &proof, deadline(), 10_000).unwrap();
    equal_problem(&p, &q.problem);
    assert_eq!(inner, &proof["inner"]);
    let p = problem(
        &[0, 0],
        vec![transition(&[], &[(0, 1)]), transition(&[], &[(1, 1)])],
        vec![constraint(&[1, 1], 0, true)],
    );
    assert_eq!(reduced(&p).trap, [0, 1]);
    let proof = json!({"kind":"target-zero-trap-v1","trap":[1],"inner":{}});
    let (q, _) = target_zero_trap::verify_reduction(&p, &proof, deadline(), 10_000).unwrap();
    assert_eq!(q.places, [0]);
    assert_eq!(q.transitions, [0]);
}

#[test]
fn rejects_malformed_or_unsound_certificates() {
    let p = problem(
        &[0, 0, 0],
        vec![transition(&[(1, 1)], &[(2, 1)])],
        vec![constraint(&[-1, -1, 0], 0, false)],
    );
    let valid = json!({"kind":"target-zero-trap-v1","trap":[0],"inner":{}});
    target_zero_trap::verify_reduction(&p, &valid, deadline(), 10_000).unwrap();
    let invalid: Vec<Value> = vec![
        json!({"kind":"target-zero-trap-v1","trap":[0]}),
        json!({"kind":"other","trap":[0],"inner":{}}),
        json!({"kind":"target-zero-trap-v1","trap":[0],"inner":{},"places":[]}),
        json!({"kind":"target-zero-trap-v1","trap":[0],"inner":null}),
        json!({"kind":"target-zero-trap-v1","trap":[0],"inner":[]}),
        json!({"kind":"target-zero-trap-v1","trap":"0","inner":{}}),
        json!({"kind":"target-zero-trap-v1","trap":[-1],"inner":{}}),
        json!({"kind":"target-zero-trap-v1","trap":[0.0],"inner":{}}),
        json!({"kind":"target-zero-trap-v1","trap":["0"],"inner":{}}),
        json!({"kind":"target-zero-trap-v1","trap":[true],"inner":{}}),
        json!({"kind":"target-zero-trap-v1","trap":[0,0],"inner":{}}),
        json!({"kind":"target-zero-trap-v1","trap":[1,0],"inner":{}}),
        json!({"kind":"target-zero-trap-v1","trap":[99],"inner":{}}),
        json!({"kind":"target-zero-trap-v1","trap":[2],"inner":{}}),
        json!({"kind":"target-zero-trap-v1","trap":[1],"inner":{}}),
    ];
    for proof in invalid {
        assert!(
            target_zero_trap::verify_reduction(&p, &proof, deadline(), 10_000).is_err(),
            "accepted {proof}"
        );
    }
    let p = problem(&[1], vec![], vec![constraint(&[1], 0, true)]);
    for proof in [
        json!({"kind":"target-zero-trap-marked-v1","trap":[0],"inner":{}}),
        json!({"kind":"target-zero-trap-marked-v1","trap":[0],"extra":0}),
    ] {
        assert!(target_zero_trap::verify_marked(&p, &proof, deadline(), 10_000).is_err());
    }
}

#[test]
fn validates_original_before_using_indices() {
    let base = problem(
        &[0],
        vec![transition(&[], &[])],
        vec![constraint(&[-1], 0, false)],
    );
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
    let proof = json!({"kind":"target-zero-trap-v1","trap":[],"inner":{}});
    for p in cases {
        assert!(target_zero_trap::prepare(&p, deadline(), 10_000).is_err());
        assert!(target_zero_trap::verify_reduction(&p, &proof, deadline(), 10_000).is_err());
    }
}

#[test]
fn witnesses_are_replayed_on_the_original_weighted_net() {
    let p = problem(
        &[0, 2, 0],
        vec![transition(&[], &[(0, 1)]), transition(&[(1, 2)], &[(2, 3)])],
        vec![
            constraint(&[-1, 0, 0], 0, false),
            constraint(&[0, 0, 1], 3, true),
        ],
    );
    let mut q = reduced(&p);
    assert_eq!(q.transitions, [1]);
    let (trace, marking) = q.lift_witness(&p, &[0], deadline(), 10_000).unwrap();
    assert_eq!(trace, [1]);
    assert_eq!(marking, [0, 0, 3]);
    assert_eq!(p.check_witness(&trace).unwrap(), marking);
    assert!(q.lift_witness(&p, &[], deadline(), 10_000).is_err());
    assert!(q.lift_witness(&p, &[1], deadline(), 10_000).is_err());
    assert!(q.lift_witness(&p, &[0, 0], deadline(), 10_000).is_err());
    q.transitions[0] = 0;
    assert!(q.lift_witness(&p, &[0], deadline(), 10_000).is_err());
    q.transitions[0] = 99;
    assert!(q.lift_witness(&p, &[0], deadline(), 10_000).is_err());
    let p = problem(&[0], vec![], vec![constraint(&[1], 0, true)]);
    assert_eq!(
        reduced(&p)
            .lift_witness(&p, &[], deadline(), 10_000)
            .unwrap(),
        (vec![], vec![0])
    );
}

#[test]
fn all_entrypoints_enforce_work_and_time_budgets() {
    let p = problem(&[0], vec![], vec![constraint(&[-1], 0, false)]);
    let q = reduced(&p);
    let proof = q
        .wrap_proof(json!({"kind":"inner"}), deadline(), 1000)
        .unwrap();
    let marked = json!({"kind":"target-zero-trap-marked-v1","trap":[0]});
    for (time, work) in [(deadline(), 0), (Instant::now(), 100_000)] {
        assert!(target_zero_trap::prepare(&p, time, work).is_err());
        assert!(target_zero_trap::verify_reduction(&p, &proof, time, work).is_err());
        assert!(target_zero_trap::verify_marked(&p, &marked, time, work).is_err());
        assert!(q.wrap_proof(json!({}), time, work).is_err());
        assert!(q.lift_witness(&p, &[], time, work).is_err());
    }
    assert!(q.wrap_proof(Value::Null, deadline(), 1000).is_err());
    let long = problem(
        &vec![0; 200],
        vec![],
        vec![constraint(&vec![-1; 200], 0, false)],
    );
    assert!(target_zero_trap::prepare(&long, deadline(), 300).is_err());
}

#[test]
fn draining_chain_fits_a_linear_work_budget() {
    let n = 2000;
    let transitions = (0..n)
        .map(|i| {
            transition(
                &[(i, 1)],
                &if i + 1 < n { vec![(i + 1, 1)] } else { vec![] },
            )
        })
        .collect();
    let p = problem(
        &vec![0; n],
        transitions,
        vec![constraint(&vec![-1; n], 0, false)],
    );
    let Preparation::Reduced(q) = target_zero_trap::prepare(&p, deadline(), n * 100).unwrap()
    else {
        panic!()
    };
    assert!(q.trap.is_empty());
    equal_problem(&p, &q.problem);
}

fn complete_reachable(p: &Problem) -> bool {
    let mut seen = HashSet::from([p.initial.clone()]);
    let mut todo = VecDeque::from([p.initial.clone()]);
    while let Some(marking) = todo.pop_front() {
        if p.accepts(&marking).unwrap() {
            return true;
        }
        for t in 0..p.transitions.len() {
            if let Some(next) = p.fire(&marking, t).unwrap() {
                assert!(next.iter().sum::<u64>() <= 2);
                if seen.insert(next.clone()) {
                    todo.push_back(next);
                }
            }
        }
    }
    false
}

#[test]
fn exhaustive_bounded_nets_preserve_reachability_and_find_the_greatest_trap() {
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
            if post.len() <= pre.len() {
                transitions.push(transition(pre, post));
            }
        }
    }
    for first in 0..transitions.len() {
        for second in first..transitions.len() {
            for initial_bits in 0..4 {
                for target_bits in 0..4 {
                    let initial = [initial_bits & 1, (initial_bits >> 1) & 1];
                    let target = vec![
                        constraint(&[1, 0], target_bits & 1, true),
                        constraint(&[0, 1], (target_bits >> 1) & 1, true),
                    ];
                    let p = problem(
                        &initial,
                        vec![transitions[first].clone(), transitions[second].clone()],
                        target,
                    );
                    let mut maximal = HashSet::new();
                    for bits in 0..4 {
                        let set: HashSet<usize> = (0..2).filter(|i| bits & (1 << i) != 0).collect();
                        if set.iter().any(|i| target_bits & (1 << i) != 0) {
                            continue;
                        }
                        if p.transitions.iter().all(|t| {
                            !t.pre.iter().any(|(i, _)| set.contains(i))
                                || t.post.iter().any(|(i, _)| set.contains(i))
                        }) {
                            maximal.extend(set);
                        }
                    }
                    let original = complete_reachable(&p);
                    let (trap, projected) = match target_zero_trap::prepare(&p, deadline(), 10_000)
                        .unwrap()
                    {
                        Preparation::Marked { trap } => {
                            let proof = json!({"kind":"target-zero-trap-marked-v1","trap":trap});
                            target_zero_trap::verify_marked(&p, &proof, deadline(), 10_000)
                                .unwrap();
                            (trap, false)
                        }
                        Preparation::Reduced(q) => {
                            let proof = q.wrap_proof(json!({}), deadline(), 10_000).unwrap();
                            let (checked, _) =
                                target_zero_trap::verify_reduction(&p, &proof, deadline(), 10_000)
                                    .unwrap();
                            equal_problem(&q.problem, &checked.problem);
                            let reachable = complete_reachable(&q.problem);
                            (q.trap, reachable)
                        }
                    };
                    assert_eq!(trap.into_iter().collect::<HashSet<_>>(), maximal);
                    assert_eq!(original, projected);
                }
            }
        }
    }
}
