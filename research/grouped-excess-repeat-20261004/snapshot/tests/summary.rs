use num_bigint::{BigInt, BigUint};
use std::time::Duration;
use vass_reach::{
    backward,
    model::{Constraint, Problem, Transition},
    summary::WordSummary,
};

fn transition(pre: u64, post: u64) -> Transition {
    Transition {
        name: format!("{pre}_{post}"),
        pre: if pre == 0 { vec![] } else { vec![(0, pre)] },
        post: if post == 0 { vec![] } else { vec![(0, post)] },
    }
}
#[test]
fn summary_matches_exhaustive_word_execution() {
    for a in 0..4 {
        for b in 0..4 {
            for c in 0..4 {
                for d in 0..4 {
                    let first = transition(a, b);
                    let second = transition(c, d);
                    let s = WordSummary::transition(1, &first)
                        .then(&WordSummary::transition(1, &second));
                    for initial in 0..16 {
                        let expected = if initial >= a && initial - a + b >= c {
                            Some(vec![BigInt::from(initial - a + b - c + d)])
                        } else {
                            None
                        };
                        assert_eq!(s.apply(&[BigInt::from(initial)]), expected);
                    }
                }
            }
        }
    }
}
#[test]
fn exact_repetition_including_read_arcs_and_zero() {
    for pre in 0..5 {
        for post in 0..5 {
            let s = WordSummary::transition(1, &transition(pre, post));
            let mut unfolded = WordSummary::identity(1);
            for count in 0u64..20 {
                assert_eq!(s.repeat(&BigUint::from(count)), unfolded);
                unfolded = unfolded.then(&s);
            }
        }
    }
    let big = BigUint::from(1u64) << 200;
    let repeated = WordSummary::transition(1, &transition(2, 1)).repeat(&big);
    assert_eq!(repeated.hurdle[0], BigInt::from(big) + 1);
}
#[test]
fn backward_respects_signed_equality_targets_and_read_arcs() {
    let p = Problem {
        places: vec!["x".into(), "y".into()],
        initial: vec![7, 1],
        transitions: vec![Transition {
            name: "transfer".into(),
            pre: vec![(0, 2), (1, 1)],
            post: vec![(0, 1), (1, 2)],
        }],
        target: vec![Constraint {
            coefficients: vec![-1, 1],
            bound: 0,
            equality: true,
        }],
    };
    let result = backward::solve(&p, Duration::from_secs(1), 100);
    assert_eq!(result.verdict, "reachable");
    assert_eq!(p.check_witness(&result.trace).unwrap(), vec![4, 4]);
    let mut blocked = p.clone();
    blocked.initial[1] = 0;
    assert_eq!(
        backward::solve(&blocked, Duration::from_secs(1), 100).verdict,
        "unknown"
    );
    assert_eq!(backward::solve(&p, Duration::ZERO, 100).verdict, "unknown");
}
#[test]
fn backward_differential_bounded_transfer_nets() {
    for total in 0..8 {
        for target in 0..=total {
            let p = Problem {
                places: vec!["x".into(), "y".into()],
                initial: vec![total, 0],
                transitions: vec![Transition {
                    name: "transfer".into(),
                    pre: vec![(0, 1)],
                    post: vec![(1, 1)],
                }],
                target: vec![Constraint {
                    coefficients: vec![1, -1],
                    bound: (total as i64) - 2 * (target as i64),
                    equality: true,
                }],
            };
            let out = backward::solve(&p, Duration::from_secs(1), 100);
            assert_eq!(out.verdict, "reachable");
            assert!(p.check_witness(&out.trace).is_ok());
        }
    }
}
