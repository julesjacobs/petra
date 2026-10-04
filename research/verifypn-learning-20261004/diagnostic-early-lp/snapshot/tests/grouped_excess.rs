use std::time::{Duration, Instant};
use vass_reach::{
    grouped_excess::{self, Certificate},
    model::{Constraint, Problem, Transition},
    search,
};

fn deadline() -> Instant {
    Instant::now() + Duration::from_secs(2)
}

#[test]
fn checked_refutations_agree_with_complete_weighted_state_spaces() {
    let mut seed = 20261004_u64;
    let mut next = || {
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        seed >> 32
    };
    let mut refutations = 0;
    for case in 0..500 {
        let mut transitions = vec![];
        for t in 0..4 {
            let pre: Vec<_> = (0..3)
                .filter_map(|q| {
                    let weight = next() % 3;
                    (weight > 0).then_some((q, weight))
                })
                .collect();
            let mut left: u64 = pre.iter().map(|&(_, w)| w).sum();
            let post = (0..3)
                .filter_map(|q| {
                    let weight = next() % (left.min(2) + 1);
                    left -= weight;
                    (weight > 0).then_some((q, weight))
                })
                .collect();
            transitions.push(Transition {
                name: format!("t{t}"),
                pre,
                post,
            });
        }
        let problem = Problem {
            places: (0..3).map(|q| format!("p{q}")).collect(),
            initial: (0..3).map(|_| next() % 3).collect(),
            transitions,
            target: vec![Constraint {
                coefficients: (0..3).map(|_| (next() % 5) as i64 - 2).collect(),
                bound: (next() % 15) as i64 - 3,
                equality: next().is_multiple_of(2),
            }],
        };
        problem.validate().unwrap();
        let candidate = grouped_excess::solve(&problem, Duration::from_secs(2), 10_000);
        let exact = search::solve(&problem, false, Duration::from_secs(2), 1000);
        assert_ne!(exact.verdict, "unknown", "case {case}");
        if candidate.verdict == "unreachable" {
            refutations += 1;
            assert_eq!(exact.verdict, "unreachable", "case {case}");
            grouped_excess::verify(&problem, candidate.proof.as_ref().unwrap(), deadline())
                .unwrap();
        }
    }
    assert!(refutations >= 30, "checked only {refutations} refutations");
}

#[test]
fn weighted_read_guard_is_required_for_nonincrease() {
    let mut problem = Problem {
        places: vec!["fuel".into(), "destination".into()],
        initial: vec![2, 1],
        transitions: vec![Transition {
            name: "move".into(),
            pre: vec![(0, 2), (1, 1)],
            post: vec![(1, 2)],
        }],
        target: vec![Constraint {
            coefficients: vec![0, 1],
            bound: 3,
            equality: false,
        }],
    };
    let outcome = grouped_excess::solve(&problem, Duration::from_secs(2), 1000);
    assert_eq!(outcome.verdict, "unreachable");
    let proof = outcome.proof.unwrap();
    problem.transitions[0].pre[0].1 = 1;
    assert!(grouped_excess::verify(&problem, &proof, deadline()).is_err());
    assert_eq!(
        search::solve(&problem, false, Duration::from_secs(2), 1000).verdict,
        "reachable"
    );
}

#[test]
fn changed_initial_marking_and_target_cannot_reuse_a_certificate() {
    let mut problem = Problem {
        places: vec!["p".into()],
        initial: vec![1],
        transitions: vec![],
        target: vec![Constraint {
            coefficients: vec![1],
            bound: 2,
            equality: false,
        }],
    };
    let outcome = grouped_excess::solve(&problem, Duration::from_secs(2), 1000);
    assert_eq!(outcome.verdict, "unreachable");
    let proof = outcome.proof.unwrap();
    problem.initial[0] = 2;
    assert!(grouped_excess::verify(&problem, &proof, deadline()).is_err());
    problem.initial[0] = 1;
    problem.target[0].bound = 1;
    assert!(grouped_excess::verify(&problem, &proof, deadline()).is_err());
}

#[test]
fn group_sums_and_target_arithmetic_use_arbitrary_precision() {
    let problem = Problem {
        places: vec!["a".into(), "b".into()],
        initial: vec![u64::MAX, u64::MAX],
        transitions: vec![Transition {
            name: "consume".into(),
            pre: vec![(0, u64::MAX), (1, u64::MAX)],
            post: vec![],
        }],
        target: vec![Constraint {
            coefficients: vec![i64::MIN, i64::MIN],
            bound: 1,
            equality: false,
        }],
    };
    let certificate = Certificate {
        kind: "grouped-excess-v1".into(),
        groups: vec![vec![0, 1]],
        thresholds: vec![u64::MAX],
        target_row: 0,
        sign: 1,
    };
    grouped_excess::verify(
        &problem,
        &serde_json::to_value(certificate).unwrap(),
        deadline(),
    )
    .unwrap();
}
