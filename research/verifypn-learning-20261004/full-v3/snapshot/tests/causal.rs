use serde_json::{Value, json};
use std::time::Duration;
use vass_reach::{
    causal,
    model::{Constraint, Problem, Transition},
    search,
};

fn catalyst() -> Problem {
    Problem {
        places: vec!["permit".into(), "result".into()],
        initial: vec![0, 0],
        transitions: vec![Transition {
            name: "produce".into(),
            pre: vec![(0, 1)],
            post: vec![(0, 1), (1, 1)],
        }],
        target: vec![Constraint {
            coefficients: vec![0, 1],
            bound: 1,
            equality: false,
        }],
    }
}

fn catalyst_certificate() -> Value {
    json!({
        "kind": "causal-state-equation-v1",
        "root": {
            "rule": "support", "places": [], "blocked": 0,
            "omit": {"rule": "farkas", "multipliers": [[2,"1"],[3,"1"]]},
            "enter": {"rule": "farkas", "multipliers": [[3,"1"]]}
        }
    })
}

fn support_nodes(node: &Value) -> usize {
    if node["rule"] == "support" {
        1 + support_nodes(&node["omit"]) + support_nodes(&node["enter"])
    } else {
        0
    }
}

#[test]
fn empty_catalyst_has_a_checked_causal_refutation() {
    let p = catalyst();
    causal::verify_certificate(&p, &catalyst_certificate()).unwrap();
    let out = causal::solve(&p, Duration::from_secs(2), 1000);
    assert_eq!(out.verdict, "unreachable");
    let certificate = out.proof.unwrap();
    causal::verify_certificate(&p, &certificate).unwrap();
    assert!(support_nodes(&certificate["root"]) >= 1);
}

#[test]
fn alternative_missing_catalysts_require_nested_cuts() {
    let p = Problem {
        places: vec!["a".into(), "b".into(), "result".into()],
        initial: vec![0, 0, 0],
        transitions: (0..2)
            .map(|i| Transition {
                name: format!("produce{i}"),
                pre: vec![(i, 1)],
                post: vec![(i, 1), (2, 1)],
            })
            .collect(),
        target: vec![Constraint {
            coefficients: vec![0, 0, 1],
            bound: 1,
            equality: false,
        }],
    };
    let out = causal::solve(&p, Duration::from_secs(2), 1000);
    assert_eq!(out.verdict, "unreachable");
    let certificate = out.proof.unwrap();
    causal::verify_certificate(&p, &certificate).unwrap();
    assert!(support_nodes(&certificate["root"]) >= 2);
}

#[test]
fn source_transition_enables_a_repeated_read_catalyst() {
    let mut p = catalyst();
    p.target[0].bound = 4;
    p.target[0].equality = true;
    p.transitions.push(Transition {
        name: "enable".into(),
        pre: vec![],
        post: vec![(0, 1)],
    });
    let out = causal::solve(&p, Duration::from_secs(2), 1000);
    assert_eq!(out.verdict, "reachable");
    p.check_witness(&out.trace).unwrap();
    assert_eq!(out.trace.iter().filter(|&&t| t == 0).count(), 4);
    assert_eq!(out.trace.first(), Some(&1));
}

#[test]
fn long_catalyst_chain_has_a_replayed_witness() {
    let places = 65;
    let p = Problem {
        places: (0..places).map(|i| format!("catalyst_{i}")).collect(),
        initial: vec![0; places],
        transitions: (0..places)
            .map(|i| {
                let pre = if i == 0 { vec![] } else { vec![(i - 1, 1)] };
                let mut post = pre.clone();
                post.push((i, 1));
                Transition {
                    name: format!("enable_{i}"),
                    pre,
                    post,
                }
            })
            .collect(),
        target: vec![Constraint {
            coefficients: (0..places).map(|i| i64::from(i == places - 1)).collect(),
            bound: 1,
            equality: false,
        }],
    };
    let out = causal::solve(&p, Duration::from_secs(5), 1000);
    assert_eq!(out.verdict, "reachable", "{}", out.reason);
    p.check_witness(&out.trace).unwrap();
    assert_eq!(out.trace.len(), places);
}

#[test]
fn qualitative_support_does_not_prove_weighted_enabling() {
    let mut p = catalyst();
    p.initial[0] = 1;
    p.transitions[0].pre[0].1 = 2;
    p.transitions[0].post[0].1 = 2;
    let out = causal::solve(&p, Duration::from_secs(2), 1000);
    assert_eq!(out.verdict, "unknown");
    assert!(out.proof.is_none());
}

#[test]
fn integer_model_failure_is_not_a_rational_refutation() {
    let p = Problem {
        places: vec!["p".into()],
        initial: vec![0],
        transitions: vec![Transition {
            name: "add_two".into(),
            pre: vec![],
            post: vec![(0, 2)],
        }],
        target: vec![Constraint {
            coefficients: vec![1],
            bound: 1,
            equality: true,
        }],
    };
    let out = causal::solve(&p, Duration::from_secs(2), 1000);
    assert_eq!(out.verdict, "unknown");
    assert!(out.proof.is_none());
}

#[test]
fn initial_target_has_an_empty_replayed_witness() {
    let mut p = catalyst();
    p.initial[1] = 1;
    p.transitions.clear();
    let out = causal::solve(&p, Duration::from_secs(1), 100);
    assert_eq!(out.verdict, "reachable");
    assert!(out.trace.is_empty());
    p.check_witness(&out.trace).unwrap();
}

