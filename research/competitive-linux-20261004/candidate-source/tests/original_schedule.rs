use std::{cell::Cell, time::Duration};
use vass_reach::{
    model::{Constraint, Problem},
    original::{self, Schedule},
    pnml::{ParsedQuery, PropertyKind},
    search::Outcome,
};

fn query(kind: PropertyKind, count: usize) -> ParsedQuery {
    ParsedQuery {
        net: Problem {
            places: vec!["p".into()],
            initial: vec![0],
            transitions: vec![],
            target: vec![Constraint {
                coefficients: vec![1],
                bound: -99,
                equality: false,
            }],
        },
        property_id: "schedule".into(),
        kind,
        targets: (0..count)
            .map(|branch| {
                vec![Constraint {
                    coefficients: vec![1],
                    bound: branch as i64,
                    equality: true,
                }]
            })
            .collect(),
    }
}
fn answer(verdict: &'static str, visit: usize) -> Outcome {
    let mut outcome = Outcome::unknown("stub", &format!("visit {visit}"), visit);
    outcome.verdict = verdict;
    if verdict == "unreachable" {
        outcome.proof = Some(serde_json::json!({"kind":"stub","visit":visit}));
    }
    if verdict == "reachable" {
        outcome.trace = vec![visit];
        outcome.marking = Some(vec![1]);
    }
    outcome
}

#[test]
fn revisits_recover_an_early_branch_and_truncate_later_attempts() {
    for kind in [PropertyKind::EF, PropertyKind::AG] {
        let now = Cell::new(Duration::from_secs(2));
        let mut calls = Vec::new();
        let mut pointers = [None; 3];
        let mut visits = [0; 3];
        let result = original::solve_with_schedule(
            query(kind, 3),
            Duration::from_secs(14),
            Schedule::Geometric,
            || now.get(),
            |net, share| {
                let branch = net.target[0].bound as usize;
                let ptr = net.target.as_ptr();
                assert!(pointers[branch].is_none_or(|old| old == ptr));
                pointers[branch] = Some(ptr);
                visits[branch] += 1;
                calls.push((branch, share));
                now.set(now.get() + Duration::from_millis(100));
                answer(
                    if branch == 0 && visits[branch] == 2 {
                        "reachable"
                    } else {
                        "unknown"
                    },
                    visits[branch],
                )
            },
        )
        .unwrap();
        assert_eq!(
            calls,
            [
                (0, Duration::from_secs(2)),
                (1, Duration::from_secs(2)),
                (2, Duration::from_secs(2)),
                (0, Duration::from_secs(4))
            ]
        );
        assert_eq!(result.verdict, "reachable");
        assert_eq!(result.property_truth, Some(kind == PropertyKind::EF));
        assert_eq!(result.attempts.len(), 1);
        assert_eq!(result.attempts[0].branch, 0);
        assert_eq!(result.attempts[0].outcome.states, 2);
        assert_eq!(result.parse_seconds, 2.0);
        assert_eq!(result.solve_seconds, 0.4);
        assert!(!result.deadline_exceeded);
    }
}

#[test]
fn cached_refutations_are_never_restarted_and_all_refuted_terminates() {
    for kind in [PropertyKind::EF, PropertyKind::AG] {
        let mut visits = [0; 3];
        let mut calls = Vec::new();
        let result = original::solve_with_schedule(
            query(kind, 3),
            Duration::from_secs(12),
            Schedule::Geometric,
            || Duration::ZERO,
            |net, share| {
                let branch = net.target[0].bound as usize;
                visits[branch] += 1;
                calls.push((branch, share));
                answer(
                    if branch == 1 && visits[branch] == 1 {
                        "unknown"
                    } else {
                        "unreachable"
                    },
                    visits[branch],
                )
            },
        )
        .unwrap();
        assert_eq!(visits, [1, 2, 1]);
        assert_eq!(calls.last(), Some(&(1, Duration::from_secs(4))));
        assert_eq!(result.verdict, "unreachable");
        assert_eq!(result.property_truth, Some(kind == PropertyKind::AG));
        assert_eq!(
            result.attempts.iter().map(|a| a.branch).collect::<Vec<_>>(),
            [0, 1, 2]
        );
        assert_eq!(result.attempts[0].outcome.states, 1);
        assert_eq!(result.attempts[1].outcome.states, 2);
        assert!(result.attempts.iter().all(|a| a.outcome.proof.is_some()));
    }
}

