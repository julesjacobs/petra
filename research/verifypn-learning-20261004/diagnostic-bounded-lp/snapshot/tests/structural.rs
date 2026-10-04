use std::time::Duration;
use vass_reach::{
    model::{Constraint, Problem, Transition},
    structural,
};
fn transition(pre: &[(usize, u64)], post: &[(usize, u64)]) -> Transition {
    Transition {
        name: "t".into(),
        pre: pre.to_vec(),
        post: post.to_vec(),
    }
}
fn cyclic_consumption() -> Problem {
    Problem {
        places: vec!["a".into(), "b".into()],
        initial: vec![1, 0],
        transitions: vec![
            transition(&[(0, 2)], &[(1, 1)]),
            transition(&[(1, 2)], &[(0, 1)]),
        ],
        target: vec![Constraint {
            coefficients: vec![1, 1],
            bound: 0,
            equality: true,
        }],
    }
}
#[test]
fn marked_trap_refutes_feasible_rational_state_equation() {
    let p = cyclic_consumption();
    assert_eq!(
        vass_reach::state_equation::solve(&p, Duration::from_secs(1), 1000).verdict,
        "unknown"
    );
    let out = structural::solve(&p, Duration::from_secs(1), 1000);
    assert_eq!(out.verdict, "unreachable");
    assert!(out.certificate.is_none());
    structural::verify_certificate(&p, out.proof.as_ref().unwrap()).unwrap();
    let mut forged = out.proof.unwrap();
    forged["traps"] = serde_json::json!([[0]]);
    assert!(structural::verify_certificate(&p, &forged).is_err());
}
#[test]
fn trap_checker_checks_arcs_marking_and_indices() {
    let p = cyclic_consumption();
    assert!(structural::verify_trap(&p, &[0, 1]).is_ok());
    for invalid in [vec![], vec![1], vec![0], vec![0, 0, 1], vec![0, 2]] {
        assert!(structural::verify_trap(&p, &invalid).is_err());
    }
    let mut drain = p.clone();
    drain.transitions.push(transition(&[(0, 1)], &[]));
    assert!(structural::verify_trap(&drain, &[0, 1]).is_err());
}
#[test]
fn larger_marked_traps_are_discovered() {
    let p = Problem {
        places: vec!["a".into(), "b".into(), "c".into()],
        initial: vec![1, 0, 0],
        transitions: vec![
            transition(&[(0, 2)], &[(1, 1)]),
            transition(&[(1, 2)], &[(2, 1)]),
            transition(&[(2, 2)], &[(0, 1)]),
        ],
        target: vec![Constraint {
            coefficients: vec![1, 1, 1],
            bound: 0,
            equality: true,
        }],
    };
    let out = structural::solve(&p, Duration::from_secs(1), 1000);
    assert_eq!(out.verdict, "unreachable");
    structural::verify_certificate(&p, out.proof.as_ref().unwrap()).unwrap();
}
#[test]
fn no_false_refutation_on_reachable_targets() {
    for source in 0..3 {
        for destination in 0..3 {
            for read in 0..3 {
                let mut initial = vec![1; 3];
                initial[source] += 1;
                let mut pre = vec![(source, 1)];
                let mut post = vec![(destination, 1)];
                if read != source && read != destination {
                    pre.push((read, 1));
                    post.push((read, 1));
                }
                let transitions = vec![transition(&pre, &post)];
                let mut p = Problem {
                    places: vec!["a".into(), "b".into(), "c".into()],
                    initial,
                    transitions,
                    target: vec![],
                };
                let goal = p.fire(&p.initial, 0).unwrap().unwrap();
                p.target = goal
                    .iter()
                    .enumerate()
                    .map(|(i, &value)| {
                        let mut coefficients = vec![0; 3];
                        coefficients[i] = 1;
                        Constraint {
                            coefficients,
                            bound: value as i64,
                            equality: true,
                        }
                    })
                    .collect();
                assert_ne!(
                    structural::solve(&p, Duration::from_secs(1), 1000).verdict,
                    "unreachable"
                );
            }
        }
    }
}
#[test]
fn limits_never_claim_unreachability() {
    let p = cyclic_consumption();
    assert_eq!(
        structural::solve(&p, Duration::ZERO, 1000).verdict,
        "unknown"
    );
    assert_eq!(
        structural::solve(&p, Duration::from_secs(1), 0).verdict,
        "unknown"
    );
}

