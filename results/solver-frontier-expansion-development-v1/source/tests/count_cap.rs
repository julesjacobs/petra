use std::time::Duration;
use vass_reach::{
    count_plan,
    model::{Constraint, Problem, Transition},
};
#[test]
fn count_cap_exhaustion_remains_unknown() {
    let p = Problem {
        places: vec!["p".into()],
        initial: vec![0],
        transitions: vec![Transition {
            name: "produce".into(),
            pre: vec![],
            post: vec![(0, 1)],
        }],
        target: vec![Constraint {
            coefficients: vec![1],
            bound: 3,
            equality: true,
        }],
    };
    for cap in [0, 2, u32::MAX] {
        assert_eq!(
            count_plan::solve_sparse_with_cap(&p, Duration::from_secs(1), 100, cap).verdict,
            "unknown"
        );
    }
    let out = count_plan::solve_sparse_with_cap(&p, Duration::from_secs(1), 100, 3);
    assert_eq!(out.verdict, "reachable");
    p.check_witness(&out.trace).unwrap();
}

#[test]
fn state_budget_reserves_the_final_acceptance_check() {
    let mut p = Problem {
        places: vec!["p".into()],
        initial: vec![0],
        transitions: vec![Transition {
            name: "produce".into(),
            pre: vec![],
            post: vec![(0, 1)],
        }],
        target: vec![Constraint {
            coefficients: vec![1],
            bound: 3,
            equality: true,
        }],
    };
    for budget in [0, 1, 3] {
        assert_eq!(
            count_plan::solve_sparse_with_state_budget(&p, Duration::from_secs(1), budget).verdict,
            "unknown"
        );
    }
    let out = count_plan::solve_sparse_with_state_budget(&p, Duration::from_secs(1), 4);
    assert_eq!(out.verdict, "reachable");
    p.check_witness(&out.trace).unwrap();
    p.target[0].bound = 0;
    let out = count_plan::solve_sparse_with_state_budget(&p, Duration::from_secs(1), 1);
    assert_eq!(out.verdict, "reachable");
    assert!(out.trace.is_empty());
}

#[test]
fn state_budget_can_represent_witnesses_beyond_the_fixed_cap() {
    let p = Problem {
        places: vec!["p".into()],
        initial: vec![0],
        transitions: vec![Transition {
            name: "produce".into(),
            pre: vec![],
            post: vec![(0, 1)],
        }],
        target: vec![Constraint {
            coefficients: vec![1],
            bound: 9000,
            equality: true,
        }],
    };
    assert_eq!(
        count_plan::solve_sparse(&p, Duration::from_secs(2), 10000).verdict,
        "unknown"
    );
    let out = count_plan::solve_sparse_with_state_budget(&p, Duration::from_secs(2), 10000);
    assert_eq!(out.verdict, "reachable");
    assert_eq!(out.trace.len(), 9000);
    p.check_witness(&out.trace).unwrap();
}
