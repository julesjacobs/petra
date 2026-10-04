use serde_json::json;
use std::time::Duration;
use vass_reach::{
    cegar,
    model::{Constraint, Problem, Transition},
    search,
};

fn problem(initial: Vec<u64>, transitions: Vec<Transition>, target: Vec<Constraint>) -> Problem {
    let p = Problem {
        places: (0..initial.len()).map(|i| format!("p{i}")).collect(),
        initial,
        transitions,
        target,
    };
    p.validate().unwrap();
    p
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

fn check(p: &Problem, expected: &str) -> search::Outcome {
    let out = cegar::solve(p, Duration::from_secs(2), 100_000);
    assert_eq!(out.verdict, expected, "{}", out.reason);
    match expected {
        "reachable" => assert_eq!(
            p.check_witness(&out.trace).unwrap(),
            out.marking.clone().unwrap()
        ),
        "unreachable" => cegar::verify_certificate(p, out.proof.as_ref().unwrap()).unwrap(),
        _ => panic!("expected a definitive verdict"),
    }
    out
}

#[test]
fn decrements_exit_high_bucket() {
    let p = problem(
        vec![4],
        vec![transition(&[(0, 1)], &[])],
        vec![constraint(&[1], 0, true)],
    );
    let out = check(&p, "reachable");
    assert_eq!(out.trace.len(), 4);
}

#[test]
fn high_bucket_can_enable_larger_precondition() {
    let p = problem(
        vec![4, 0],
        vec![transition(&[(0, 4)], &[(1, 1)])],
        vec![constraint(&[0, 1], 1, true)],
    );
    check(&p, "reachable");
}

#[test]
fn spurious_initial_target_is_refined() {
    let p = problem(vec![3], vec![], vec![constraint(&[1], 4, true)]);
    let out = check(&p, "unreachable");
    assert!(out.proof.unwrap()["thresholds"][0].as_u64().unwrap() > 3);
}

#[test]
fn spurious_disabled_path_is_refined() {
    let p = problem(
        vec![2, 0],
        vec![transition(&[(0, 3)], &[(1, 1)])],
        vec![constraint(&[0, 1], 1, false)],
    );
    check(&p, "unreachable");
}

#[test]
fn read_arc_keeps_enabling_requirement() {
    let transitions = vec![transition(&[(0, 2)], &[(0, 2), (1, 1)])];
    let target = vec![constraint(&[0, 1], 1, false)];
    check(
        &problem(vec![1, 0], transitions.clone(), target.clone()),
        "unreachable",
    );
    check(&problem(vec![2, 0], transitions, target), "reachable");
}

#[test]
fn signed_equality_target_requires_refinement() {
    let transitions = vec![transition(&[(0, 1)], &[(1, 1)])];
    check(
        &problem(
            vec![4, 0],
            transitions.clone(),
            vec![constraint(&[1, -1], 0, true)],
        ),
        "reachable",
    );
    check(
        &problem(vec![4, 0], transitions, vec![constraint(&[1, -1], 1, true)]),
        "unreachable",
    );
}

#[test]
fn incompatible_conjunction_is_not_a_witness() {
    let p = problem(
        vec![2],
        vec![],
        vec![constraint(&[1], 3, false), constraint(&[-1], -2, false)],
    );
    check(&p, "unreachable");
}

#[test]
fn exhausted_budgets_are_unknown() {
    let p = problem(vec![2], vec![], vec![constraint(&[1], 3, false)]);
    for (time, states) in [
        (Duration::ZERO, 100),
        (Duration::from_secs(1), 0),
        (Duration::from_secs(1), 1),
    ] {
        let out = cegar::solve(&p, time, states);
        assert_eq!(out.verdict, "unknown");
        assert!(out.proof.is_none());
    }
}

#[test]
fn forged_closures_are_rejected() {
    let p = problem(
        vec![2, 0],
        vec![transition(&[(0, 1)], &[(1, 1)])],
        vec![constraint(&[0, 1], 2, false)],
    );
    for proof in [
        json!({"kind":"threshold-closure-v1","thresholds":[1,1],"states":[[1,0]]}),
        json!({"kind":"threshold-closure-v1","thresholds":[1,1],"states":[[1,0],[1,1],[0,1]]}),
        json!({"kind":"threshold-closure-v1","thresholds":[0,1],"states":[[0,0]]}),
        json!({"kind":"threshold-closure-v1","thresholds":[1,1],"states":[[1]]}),
        json!({"kind":"threshold-closure-v1","thresholds":[1,1],"states":[]}),
    ] {
        assert!(cegar::verify_certificate(&p, &proof).is_err());
    }
}

#[test]
fn bounded_nets_agree_with_bfs() {
    let mut seed = 0x31415926_u64;
    let mut next = || {
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        seed >> 32
    };
    for case in 0..180 {
        let mut transitions = vec![];
        for _ in 0..4 {
            let from = next() as usize % 3;
            let to = next() as usize % 3;
            let weight = 1 + next() % 2;
            transitions.push(transition(&[(from, weight)], &[(to, weight)]));
        }
        let coefficients: Vec<_> = (0..3).map(|_| (next() % 5) as i64 - 2).collect();
        let bound = (next() % 13) as i64 - 6;
        let p = problem(
            vec![3, 0, 0],
            transitions,
            vec![constraint(&coefficients, bound, case % 2 == 0)],
        );
        let exact = search::solve(&p, false, Duration::from_secs(2), 1000);
        assert_ne!(exact.verdict, "unknown");
        check(&p, exact.verdict);
    }
}