#[test]
fn empty_siphon_blocks_spontaneous_cycles() {
    let p = Problem {
        places: vec!["a".into(), "b".into()],
        initial: vec![0, 0],
        transitions: vec![
            transition(&[(0, 1)], &[(1, 2)]),
            transition(&[(1, 1)], &[(0, 2)]),
        ],
        target: vec![Constraint {
            coefficients: vec![1, 1],
            bound: 1,
            equality: false,
        }],
    };
    assert_eq!(
        vass_reach::state_equation::solve(&p, Duration::from_secs(1), 1000).verdict,
        "unknown"
    );
    let out = structural::solve_support(&p, Duration::from_secs(1), 1000);
    assert_eq!(out.verdict, "unreachable");
    structural::verify_support_certificate(&p, out.proof.as_ref().unwrap()).unwrap();
    let mut enabled = p.clone();
    enabled.transitions.push(transition(&[], &[(0, 1)]));
    assert!(structural::verify_support_certificate(&enabled, out.proof.as_ref().unwrap()).is_err());
    assert_eq!(
        structural::solve_support(&enabled, Duration::from_secs(1), 1000).verdict,
        "unknown"
    );
}

#[test]
fn bounded_weighted_nets_match_independent_reachable_closure() {
    let mut seed = 821935u64;
    let mut random = || {
        seed ^= seed << 13;
        seed ^= seed >> 7;
        seed ^= seed << 17;
        seed as usize
    };
    for _ in 0..100 {
        let mut initial = vec![0u64; 3];
        for _ in 0..4 {
            initial[random() % 3] += 1;
        }
        let transitions = (0..4)
            .map(|_| {
                let source = random() % 3;
                let destination = random() % 3;
                let weight = (random() % 3 + 1) as u64;
                let read = random() % 3;
                let mut pre = vec![0; 3];
                let mut post = vec![0; 3];
                pre[source] += weight;
                post[destination] += weight;
                pre[read] += 1;
                post[read] += 1;
                let arcs = |dense: Vec<u64>| {
                    dense
                        .into_iter()
                        .enumerate()
                        .filter(|&(_, v)| v != 0)
                        .collect::<Vec<_>>()
                };
                transition(&arcs(pre), &arcs(post))
            })
            .collect::<Vec<_>>();
        let target = (0..2)
            .map(|_| Constraint {
                coefficients: (0..3).map(|_| (random() % 5) as i64 - 2).collect(),
                bound: (random() % 9) as i64 - 4,
                equality: random() % 2 == 0,
            })
            .collect();
        let p = Problem {
            places: vec!["a".into(), "b".into(), "c".into()],
            initial: initial.clone(),
            transitions,
            target,
        };
        p.validate().unwrap();
        let mut closure = std::collections::HashSet::from([initial]);
        loop {
            let before = closure.len();
            for marking in closure.clone() {
                for t in &p.transitions {
                    let mut input = [0; 3];
                    let mut output = [0; 3];
                    for &(i, w) in &t.pre {
                        input[i] = w;
                    }
                    for &(i, w) in &t.post {
                        output[i] = w;
                    }
                    if (0..3).all(|i| marking[i] >= input[i]) {
                        closure.insert((0..3).map(|i| marking[i] - input[i] + output[i]).collect());
                    }
                }
            }
            if before == closure.len() {
                break;
            }
        }
        let reachable = closure.iter().any(|marking| {
            p.target.iter().all(|c| {
                let sum: i64 = c
                    .coefficients
                    .iter()
                    .zip(marking)
                    .map(|(&a, &b)| a * b as i64)
                    .sum();
                if c.equality {
                    sum == c.bound
                } else {
                    sum >= c.bound
                }
            })
        });
        for support in [false, true] {
            let out = if support {
                structural::solve_support(&p, Duration::from_secs(1), 1000)
            } else {
                structural::solve(&p, Duration::from_secs(1), 1000)
            };
            if out.verdict == "unreachable" {
                assert!(!reachable);
                let proof = out.proof.as_ref().unwrap();
                if support {
                    structural::verify_support_certificate(&p, proof).unwrap();
                } else {
                    structural::verify_certificate(&p, proof).unwrap();
                }
            }
        }
    }
}

#[test]
fn invariants_hold_with_unbounded_independent_growth() {
    let mut p = cyclic_consumption();
    p.places.push("unbounded".into());
    p.initial.push(0);
    p.target[0].coefficients.push(0);
    p.transitions.push(transition(&[], &[(2, 1)]));
    let out = structural::solve(&p, Duration::from_secs(1), 1000);
    assert_eq!(out.verdict, "unreachable");
    structural::verify_certificate(&p, out.proof.as_ref().unwrap()).unwrap();
    p.target = vec![
        Constraint {
            coefficients: vec![1, 0, 0],
            bound: 1,
            equality: true,
        },
        Constraint {
            coefficients: vec![0, 0, 1],
            bound: 1000000,
            equality: false,
        },
    ];
    assert_eq!(
        structural::solve(&p, Duration::from_secs(1), 1000).verdict,
        "unknown"
    );
    assert_eq!(
        structural::solve_support(&p, Duration::from_secs(1), 1000).verdict,
        "unknown"
    );
}