#[test]
fn refuting_one_alternative_does_not_refute_an_unresolved_sibling() {
    let p = Problem {
        places: vec!["absent".into(), "insufficient".into(), "result".into()],
        initial: vec![0, 1, 0],
        transitions: vec![
            Transition {
                name: "missing_catalyst".into(),
                pre: vec![(0, 1)],
                post: vec![(0, 1), (2, 1)],
            },
            Transition {
                name: "weighted_catalyst".into(),
                pre: vec![(1, 2)],
                post: vec![(1, 2), (2, 1)],
            },
        ],
        target: vec![Constraint {
            coefficients: vec![0, 0, 1],
            bound: 1,
            equality: false,
        }],
    };
    let out = causal::solve(&p, Duration::from_secs(2), 1000);
    assert_eq!(out.verdict, "unknown");
    assert!(out.proof.is_none());
}

#[test]
fn count_cap_cannot_refute_a_long_witness() {
    let p = Problem {
        places: vec!["p".into()],
        initial: vec![0],
        transitions: vec![Transition {
            name: "increment".into(),
            pre: vec![],
            post: vec![(0, 1)],
        }],
        target: vec![Constraint {
            coefficients: vec![1],
            bound: 8193,
            equality: true,
        }],
    };
    let out = causal::solve(&p, Duration::from_secs(2), 100);
    assert_eq!(out.verdict, "unknown");
    assert!(out.proof.is_none());
}

#[test]
fn checker_rejects_malformed_and_one_sided_proofs() {
    let p = catalyst();
    let original = catalyst_certificate();
    for (pointer, replacement) in [
        ("/kind", json!("another-proof")),
        ("/root/rule", json!("unknown-rule")),
        ("/root/blocked", json!(100)),
        ("/root/blocked", json!(-1)),
        ("/root/places", json!([2])),
        ("/root/places", json!([1, 1])),
        ("/root/places", json!([1, 0])),
        ("/root/places", json!([0])),
        ("/root/omit", Value::Null),
        ("/root/enter", Value::Null),
        ("/root/omit/multipliers", json!([])),
        ("/root/omit/multipliers", json!([[2, "1"]])),
        ("/root/omit/multipliers", json!([[3, "1"], [2, "1"]])),
        ("/root/omit/multipliers", json!([[2, "1"], [2, "1"]])),
        ("/root/enter/multipliers", json!([[4, "1"]])),
        ("/root/enter/multipliers", json!([[3, "0"]])),
        ("/root/enter/multipliers", json!([[3, "-1"]])),
        ("/root/enter/multipliers", json!([[3, "1/0"]])),
        ("/root/enter/multipliers", json!([[3, "NaN"]])),
    ] {
        let mut proof = original.clone();
        *proof.pointer_mut(pointer).unwrap() = replacement;
        assert!(
            causal::verify_certificate(&p, &proof).is_err(),
            "accepted mutation {pointer}: {proof}"
        );
    }
    let mut missing = original.clone();
    missing["root"].as_object_mut().unwrap().remove("enter");
    assert!(causal::verify_certificate(&p, &missing).is_err());
    let mut extra = original;
    extra["root"]["frontier"] = json!([]);
    assert!(causal::verify_certificate(&p, &extra).is_err());
}

#[test]
fn checker_reconstructs_initial_support_and_complete_frontier() {
    let proof = catalyst_certificate();
    let mut p = catalyst();
    p.initial[0] = 1;
    assert!(causal::verify_certificate(&p, &proof).is_err());
    p.initial[0] = 0;
    p.transitions.push(Transition {
        name: "enable".into(),
        pre: vec![],
        post: vec![(0, 1)],
    });
    assert!(causal::verify_certificate(&p, &proof).is_err());
    p.transitions.pop();
    p.transitions[0].pre.clear();
    assert!(causal::verify_certificate(&p, &proof).is_err());
}

#[test]
fn zero_resources_return_unknown_without_a_proof() {
    let p = catalyst();
    for (timeout, states) in [(Duration::ZERO, 1000), (Duration::from_secs(1), 0)] {
        let out = causal::solve(&p, timeout, states);
        assert_eq!(out.verdict, "unknown");
        assert!(out.proof.is_none());
    }
}

#[test]
fn finite_conservative_nets_agree_with_exhaustive_search() {
    for seed in 0..32usize {
        let size = 3 + seed % 3;
        let mut p = Problem {
            places: (0..size).map(|i| format!("p{i}")).collect(),
            initial: (0..size).map(|i| u64::from(i == 0)).collect(),
            transitions: (0..size)
                .filter(|i| (i + seed) % 4 != 0)
                .map(|i| Transition {
                    name: format!("move{i}"),
                    pre: vec![(i, 1)],
                    post: vec![((i + 1) % size, 1)],
                })
                .collect(),
            target: vec![Constraint {
                coefficients: (0..size).map(|i| i64::from(i == size - 1)).collect(),
                bound: 1,
                equality: true,
            }],
        };
        if seed % 2 == 0 {
            let mut pre = vec![(0, 1)];
            let mut post = vec![(size - 1, 1)];
            pre.push((1, 1));
            post.push((1, 1));
            p.transitions.push(Transition {
                name: "read_shortcut".into(),
                pre,
                post,
            });
        }
        p.validate().unwrap();
        let oracle = search::solve(&p, false, Duration::from_secs(1), 1000);
        assert_ne!(oracle.verdict, "unknown");
        let out = causal::solve(&p, Duration::from_secs(1), 1000);
        match out.verdict {
            "reachable" => {
                assert_eq!(oracle.verdict, "reachable", "seed {seed}");
                p.check_witness(&out.trace).unwrap();
            }
            "unreachable" => {
                assert_eq!(oracle.verdict, "unreachable", "seed {seed}");
                causal::verify_certificate(&p, out.proof.as_ref().unwrap()).unwrap();
            }
            "unknown" => assert!(out.proof.is_none()),
            other => panic!("unexpected verdict {other}"),
        }
    }
}
