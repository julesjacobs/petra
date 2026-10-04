use std::time::Duration;
use vass_reach::{
    local_closure,
    model::{Constraint, Problem, Transition},
    search,
};

fn row(coefficients: Vec<i64>, bound: i64, equality: bool) -> Constraint {
    Constraint {
        coefficients,
        bound,
        equality,
    }
}
fn problem(initial: Vec<u64>, target: Vec<Constraint>) -> Problem {
    Problem {
        places: (0..initial.len()).map(|i| format!("p{i}")).collect(),
        initial,
        transitions: vec![],
        target,
    }
}
fn transition(pre: Vec<(usize, u64)>, post: Vec<(usize, u64)>) -> Transition {
    Transition {
        name: "t".into(),
        pre,
        post,
    }
}
fn negative(p: &Problem) -> serde_json::Value {
    let out = local_closure::solve(p, Duration::from_secs(2), 10_000);
    assert_eq!(out.verdict, "unreachable", "{}", out.reason);
    let proof = out.proof.unwrap();
    local_closure::verify_certificate(p, &proof).unwrap();
    proof
}

#[test]
fn omitted_negative_terms_give_necessary_constraints() {
    let mut p = problem(vec![0, 0], vec![row(vec![1, -1], 1, false)]);
    p.transitions.push(transition(vec![], vec![(1, 1)]));
    let local = local_closure::necessary_projection(&p, &[0]).unwrap();
    assert_eq!(local.target[0].coefficients, vec![1]);
    assert_eq!(local.target[0].bound, 1);
    negative(&p);
}

#[test]
fn omitted_positive_terms_discard_the_constraint() {
    let mut p = problem(vec![0, 0], vec![row(vec![1, 1], 1, false)]);
    p.transitions.push(transition(vec![], vec![(1, 1)]));
    assert!(
        local_closure::necessary_projection(&p, &[0])
            .unwrap()
            .target
            .is_empty()
    );
    assert_eq!(
        local_closure::solve(&p, Duration::from_secs(1), 100).verdict,
        "unknown"
    );
}

#[test]
fn equality_directions_and_minimum_integers() {
    let p = problem(vec![0, 0], vec![row(vec![-1, 1], -1, true)]);
    let local = local_closure::necessary_projection(&p, &[0]).unwrap();
    assert_eq!(local.target.len(), 1);
    assert_eq!(local.target[0].coefficients, vec![1]);
    assert_eq!(local.target[0].bound, 1);
    assert!(!local.target[0].equality);
    negative(&p);
    let p = problem(vec![1], vec![row(vec![i64::MIN], i64::MIN, true)]);
    let local = local_closure::necessary_projection(&p, &[0]).unwrap();
    assert_eq!(local.target.len(), 1);
    assert_eq!(local.target[0].coefficients, vec![i64::MIN]);
    assert_eq!(
        local_closure::solve(&p, Duration::from_secs(1), 100).verdict,
        "unknown"
    );
    let p = problem(vec![0], vec![row(vec![0], i64::MIN, true)]);
    let local = local_closure::necessary_projection(&p, &[0]).unwrap();
    assert_eq!(local.target.len(), 1);
    assert_eq!(local.target[0].bound, i64::MIN);
}

#[test]
fn globally_read_only_transitions_do_not_join_components() {
    let mut p = problem(vec![0, 1], vec![row(vec![1, -1], 1, false)]);
    p.transitions
        .push(transition(vec![(1, 1), (0, 1)], vec![(0, 1), (1, 1)]));
    p.transitions.push(transition(vec![(1, 1)], vec![(1, 2)]));
    p.transitions.push(p.transitions[1].clone());
    let proof = negative(&p);
    assert_eq!(proof["places"], serde_json::json!([0]));
    let mut tampered = proof.clone();
    tampered["places"] = serde_json::json!([1]);
    assert!(local_closure::verify_certificate(&p, &tampered).is_err());
    tampered["places"] = serde_json::json!([0, 0]);
    assert!(local_closure::verify_certificate(&p, &tampered).is_err());
    p.transitions.push(transition(vec![(0, 1), (0, 1)], vec![]));
    assert_eq!(
        local_closure::solve(&p, Duration::from_secs(1), 100).verdict,
        "unknown"
    );
}

#[test]
fn local_positive_with_dropped_guard_proves_nothing() {
    let mut p = problem(vec![0, 0], vec![row(vec![1, 0], 1, false)]);
    p.transitions.push(transition(vec![(1, 1)], vec![(0, 1)]));
    let local = local_closure::necessary_projection(&p, &[0]).unwrap();
    assert_eq!(
        search::solve(&local, false, Duration::from_secs(1), 100).verdict,
        "reachable"
    );
    let mut forged = serde_json::json!({"kind":"local-closure-v1", "places":[0],
        "closure":{"kind":"threshold-closure-v1", "thresholds":[2], "states":[[0]]}});
    assert!(local_closure::verify_certificate(&p, &forged).is_err());
    forged["closure"]["states"] = serde_json::json!([[0], [1], [2]]);
    assert!(local_closure::verify_certificate(&p, &forged).is_err());
}

#[test]
fn bounded_differential_negative_soundness() {
    let mut seed = 831u64;
    for _ in 0..64 {
        let mut next = || {
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            seed >> 32
        };
        let mut p = problem(
            vec![3, 0, 2, 0],
            vec![
                row(vec![1, -1, -1, 0], (next() % 7) as i64 - 3, next() % 2 == 0),
                row(vec![0, 0, 0, 1], (next() % 4) as i64, next() % 2 == 0),
            ],
        );
        for _ in 0..8 {
            let base = 2 * (next() as usize % 2);
            let a = base + next() as usize % 2;
            let b = base + next() as usize % 2;
            let w = next() % 2 + 1;
            p.transitions.push(transition(vec![(a, w)], vec![(b, w)]));
        }
        let reference = search::solve(&p, false, Duration::from_secs(1), 1000);
        assert_ne!(reference.verdict, "unknown");
        let out = local_closure::solve(&p, Duration::from_secs(1), 1000);
        assert_ne!(out.verdict, "reachable");
        if out.verdict == "unreachable" {
            assert_eq!(reference.verdict, "unreachable");
            local_closure::verify_certificate(&p, &out.proof.unwrap()).unwrap();
        }
    }
}
