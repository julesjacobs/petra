//! Native integer solving for one fixed sequence of positively repeated words.
//! Infeasibility excludes this scheme only; it never proves global unreachability.
use crate::{
    accelerated_bmc::{self, Segment},
    complete_arithmetic::{self, Answer, Limits, System},
    model::Problem,
    summary::sparse_summary,
};
use anyhow::{Result, ensure};
use num_bigint::BigInt;
use num_traits::{One, Zero};
use std::time::Instant;

struct Row {
    coefficients: Vec<(usize, BigInt)>,
    bound: BigInt,
    equality: bool,
}

fn rows(
    problem: &Problem,
    words: &[Vec<usize>],
    deadline: Instant,
    max_entries: usize,
) -> Result<Option<Vec<Row>>> {
    if max_entries == 0 || Instant::now() >= deadline {
        return Ok(None);
    }
    problem.validate()?;
    let mut work = problem.places.len().saturating_add(words.len());
    if work > max_entries {
        return Ok(None);
    }
    for word in words {
        ensure!(!word.is_empty(), "empty transition word");
        for &index in word {
            let tr = problem
                .transitions
                .get(index)
                .ok_or_else(|| anyhow::anyhow!("invalid transition index"))?;
            work = work
                .saturating_add(1)
                .saturating_add(tr.pre.len())
                .saturating_add(tr.post.len());
            if work > max_entries || Instant::now() >= deadline {
                return Ok(None);
            }
        }
    }
    let mut constant: Vec<BigInt> = problem.initial.iter().copied().map(BigInt::from).collect();
    let mut effects = vec![Vec::<(usize, BigInt)>::new(); problem.places.len()];
    let mut result = Vec::new();
    let mut inequalities = 0usize;
    let mut add = |row: Row| -> bool {
        inequalities += usize::from(!row.equality);
        let fits = result
            .len()
            .checked_add(1)
            .and_then(|n| n.checked_mul(words.len().checked_add(inequalities)?.checked_add(1)?))
            .is_some_and(|n| n <= max_entries);
        if !fits || Instant::now() >= deadline {
            return false;
        }
        result.push(row);
        true
    };
    for (i, word) in words.iter().enumerate() {
        let summary = sparse_summary(problem, word)?;
        for (&place, (hurdle, effect)) in &summary.places {
            if hurdle.is_zero() && effect >= &BigInt::zero() {
                continue;
            }
            let mut coefficients = effects[place].clone();
            let depletion = (-effect).max(BigInt::zero());
            if !depletion.is_zero() {
                coefficients.push((i, -depletion));
            }
            if !add(Row {
                coefficients,
                bound: hurdle - &constant[place],
                equality: false,
            }) {
                return Ok(None);
            }
        }
        for (place, (_, effect)) in summary.places {
            constant[place] += &effect;
            if !effect.is_zero() {
                effects[place].push((i, effect));
            }
        }
    }
    for target in &problem.target {
        let mut coefficients = vec![BigInt::zero(); words.len()];
        let mut bound = BigInt::from(target.bound);
        for (place, &weight) in target.coefficients.iter().enumerate() {
            if Instant::now() >= deadline {
                return Ok(None);
            }
            if weight == 0 {
                continue;
            }
            bound -= &constant[place] * weight;
            for (i, effect) in &effects[place] {
                coefficients[*i] += effect * weight;
            }
        }
        if !add(Row {
            coefficients: coefficients
                .into_iter()
                .enumerate()
                .filter(|(_, c)| !c.is_zero())
                .collect(),
            bound,
            equality: target.equality,
        }) {
            return Ok(None);
        }
    }
    Ok(Some(result))
}

