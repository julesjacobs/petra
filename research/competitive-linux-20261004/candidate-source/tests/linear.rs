use std::time::Duration;
use vass_reach::{
    linear::{self, Row, System},
    model::{Constraint, Problem, Transition},
    search,
};

#[test]
fn exact_checker_rejects_approximate_and_signed_proofs() {
    let system = System {
        variables: 1,
        rows: vec![
            Row {
                coefficients: vec![(0, 3.into())],
                bound: 1.into(),
            },
            Row {
                coefficients: vec![(0, (-1).into())],
                bound: 0.into(),
            },
        ],
    };
    assert!(system.check(&[(0, "1/3".into()), (1, "1".into())]).is_ok());
    assert!(
        system
            .check(&[(0, "333334/1000000".into()), (1, "1".into())])
            .is_err()
    );
    assert!(system.check(&[(0, "-1".into())]).is_err());
    assert!(system.check(&[(0, "1".into()), (0, "1".into())]).is_err());
    assert!(system.check(&[(99, "1".into())]).is_err());
}

#[test]
fn dual_discovery_is_checked_exactly() {
    let system = System {
        variables: 2,
        rows: vec![
            Row {
                coefficients: vec![(0, 3.into()), (1, 7.into())],
                bound: 1.into(),
            },
            Row {
                coefficients: vec![(0, (-1).into())],
                bound: 0.into(),
            },
            Row {
                coefficients: vec![(1, (-1).into())],
                bound: 0.into(),
            },
        ],
    };
    let proof = system
        .refute(std::time::Instant::now() + Duration::from_secs(1))
        .unwrap();
    system.check(&proof).unwrap();
}

#[test]
fn sparse_net_equation_matches_bounded_exploration() {
    for seed in 0..40usize {
        let size = 2 + seed % 5;
        let mut p = Problem {
            places: (0..size).map(|i| format!("p{i}")).collect(),
            initial: (0..size).map(|i| u64::from(i == 0)).collect(),
            transitions: (0..size - 1)
                .filter(|i| (i + seed) % 3 != 0)
                .map(|i| Transition {
                    name: format!("t{i}"),
                    pre: vec![(i, 1)],
                    post: vec![(i + 1, 1)],
                })
                .collect(),
            target: vec![Constraint {
                coefficients: (0..size).map(|i| i64::from(i == size - 1)).collect(),
                bound: 1,
                equality: seed % 2 == 0,
            }],
        };
        p.validate().unwrap();
        let oracle = search::solve(&p, false, Duration::from_secs(1), 100);
        let out = linear::solve(&p, Duration::from_secs(1));
        if oracle.verdict == "unreachable" {
            assert_eq!(out.verdict, "unreachable", "seed {seed}");
            linear::verify_certificate(&p, out.proof.as_ref().unwrap()).unwrap();
        } else {
            assert_eq!(out.verdict, "unknown");
        }
        p.initial.fill(0);
        p.initial[size - 1] = 1;
        assert_ne!(
            linear::solve(&p, Duration::from_secs(1)).verdict,
            "unreachable"
        );
    }
}

#[test]
fn arbitrary_precision_target_and_no_transitions() {
    let p = Problem {
        places: vec!["p".into()],
        initial: vec![u64::MAX],
        transitions: vec![],
        target: vec![Constraint {
            coefficients: vec![-1],
            bound: 0,
            equality: false,
        }],
    };
    let out = linear::solve(&p, Duration::from_secs(1));
    assert_eq!(out.verdict, "unreachable");
    linear::verify_certificate(&p, out.proof.as_ref().unwrap()).unwrap();
}

#[test]
fn weighted_conservation_needs_a_relational_certificate() {
    let p = Problem {
        places: vec!["large".into(), "small".into()],
        initial: vec![1, 0],
        transitions: vec![
            Transition {
                name: "split".into(),
                pre: vec![(0, 1)],
                post: vec![(1, 7)],
            },
            Transition {
                name: "join".into(),
                pre: vec![(1, 7)],
                post: vec![(0, 1)],
            },
        ],
        target: vec![Constraint {
            coefficients: vec![1, 1],
            bound: 8,
            equality: false,
        }],
    };
    let out = linear::solve(&p, Duration::from_secs(1));
    assert_eq!(out.verdict, "unreachable");
    let proof = out.proof.unwrap();
    linear::verify_certificate(&p, &proof).unwrap();
    let mut broken = p;
    broken.transitions[1].post[0].1 = 2;
    assert!(linear::verify_certificate(&broken, &proof).is_err());
    assert_ne!(
        linear::solve(&broken, Duration::from_secs(1)).verdict,
        "unreachable"
    );
}