#[test]
fn late_cheap_branch_is_visited_before_any_restart() {
    let now = Cell::new(Duration::ZERO);
    let mut calls = Vec::new();
    let result = original::solve_with_schedule(
        query(PropertyKind::EF, 4),
        Duration::from_secs(8),
        Schedule::Geometric,
        || now.get(),
        |net, share| {
            let branch = net.target[0].bound as usize;
            calls.push(branch);
            assert_eq!(share, Duration::from_secs(1));
            now.set(
                now.get()
                    + if branch == 3 {
                        Duration::from_millis(1)
                    } else {
                        share
                    },
            );
            answer(if branch == 3 { "reachable" } else { "unknown" }, 1)
        },
    )
    .unwrap();
    assert_eq!(calls, [0, 1, 2, 3]);
    assert_eq!(result.verdict, "reachable");
    assert_eq!(result.attempts.len(), 4);
}

#[test]
fn whole_limit_censors_late_definitive_revisit_and_its_evidence() {
    for verdict in ["reachable", "unreachable"] {
        let now = Cell::new(Duration::ZERO);
        let mut calls = 0;
        let result = original::solve_with_schedule(
            query(PropertyKind::AG, 2),
            Duration::from_secs(8),
            Schedule::Geometric,
            || now.get(),
            |net, share| {
                calls += 1;
                if calls == 3 {
                    assert_eq!(net.target[0].bound, 0);
                    assert_eq!(share, Duration::from_secs(4));
                    now.set(Duration::from_secs(8));
                    answer(verdict, 2)
                } else {
                    now.set(now.get() + Duration::from_secs(1));
                    answer("unknown", 1)
                }
            },
        )
        .unwrap();
        assert_eq!(calls, 3);
        assert_eq!(result.verdict, "unknown");
        assert_eq!(result.property_truth, None);
        assert!(result.deadline_exceeded);
        assert_eq!(result.attempts.len(), 2);
        let censored = &result.attempts[0].outcome;
        assert_eq!(censored.verdict, "unknown");
        assert_eq!(censored.reason, "whole-property time limit");
        assert!(
            censored.trace.is_empty() && censored.proof.is_none() && censored.marking.is_none()
        );
    }
}

#[test]
fn deadline_before_revisit_starts_no_call_and_preserves_prefix() {
    let clock_calls = Cell::new(0);
    let mut solver_calls = 0;
    let result = original::solve_with_schedule(
        query(PropertyKind::EF, 2),
        Duration::from_secs(1),
        Schedule::Geometric,
        || {
            let call = clock_calls.get();
            clock_calls.set(call + 1);
            if call >= 5 {
                Duration::from_secs(1)
            } else {
                Duration::ZERO
            }
        },
        |_, _| {
            solver_calls += 1;
            answer("unknown", 1)
        },
    )
    .unwrap();
    assert_eq!(solver_calls, 2);
    assert_eq!(result.attempts.len(), 2);
    assert_eq!(result.verdict, "unknown");
    assert!(result.deadline_exceeded);
}

#[test]
fn current_remaining_caps_revisit_share_even_when_engine_exceeds_its_slice() {
    let now = Cell::new(Duration::ZERO);
    let mut calls = Vec::new();
    let result = original::solve_with_schedule(
        query(PropertyKind::EF, 2),
        Duration::from_secs(8),
        Schedule::Geometric,
        || now.get(),
        |net, share| {
            calls.push((net.target[0].bound, share));
            match calls.len() {
                1 => now.set(Duration::from_secs(5)),
                2 => now.set(Duration::from_secs(7)),
                _ => now.set(Duration::from_millis(7500)),
            }
            answer(
                if calls.len() == 3 {
                    "reachable"
                } else {
                    "unknown"
                },
                calls.len(),
            )
        },
    )
    .unwrap();
    assert_eq!(
        calls,
        [
            (0, Duration::from_secs(2)),
            (1, Duration::from_secs(2)),
            (0, Duration::from_secs(1))
        ]
    );
    assert_eq!(result.verdict, "reachable");
}