/// Solve m0 --w0^n0 ... wk^nk--> target with every ni >= 1.
/// Variables are xi = ni - 1, so every prefix guard remains linear.
/// The caller enumerates omissions separately if zero repetitions are desired.
pub fn solve(
    problem: &Problem,
    words: &[Vec<usize>],
    limits: &Limits,
    max_entries: usize,
) -> Result<Answer<Vec<Segment>>> {
    let deadline = limits
        .deadline
        .ok_or_else(|| anyhow::anyhow!("scheme solving requires a deadline"))?;
    let Some(rows) = rows(problem, words, deadline, max_entries)? else {
        return Ok(Answer::Unknown("scheme construction limit"));
    };
    let variables = words.len() + rows.iter().filter(|r| !r.equality).count();
    let mut system = System {
        variables,
        a: Vec::new(),
        b: Vec::new(),
    };
    let mut slack = words.len();
    for row in rows {
        let mut coefficients = vec![BigInt::zero(); variables];
        for (i, coefficient) in row.coefficients {
            coefficients[i] = coefficient;
        }
        if !row.equality {
            coefficients[slack] = -BigInt::one();
            slack += 1;
        }
        system.a.push(coefficients);
        system.b.push(row.bound);
    }
    Ok(match complete_arithmetic::solve_integer(&system, limits) {
        Answer::Feasible(model) => {
            let segments: Vec<_> = words
                .iter()
                .zip(model)
                .map(|(word, x)| Segment {
                    word: word.clone(),
                    repetitions: (x + BigInt::one()).to_string(),
                })
                .collect();
            accelerated_bmc::check(problem, &segments)?;
            if Instant::now() >= deadline {
                Answer::Unknown("scheme checking deadline")
            } else {
                Answer::Feasible(segments)
            }
        }
        Answer::Infeasible => Answer::Infeasible,
        Answer::Unknown(reason) => Answer::Unknown(reason),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Constraint, Transition};
    use std::time::Duration;

    fn net() -> Problem {
        Problem {
            places: vec!["a".into(), "b".into()],
            initial: vec![0, 0],
            transitions: vec![
                Transition {
                    name: "move".into(),
                    pre: vec![(0, 2)],
                    post: vec![(1, 1)],
                },
                Transition {
                    name: "back".into(),
                    pre: vec![(1, 1)],
                    post: vec![(0, 3)],
                },
                Transition {
                    name: "read".into(),
                    pre: vec![(0, 2)],
                    post: vec![(0, 2)],
                },
                Transition {
                    name: "source".into(),
                    pre: vec![],
                    post: vec![(1, 1)],
                },
            ],
            target: vec![Constraint {
                coefficients: vec![-1, 2],
                bound: 0,
                equality: false,
            }],
        }
    }

    #[test]
    fn scheme_rows_match_original_transition_replay() {
        let vocabulary = [vec![0], vec![1], vec![2], vec![3], vec![0, 1], vec![1, 0]];
        let mut p = net();
        for equality in [false, true] {
            p.target[0].equality = equality;
            for a in 0..3 {
                for b in 0..3 {
                    p.initial = vec![a, b];
                    for left in &vocabulary {
                        for right in &vocabulary {
                            let words = vec![left.clone(), right.clone()];
                            let constraints =
                                rows(&p, &words, Instant::now() + Duration::from_secs(2), 10000)
                                    .unwrap()
                                    .unwrap();
                            for x in 0..4u64 {
                                for y in 0..4u64 {
                                    let counts = [x, y];
                                    let formula = constraints.iter().all(|row| {
                                        let value: BigInt = row
                                            .coefficients
                                            .iter()
                                            .map(|(i, c)| c * counts[*i])
                                            .sum();
                                        if row.equality {
                                            value == row.bound
                                        } else {
                                            value >= row.bound
                                        }
                                    });
                                    let mut marking = Some(p.initial.clone());
                                    for (word, count) in words.iter().zip(counts) {
                                        for _ in 0..=count {
                                            for &t in word {
                                                marking =
                                                    marking.and_then(|m| p.fire(&m, t).unwrap());
                                            }
                                        }
                                    }
                                    let accepted = marking.is_some_and(|m| p.accepts(&m).unwrap());
                                    assert_eq!(
                                        formula, accepted,
                                        "initial={:?} words={words:?} x={counts:?}",
                                        p.initial
                                    );
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    #[test]
    fn native_solver_finds_trillion_repetitions_and_rejects_read_guard() {
        let mut p = net();
        p.initial = vec![2, 0];
        p.target = vec![
            Constraint {
                coefficients: vec![1, 0],
                bound: 1_000_000_000_002,
                equality: true,
            },
            Constraint {
                coefficients: vec![0, 1],
                bound: 0,
                equality: true,
            },
        ];
        let words = vec![vec![0, 1]];
        let limits = Limits {
            deadline: Some(Instant::now() + Duration::from_secs(3)),
            max_rows: Some(1000),
            max_nodes: Some(1000),
        };
        let Answer::Feasible(segments) = solve(&p, &words, &limits, 10000).unwrap() else {
            panic!("no native witness")
        };
        assert_eq!(segments[0].repetitions, "1000000000000");
        p.initial = vec![1, 0];
        assert!(matches!(
            solve(&p, &words, &limits, 10000).unwrap(),
            Answer::Infeasible
        ));
    }

    #[test]
    fn exhausted_budget_is_unknown_and_empty_scheme_is_identity() {
        let p = net();
        let limits = Limits {
            deadline: Some(Instant::now() + Duration::from_secs(2)),
            ..Limits::default()
        };
        assert!(
            matches!(solve(&p, &[], &limits, 10000).unwrap(), Answer::Feasible(s) if s.is_empty())
        );
        assert!(matches!(
            solve(&p, &[vec![0]], &limits, 0).unwrap(),
            Answer::Unknown(_)
        ));
        let expired = Limits {
            deadline: Some(Instant::now()),
            ..Limits::default()
        };
        assert!(matches!(
            solve(&p, &[vec![0]], &expired, 10000).unwrap(),
            Answer::Unknown(_)
        ));
        assert!(solve(&p, &[vec![]], &limits, 10000).is_err());
        assert!(solve(&p, &[vec![99]], &limits, 10000).is_err());
    }
}
