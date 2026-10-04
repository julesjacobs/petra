use std::time::Duration;
use vass_reach::{
    model::{Constraint, Problem, Transition},
    relaxed,
};

fn problem(
    initial: Vec<u64>,
    transitions: Vec<Transition>,
    coefficients: Vec<i64>,
    bound: i64,
) -> Problem {
    Problem {
        places: (0..initial.len()).map(|i| format!("p{i}")).collect(),
        initial,
        transitions,
        target: vec![Constraint {
            coefficients,
            bound,
            equality: true,
        }],
    }
}

fn transition(pre: &[(usize, u64)], post: &[(usize, u64)]) -> Transition {
    Transition {
        name: "step".into(),
        pre: pre.to_vec(),
        post: post.to_vec(),
    }
}

fn checked(p: &Problem, cap: usize) -> vass_reach::search::Outcome {
    let answer = relaxed::solve_batched(p, Duration::from_secs(3), cap);
    assert_eq!(answer.verdict, "reachable", "{}", answer.reason);
    assert_eq!(
        answer.marking.as_ref().unwrap(),
        &p.check_witness(&answer.trace).unwrap()
    );
    answer
}

#[test]
fn long_consuming_run_uses_few_states_and_expands_the_witness() {
    let p = problem(
        vec![100_000, 0, 1],
        vec![transition(&[(0, 1), (2, 1)], &[(1, 1), (2, 1)])],
        vec![0, 1, 0],
        100_000,
    );
    let answer = checked(&p, 4);
    assert!(answer.states <= 4);
    assert_eq!(answer.trace, vec![0; 100_000]);
    assert_eq!(
        relaxed::solve_focused(&p, Duration::from_secs(1), 4).verdict,
        "unknown"
    );
}

#[test]
fn equality_milestone_is_retained_before_resource_exhaustion() {
    let p = problem(
        vec![100, 0],
        vec![transition(&[(0, 1)], &[(1, 2)])],
        vec![0, 1],
        70,
    );
    assert_eq!(checked(&p, 8).trace.len(), 35);
}

#[test]
fn decreasing_guard_checks_every_prefix_including_selfloops() {
    let p = problem(vec![10], vec![transition(&[(0, 5)], &[(0, 3)])], vec![1], 4);
    assert_eq!(checked(&p, 4).trace, vec![0, 0, 0]);
    let blocked = problem(
        vec![4, 0],
        vec![transition(&[(0, 5)], &[(0, 5), (1, 1)])],
        vec![0, 1],
        1,
    );
    assert_eq!(
        relaxed::solve_batched(&blocked, Duration::from_secs(1), 100).verdict,
        "unknown"
    );
}

#[test]
fn single_steps_allow_switching_before_the_maximum_repeat() {
    let p = problem(
        vec![100, 0, 0],
        vec![
            transition(&[(0, 1)], &[(1, 1)]),
            transition(&[(0, 90), (1, 3)], &[(2, 1)]),
        ],
        vec![0, 0, 1],
        1,
    );
    let answer = checked(&p, 100);
    assert!(answer.trace.contains(&1));
}

#[test]
fn large_counters_and_mixed_sign_equality_use_checked_arithmetic() {
    let p = problem(
        vec![u64::MAX - 2, u64::MAX],
        vec![transition(&[], &[(0, 1)])],
        vec![1, -1],
        0,
    );
    assert_eq!(checked(&p, 4).trace, vec![0, 0]);
}

#[test]
fn deadlines_and_exhaustion_never_produce_negative_answers() {
    let p = problem(vec![1], vec![transition(&[(0, 1)], &[(0, 1)])], vec![1], 2);
    for timeout in [Duration::ZERO, Duration::from_secs(1)] {
        assert_eq!(relaxed::solve_batched(&p, timeout, 50).verdict, "unknown");
    }
}