#[test]
fn integer_model_does_not_accept_fractional_feasibility() {
    let system = System {
        variables: 1,
        rows: vec![
            Row {
                coefficients: vec![(0, 2.into())],
                bound: 1.into(),
            },
            Row {
                coefficients: vec![(0, (-2).into())],
                bound: (-1).into(),
            },
        ],
    };
    assert!(
        system
            .integer_model(std::time::Instant::now() + Duration::from_secs(1), 100)
            .is_none()
    );
}

#[test]
fn sparse_counts_refine_missing_enabling_support() {
    let mut p = Problem {
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
    };
    assert_eq!(
        vass_reach::count_plan::solve_sparse(&p, Duration::from_secs(1), 100).verdict,
        "unknown"
    );
    p.transitions.push(Transition {
        name: "enable".into(),
        pre: vec![],
        post: vec![(0, 1)],
    });
    let out = vass_reach::count_plan::solve_sparse(&p, Duration::from_secs(1), 100);
    assert_eq!(out.verdict, "reachable");
    assert_eq!(out.trace, [1, 0]);
    p.check_witness(&out.trace).unwrap();
}

fn rational_equality(coefficient: i64, bound: i64) -> System {
    System {
        variables: 1,
        rows: vec![
            Row {
                coefficients: vec![(0, coefficient.into())],
                bound: bound.into(),
            },
            Row {
                coefficients: vec![(0, (-coefficient).into())],
                bound: (-bound).into(),
            },
        ],
    }
}

#[test]
fn rational_model_reconstructs_fractional_equality() {
    let system = rational_equality(3, 1);
    let candidate = system
        .rational_model(std::time::Instant::now() + Duration::from_secs(1))
        .unwrap();
    assert_eq!(candidate, vec!["1/3".parse().unwrap()]);
}

#[test]
fn rational_model_retains_integer_part() {
    let system = rational_equality(3, 10);
    let candidate = system
        .rational_model(std::time::Instant::now() + Duration::from_secs(1))
        .unwrap();
    assert_eq!(candidate, vec!["10/3".parse().unwrap()]);
}

#[test]
fn rational_model_rejects_contradiction() {
    let mut system = rational_equality(3, 1);
    system.rows.push(Row {
        coefficients: vec![(0, 1.into())],
        bound: 1.into(),
    });
    assert!(
        system
            .rational_model(std::time::Instant::now() + Duration::from_secs(1))
            .is_none()
    );
}

#[test]
fn rational_model_respects_expired_deadline() {
    assert!(
        rational_equality(3, 1)
            .rational_model(std::time::Instant::now())
            .is_none()
    );
}

#[test]
fn rational_model_rejects_numerically_indistinguishable_bounds() {
    let upper = num_bigint::BigInt::from(10_000_000_000_000_000u64);
    let system = System {
        variables: 1,
        rows: vec![
            Row {
                coefficients: vec![(0, 1.into())],
                bound: &upper + 1,
            },
            Row {
                coefficients: vec![(0, (-1).into())],
                bound: -upper,
            },
        ],
    };
    assert!(
        system
            .rational_model(std::time::Instant::now() + Duration::from_secs(1))
            .is_none()
    );
}

#[test]
fn rational_model_satisfies_original_sparse_rows_exactly() {
    let system = System {
        variables: 3,
        rows: vec![
            Row {
                coefficients: vec![(0, 3.into()), (1, (-2).into())],
                bound: 7.into(),
            },
            Row {
                coefficients: vec![(1, 4.into()), (1, 3.into())],
                bound: 2.into(),
            },
            Row {
                coefficients: vec![(0, (-1).into()), (2, 1.into())],
                bound: 1.into(),
            },
        ],
    };
    let candidate = system
        .rational_model(std::time::Instant::now() + Duration::from_secs(1))
        .unwrap();
    assert_eq!(candidate.len(), system.variables);
    assert!(
        candidate
            .iter()
            .all(|value| value >= &num_rational::BigRational::from_integer(0.into()))
    );
    for row in system.rows {
        let lhs: num_rational::BigRational = row
            .coefficients
            .into_iter()
            .map(|(index, coefficient)| &candidate[index] * coefficient)
            .sum();
        assert!(lhs >= num_rational::BigRational::from_integer(row.bound));
    }
}
