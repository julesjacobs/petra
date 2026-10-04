use std::time::Duration;
use vass_reach::{
    interval,
    model::{Constraint, Problem, Transition},
    projection, search,
};

fn goal(n: usize, i: usize, value: i64) -> Constraint {
    let mut coefficients = vec![0; n];
    coefficients[i] = 1;
    Constraint {
        coefficients,
        bound: value,
        equality: true,
    }
}

#[test]
fn enabling_lower_bound_strengthens_state_equation() {
    let p = Problem {
        places: vec!["fuel".into(), "used".into(), "made".into()],
        initial: vec![2, 0, 0],
        transitions: vec![
            Transition {
                name: "use".into(),
                pre: vec![(0, 3)],
                post: vec![(0, 2), (1, 1)],
            },
            Transition {
                name: "make".into(),
                pre: vec![(0, 1)],
                post: vec![(0, 2), (2, 1)],
            },
        ],
        target: vec![Constraint {
            coefficients: vec![0, 1, -1],
            bound: 1,
            equality: false,
        }],
    };
    let out = interval::solve(&p, Duration::from_secs(1), 10000, 1000);
    assert_eq!(out.verdict, "unreachable");
    let proof = out.proof.unwrap();
    interval::verify_certificate(&p, &proof).unwrap();
    let mut bad = proof.clone();
    bad["regions"][0]["lower"][0] = serde_json::json!(3);
    assert!(interval::verify_certificate(&p, &bad).is_err());
    let mut p2 = p.clone();
    p2.transitions[0].pre = vec![(0, 2)];
    p2.transitions[0].post = vec![(0, 1), (1, 1)];
    assert!(interval::verify_certificate(&p2, &proof).is_err());
    assert_ne!(
        interval::solve(&p2, Duration::from_secs(1), 10000, 1000).verdict,
        "unreachable"
    );
}

#[test]
fn control_partition_proves_irreversible_phase_property() {
    let p = Problem {
        places: vec!["before".into(), "after".into(), "count".into()],
        initial: vec![1, 0, 0],
        transitions: vec![
            Transition {
                name: "switch".into(),
                pre: vec![(0, 1)],
                post: vec![(1, 1)],
            },
            Transition {
                name: "count".into(),
                pre: vec![(1, 1)],
                post: vec![(1, 1), (2, 1)],
            },
        ],
        target: vec![goal(3, 0, 1), goal(3, 2, 7)],
    };
    let out = interval::solve(&p, Duration::from_secs(1), 10000, 1000);
    assert_eq!(out.verdict, "unreachable");
    interval::verify_certificate(&p, out.proof.as_ref().unwrap()).unwrap();
    let mut bad = out.proof.unwrap();
    bad["regions"].as_array_mut().unwrap().pop();
    assert!(interval::verify_certificate(&p, &bad).is_err());
}

#[test]
fn projection_does_not_claim_abstract_witness_is_concrete() {
    let p = Problem {
        places: vec!["gate".into(), "target".into(), "noise".into()],
        initial: vec![0, 0, 0],
        transitions: vec![
            Transition {
                name: "blocked".into(),
                pre: vec![(0, 1)],
                post: vec![(1, 1)],
            },
            Transition {
                name: "noise".into(),
                pre: vec![],
                post: vec![(2, 1)],
            },
        ],
        target: vec![goal(3, 1, 1)],
    };
    assert!(projection::project(&p, &[0]).is_err());
    let out = projection::solve(&p, Duration::from_secs(1), 1000);
    assert_eq!(out.verdict, "unreachable");
    projection::verify_certificate(&p, out.proof.as_ref().unwrap()).unwrap();
    let mut bad = out.proof.unwrap();
    bad["places"] = serde_json::json!([2]);
    assert!(projection::verify_certificate(&p, &bad).is_err());
}

#[test]
fn differential_invariants_on_bounded_nets() {
    let mut seed = 713u64;
    let mut next = || {
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        (seed >> 32) as usize
    };
    for case in 0..100 {
        let n = 3 + next() % 3;
        let mut initial = vec![0; n];
        initial[next() % n] = 1;
        initial[next() % n] += 1;
        let transitions = (0..5)
            .map(|t| {
                let a = next() % n;
                let b = next() % n;
                Transition {
                    name: format!("t{t}"),
                    pre: vec![(a, 1)],
                    post: vec![(b, 1)],
                }
            })
            .collect();
        let target = vec![goal(n, next() % n, (next() % 4) as i64)];
        let p = Problem {
            places: (0..n).map(|i| format!("p{i}")).collect(),
            initial,
            transitions,
            target,
        };
        let exact = search::solve(&p, false, Duration::from_secs(1), 1000);
        assert_ne!(exact.verdict, "unknown");
        for result in [
            interval::solve(&p, Duration::from_millis(100), 10000, 1000),
            projection::solve(&p, Duration::from_millis(100), 1000),
        ] {
            if result.verdict == "reachable" {
                assert_eq!(exact.verdict, "reachable", "case {case}");
                p.check_witness(&result.trace).unwrap();
            }
            if result.verdict == "unreachable" {
                assert_eq!(exact.verdict, "unreachable", "case {case}");
                if result.method == "interval-invariant" {
                    interval::verify_certificate(&p, &result.proof.unwrap()).unwrap();
                } else {
                    projection::verify_certificate(&p, &result.proof.unwrap()).unwrap();
                }
            }
        }
    }
}
