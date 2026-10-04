use std::{cell::Cell, time::Duration};
use vass_reach::{
    model::{Constraint, Problem},
    original,
    pnml::{ParsedQuery, PropertyKind},
    search::Outcome,
};

fn query(kind: PropertyKind, count: usize) -> ParsedQuery {
    ParsedQuery {
        net: Problem {
            places: vec!["p".into()],
            initial: vec![0],
            transitions: vec![],
            target: vec![],
        },
        property_id: "selected".into(),
        kind,
        targets: (0..count)
            .map(|i| {
                vec![Constraint {
                    coefficients: vec![1],
                    bound: i as i64,
                    equality: false,
                }]
            })
            .collect(),
    }
}
fn answer(verdict: &'static str) -> Outcome {
    let mut answer = Outcome::unknown("stub", "stub", 1);
    answer.verdict = verdict;
    if verdict == "unreachable" {
        answer.proof = Some(serde_json::json!({"kind":"test-certificate"}));
    }
    answer
}

#[test]
fn original_deadline_includes_parse_and_unused_time_is_shared() {
    let now = Cell::new(Duration::from_secs(2));
    let mut budgets = Vec::new();
    let mut targets = Vec::new();
    let mut nets = Vec::new();
    let result = original::solve(
        query(PropertyKind::EF, 3),
        Duration::from_secs(10),
        || now.get(),
        |net, budget| {
            budgets.push(budget);
            targets.push(net.target[0].bound);
            nets.push(net.initial.as_ptr());
            now.set(now.get() + Duration::from_secs(1));
            answer("unreachable")
        },
    )
    .unwrap();
    assert_eq!(targets, [0, 1, 2]);
    assert!(nets.iter().all(|p| *p == nets[0]));
    assert_eq!(
        budgets,
        [
            Duration::from_secs(8) / 3,
            Duration::from_secs(7) / 2,
            Duration::from_secs(6)
        ]
    );
    assert_eq!(result.verdict, "unreachable");
    assert_eq!(result.property_truth, Some(false));
    assert_eq!(result.parse_seconds, 2.0);
    assert_eq!(result.solve_seconds, 3.0);
    assert!(!result.deadline_exceeded);
    assert!(result.attempts.iter().all(|a| a.outcome.proof.is_some()));
}

#[test]
fn unknown_then_positive_stops_and_inverts_only_ag_property_truth() {
    let now = Cell::new(Duration::ZERO);
    let mut calls = 0;
    let result = original::solve(
        query(PropertyKind::AG, 3),
        Duration::from_secs(10),
        || now.get(),
        |_, _| {
            now.set(now.get() + Duration::from_secs(1));
            calls += 1;
            answer(if calls == 1 { "unknown" } else { "reachable" })
        },
    )
    .unwrap();
    assert_eq!(calls, 2);
    assert_eq!(result.verdict, "reachable");
    assert_eq!(result.property_truth, Some(false));
    assert_eq!(
        result.attempts.iter().map(|a| a.branch).collect::<Vec<_>>(),
        [0, 1]
    );
}

#[test]
fn unresolved_branches_prevent_negative_aggregation() {
    let mut calls = 0;
    let result = original::solve(
        query(PropertyKind::EF, 2),
        Duration::from_secs(1),
        || Duration::ZERO,
        |_, _| {
            calls += 1;
            answer(if calls == 1 { "unreachable" } else { "unknown" })
        },
    )
    .unwrap();
    assert_eq!(result.verdict, "unknown");
    assert_eq!(result.property_truth, None);
}

#[test]
fn parse_exhaustion_starts_no_solver_even_for_empty_disjunction() {
    for branches in [0, 3] {
        let result = original::solve(
            query(PropertyKind::EF, branches),
            Duration::from_secs(1),
            || Duration::from_secs(1),
            |_, _| panic!("solver must not start after parsing consumed the deadline"),
        )
        .unwrap();
        assert_eq!(result.verdict, "unknown");
        assert!(result.deadline_exceeded);
        assert!(result.attempts.is_empty());
    }
}

#[test]
fn late_definitive_results_and_their_certificates_are_discarded() {
    for verdict in ["reachable", "unreachable"] {
        let now = Cell::new(Duration::ZERO);
        let result = original::solve(
            query(PropertyKind::EF, 2),
            Duration::from_secs(1),
            || now.get(),
            |_, _| {
                now.set(Duration::from_secs(2));
                answer(verdict)
            },
        )
        .unwrap();
        assert_eq!(result.verdict, "unknown");
        assert_eq!(result.attempts.len(), 1);
        assert_eq!(result.attempts[0].outcome.verdict, "unknown");
        assert!(result.attempts[0].outcome.proof.is_none());
        assert!(result.deadline_exceeded);
    }
}

#[test]
fn shares_are_advisory_but_the_property_limit_is_shared() {
    let now = Cell::new(Duration::ZERO);
    let mut budgets = Vec::new();
    let result = original::solve(
        query(PropertyKind::AG, 2),
        Duration::from_secs(10),
        || now.get(),
        |_, budget| {
            budgets.push(budget);
            now.set(
                now.get()
                    + if budgets.len() == 1 {
                        Duration::from_secs(7)
                    } else {
                        Duration::from_secs(1)
                    },
            );
            answer("unreachable")
        },
    )
    .unwrap();
    assert_eq!(budgets, [Duration::from_secs(5), Duration::from_secs(3)]);
    assert_eq!(result.verdict, "unreachable");
    assert_eq!(result.property_truth, Some(true));
}

#[test]
fn empty_disjunction_and_true_branch_are_distinct() {
    let false_query = original::solve(
        query(PropertyKind::AG, 0),
        Duration::from_secs(1),
        || Duration::ZERO,
        |_, _| panic!("false target has no branches"),
    )
    .unwrap();
    assert_eq!(false_query.verdict, "unreachable");
    assert_eq!(false_query.property_truth, Some(true));
    let mut true_query = query(PropertyKind::EF, 1);
    true_query.targets[0].clear();
    let result = original::solve(
        true_query,
        Duration::from_secs(1),
        || Duration::ZERO,
        |net, _| {
            assert!(net.target.is_empty());
            answer("reachable")
        },
    )
    .unwrap();
    assert_eq!(result.verdict, "reachable");
    assert_eq!(result.attempts.len(), 1);
}

#[test]
fn malformed_backend_verdict_is_an_error() {
    assert!(
        original::solve(
            query(PropertyKind::EF, 1),
            Duration::from_secs(1),
            || Duration::ZERO,
            |_, _| { answer("bogus") }
        )
        .is_err()
    );
}