#[test]
fn stationary_clock_terminates_after_one_full_capped_pass() {
    let mut calls = Vec::new();
    let result = original::solve_with_schedule(
        query(PropertyKind::EF, 2),
        Duration::from_nanos(8),
        Schedule::Geometric,
        || Duration::ZERO,
        |net, share| {
            calls.push((net.target[0].bound, share.as_nanos()));
            answer("unknown", calls.len())
        },
    )
    .unwrap();
    assert_eq!(calls, [(0, 2), (1, 2), (0, 4), (1, 4), (0, 8), (1, 8)]);
    assert_eq!(result.verdict, "unknown");
    assert!(!result.deadline_exceeded);
    assert_eq!(
        result
            .attempts
            .iter()
            .map(|a| a.outcome.states)
            .collect::<Vec<_>>(),
        [5, 6]
    );
    let mut calls = 0;
    let result = original::solve_with_schedule(
        query(PropertyKind::EF, 3),
        Duration::from_nanos(1),
        Schedule::Geometric,
        || Duration::ZERO,
        |_, share| {
            assert_eq!(share, Duration::from_nanos(1));
            calls += 1;
            answer("unknown", calls)
        },
    )
    .unwrap();
    assert_eq!(calls, 3);
    assert_eq!(result.attempts.len(), 3);
    assert!(!result.deadline_exceeded);
}

#[test]
fn one_branch_gets_all_remaining_time_once() {
    let now = Cell::new(Duration::from_secs(2));
    let mut calls = 0;
    let result = original::solve_with_schedule(
        query(PropertyKind::EF, 1),
        Duration::from_secs(10),
        Schedule::Geometric,
        || now.get(),
        |_, share| {
            calls += 1;
            assert_eq!(share, Duration::from_secs(8));
            now.set(Duration::from_secs(9));
            answer("unknown", 1)
        },
    )
    .unwrap();
    assert_eq!(calls, 1);
    assert_eq!(result.verdict, "unknown");
    assert!(!result.deadline_exceeded);
}

#[test]
fn empty_disjunction_and_parsing_deadline_keep_existing_semantics() {
    for kind in [PropertyKind::EF, PropertyKind::AG] {
        let result = original::solve_with_schedule(
            query(kind, 0),
            Duration::from_secs(1),
            Schedule::Geometric,
            || Duration::ZERO,
            |_, _| panic!("empty disjunction"),
        )
        .unwrap();
        assert_eq!(result.verdict, "unreachable");
        assert_eq!(result.property_truth, Some(kind == PropertyKind::AG));
        for count in [0, 1, 3] {
            let result = original::solve_with_schedule(
                query(kind, count),
                Duration::from_secs(1),
                Schedule::Geometric,
                || Duration::from_secs(1),
                |_, _| panic!("parse deadline exhausted"),
            )
            .unwrap();
            assert_eq!(result.verdict, "unknown");
            assert!(result.deadline_exceeded);
            assert!(result.attempts.is_empty());
        }
    }
}

#[test]
fn default_and_explicit_single_pass_have_identical_clock_calls_and_outputs() {
    fn run(explicit: bool) -> (serde_json::Value, Vec<(i64, Duration)>, usize) {
        let now = Cell::new(Duration::from_secs(2));
        let clock_calls = Cell::new(0);
        let mut calls = Vec::new();
        let clock = || {
            clock_calls.set(clock_calls.get() + 1);
            now.get()
        };
        let solver = |net: &Problem, share| {
            calls.push((net.target[0].bound, share));
            now.set(now.get() + Duration::from_secs(1));
            answer(
                if net.target[0].bound == 1 {
                    "unreachable"
                } else {
                    "unknown"
                },
                1,
            )
        };
        let outcome = if explicit {
            original::solve_with_schedule(
                query(PropertyKind::AG, 3),
                Duration::from_secs(10),
                Schedule::SinglePass,
                clock,
                solver,
            )
        } else {
            original::solve(
                query(PropertyKind::AG, 3),
                Duration::from_secs(10),
                clock,
                solver,
            )
        }
        .unwrap();
        (
            serde_json::to_value(outcome).unwrap(),
            calls,
            clock_calls.get(),
        )
    }
    let (value, calls, clocks) = run(false);
    assert_eq!((value.clone(), calls.clone(), clocks), run(true));
    assert_eq!(
        calls,
        [
            (0, Duration::from_secs(8) / 3),
            (1, Duration::from_secs(7) / 2),
            (2, Duration::from_secs(6))
        ]
    );
    assert_eq!(clocks, 8);
    assert_eq!(value["verdict"], "unknown");
}

#[test]
fn malformed_revisit_verdict_is_rejected() {
    let mut calls = 0;
    assert!(
        original::solve_with_schedule(
            query(PropertyKind::EF, 2),
            Duration::from_secs(8),
            Schedule::Geometric,
            || Duration::ZERO,
            |_, _| {
                calls += 1;
                answer(if calls == 3 { "bogus" } else { "unknown" }, calls)
            }
        )
        .is_err()
    );
    assert_eq!(calls, 3);
}
