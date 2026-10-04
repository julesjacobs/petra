use std::time::Duration;
use vass_reach::{
    dag_solve,
    model::{Constraint, Problem, Transition},
};

fn weighted_read() -> Problem {
    Problem {
        places: ["entry", "middle", "exit", "resource", "saved"]
            .into_iter()
            .map(String::from)
            .collect(),
        initial: vec![1, 0, 0, 2, 0],
        transitions: vec![
            Transition {
                name: "consume".into(),
                pre: vec![(0, 1), (3, 2)],
                post: vec![(1, 1), (4, 7)],
            },
            Transition {
                name: "test".into(),
                pre: vec![(1, 1), (4, 7)],
                post: vec![(2, 1), (4, 7)],
            },
        ],
        target: vec![
            Constraint {
                coefficients: vec![0, 0, 1, 0, 0],
                bound: 1,
                equality: false,
            },
            Constraint {
                coefficients: vec![0, 0, 0, -3, 1],
                bound: 7,
                equality: true,
            },
        ],
    }
}

#[test]
fn weighted_read_witness_and_exact_negative_proof() {
    let mut p = weighted_read();
    let positive = dag_solve::solve(&p, Duration::from_secs(2), 100_000);
    assert_eq!(positive.verdict, "reachable", "{}", positive.reason);
    assert_eq!(positive.trace, vec![0, 1]);
    assert_eq!(
        p.check_witness(&positive.trace).unwrap(),
        positive.marking.unwrap()
    );
    p.target[1].bound = 8;
    let negative = dag_solve::solve(&p, Duration::from_secs(2), 100_000);
    assert_eq!(negative.verdict, "unreachable", "{}", negative.reason);
    let proof = negative.proof.unwrap();
    dag_solve::verify_certificate(&p, &proof).unwrap();
    p.target[1].bound = 7;
    assert!(dag_solve::verify_certificate(&p, &proof).is_err());
}

#[test]
fn cyclic_control_and_budget_limits_are_inconclusive() {
    let mut p = weighted_read();
    assert_eq!(dag_solve::solve(&p, Duration::ZERO, 100).verdict, "unknown");
    assert_eq!(
        dag_solve::solve(&p, Duration::from_secs(1), 0).verdict,
        "unknown"
    );
    p.transitions.push(Transition {
        name: "repeat".into(),
        pre: vec![(2, 1)],
        post: vec![(0, 1)],
    });
    assert_eq!(
        dag_solve::solve(&p, Duration::from_secs(1), 100_000).verdict,
        "unknown"
    );
}

#[test]
fn ordinary_replay_controls_large_counter_positives() {
    let mut p = weighted_read();
    p.initial[4] = u64::MAX;
    p.target.truncate(1);
    let answer = dag_solve::solve(&p, Duration::from_secs(2), 100_000);
    assert_eq!(answer.verdict, "unknown", "{}", answer.reason);
}
