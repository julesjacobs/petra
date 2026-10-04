use serde_json::{Value, json};
use vass_reach::{
    linear::{self, Certificate},
    model::{Constraint, Problem, Transition},
};

fn proof(multipliers: Vec<(usize, &str)>) -> Value {
    json!({"kind": "sparse-farkas-v1", "multipliers": multipliers})
}

fn reference_accepts(problem: &Problem, proof: &Value) -> bool {
    if problem.validate().is_err() {
        return false;
    }
    let Ok(certificate) = serde_json::from_value::<Certificate>(proof.clone()) else {
        return false;
    };
    certificate.kind == "sparse-farkas-v1"
        && linear::state_equation(problem)
            .check(&certificate.multipliers)
            .is_ok()
}

fn agrees(problem: &Problem, proof: &Value) -> bool {
    let direct = linear::verify_certificate(problem, proof).is_ok();
    assert_eq!(
        direct,
        reference_accepts(problem, proof),
        "{problem:?} {proof}"
    );
    direct
}

fn conversion() -> Problem {
    Problem {
        places: vec!["a".into(), "b".into()],
        initial: vec![1, 0],
        transitions: vec![Transition {
            name: "convert".into(),
            pre: vec![(0, 1)],
            post: vec![(1, 3)],
        }],
        target: vec![Constraint {
            coefficients: vec![0, 1],
            bound: 4,
            equality: false,
        }],
    }
}

#[test]
fn direct_checker_matches_matrix_checker_on_signed_weighted_systems() {
    let mut accepted = 0;
    let mut rejected = 0;
    for variant in 0..4 {
        for left in -2..=2 {
            for right in -2..=2 {
                for bound in [-2, 0, 3] {
                    for equality in [false, true] {
                        let mut problem = conversion();
                        problem.initial = vec![variant % 2, variant / 2];
                        problem.transitions[0].post[0].1 = variant + 1;
                        if variant % 2 == 1 {
                            problem.transitions[0].pre.push((1, 2));
                            problem.transitions[0].post[0].1 += 2;
                        }
                        if variant > 1 {
                            problem.transitions.push(Transition {
                                name: "return".into(),
                                pre: vec![(1, variant)],
                                post: vec![(0, 1)],
                            });
                        }
                        problem.target = vec![
                            Constraint {
                                coefficients: vec![left, right],
                                bound,
                                equality,
                            },
                            Constraint {
                                coefficients: vec![-right, left],
                                bound: 1 - bound,
                                equality: !equality,
                            },
                        ];
                        let rows = linear::state_equation(&problem).rows.len();
                        let mut candidates = vec![proof(vec![])];
                        for first in 0..rows {
                            for weight in ["1/3", "1", "5/2"] {
                                candidates.push(proof(vec![(first, weight)]));
                                for second in first + 1..rows {
                                    candidates.push(proof(vec![(first, weight), (second, "1")]));
                                }
                            }
                        }
                        candidates.push(proof((0..rows).map(|row| (row, "1/7")).collect()));
                        for candidate in candidates {
                            if agrees(&problem, &candidate) {
                                accepted += 1;
                            } else {
                                rejected += 1;
                            }
                        }
                    }
                }
            }
        }
    }
    assert!(accepted > 100);
    assert!(rejected > 100);
}

#[test]
fn rational_coefficients_are_checked_without_rounding() {
    let problem = conversion();
    assert!(agrees(&problem, &proof(vec![(0, "1"), (2, "1/3")])));
    assert!(!agrees(
        &problem,
        &proof(vec![(0, "999999/1000000"), (2, "1/3")])
    ));
}

#[test]
fn negative_combined_coefficients_and_huge_products_are_valid() {
    let mut problem = Problem {
        places: vec!["p".into()],
        initial: vec![u64::MAX],
        transitions: vec![Transition {
            name: "read".into(),
            pre: vec![(0, u64::MAX)],
            post: vec![(0, u64::MAX)],
        }],
        target: vec![Constraint {
            coefficients: vec![i64::MIN],
            bound: i64::MIN,
            equality: true,
        }],
    };
    let huge = "1000000000000000000000000000000000000000000000000000000000001/13";
    assert!(agrees(&problem, &proof(vec![(2, huge)])));
    assert!(!agrees(&problem, &proof(vec![(1, huge)])));
    problem.transitions.clear();
    assert!(agrees(&problem, &proof(vec![(2, "1/7")])));
    problem.target[0].coefficients[0] = i64::MAX;
    problem.target[0].bound = i64::MAX;
    assert!(agrees(&problem, &proof(vec![(1, huge)])));
}

#[test]
fn malformed_certificates_preserve_strict_validation() {
    let problem = conversion();
    let valid = proof(vec![(0, "1"), (2, "1/3")]);
    assert!(agrees(&problem, &valid));
    for multipliers in [
        vec![],
        vec![(3, "1")],
        vec![(usize::MAX, "1")],
        vec![(0, "1"), (0, "1")],
        vec![(2, "1/3"), (0, "1")],
        vec![(0, "0"), (2, "1/3")],
        vec![(0, "-1"), (2, "1/3")],
        vec![(0, "1/0"), (2, "1/3")],
        vec![(0, "NaN"), (2, "1/3")],
    ] {
        assert!(!agrees(&problem, &proof(multipliers)));
    }
    for invalid in [
        json!({"kind": "wrong", "multipliers": [[0,"1"],[2,"1/3"]]}),
        json!({"kind": "sparse-farkas-v1", "multipliers": [[0,"1"],[2,"1/3"]], "extra": 1}),
        json!({"kind": "sparse-farkas-v1", "multipliers": [[-1,"1"]]}),
        json!({"kind": "sparse-farkas-v1", "multipliers": [[true,"1"]]}),
        json!({"kind": "sparse-farkas-v1", "multipliers": [[0,1]]}),
        json!({"kind": "sparse-farkas-v1", "multipliers": [[0,"1",0]]}),
        json!({"kind": "sparse-farkas-v1"}),
    ] {
        assert!(!agrees(&problem, &invalid));
    }
    let mut invalid_problem = problem.clone();
    invalid_problem.initial.pop();
    assert!(!agrees(&invalid_problem, &valid));
    invalid_problem = problem.clone();
    invalid_problem.transitions[0].pre.push((0, 1));
    assert!(!agrees(&invalid_problem, &valid));
    invalid_problem = problem;
    invalid_problem.target[0].coefficients.pop();
    assert!(!agrees(&invalid_problem, &valid));
}

#[test]
fn empty_place_space_keeps_constant_target_rows() {
    let problem = Problem {
        places: vec![],
        initial: vec![],
        transitions: vec![],
        target: vec![Constraint {
            coefficients: vec![],
            bound: -1,
            equality: true,
        }],
    };
    assert!(agrees(&problem, &proof(vec![(0, "1/3")])));
    assert!(!agrees(&problem, &proof(vec![(1, "1/3")])));
}
