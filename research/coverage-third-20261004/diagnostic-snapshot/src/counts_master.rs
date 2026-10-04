//! Exact elimination of final markings from a canonical token-cut master.
//! Proofs are lifted back to the original row numbering before acceptance.
use crate::linear::{Row, System};
use anyhow::{Context, Result, ensure};
use num_bigint::BigInt;
use num_rational::BigRational as Q;
use num_traits::{One, Signed, Zero};
use std::{collections::BTreeMap, time::Instant};

struct Marking {
    initial: BigInt,
    effects: Vec<(usize, BigInt)>,
}

pub(crate) struct CountsMaster {
    pub system: System,
    pub objective: Vec<BigInt>,
    markings: Vec<Marking>,
    lifts: Vec<Vec<(usize, BigInt)>>,
}

fn in_time(deadline: Instant) -> Result<()> {
    ensure!(
        Instant::now() < deadline,
        "counts-only master deadline exhausted"
    );
    Ok(())
}

impl CountsMaster {
    pub fn new(original: &System, places: usize, deadline: Instant) -> Result<Self> {
        in_time(deadline)?;
        let edges = original
            .variables
            .checked_sub(places)
            .context("missing marking variables")?;
        let prefix = places
            .checked_mul(2)
            .context("state-equation dimension overflow")?;
        ensure!(prefix <= original.rows.len(), "missing state-equation rows");
        let mut result = Self {
            system: System {
                variables: edges,
                rows: vec![],
            },
            objective: vec![BigInt::one(); edges],
            markings: Vec::with_capacity(places),
            lifts: vec![],
        };
        for p in 0..places {
            in_time(deadline)?;
            let negative = &original.rows[2 * p];
            let positive = &original.rows[2 * p + 1];
            ensure!(
                negative.bound == -&positive.bound
                    && negative.coefficients.len() == positive.coefficients.len(),
                "invalid state-equation pair"
            );
            let mut effects = vec![];
            let mut marking_terms = 0;
            for ((i, a), (j, b)) in negative.coefficients.iter().zip(&positive.coefficients) {
                in_time(deadline)?;
                ensure!(i == j && a == &-b, "invalid state-equation pair");
                if *i < edges {
                    effects.push((*i, a.clone()));
                    result.objective[*i] += a;
                } else {
                    ensure!(
                        *i == edges + p && a == &-BigInt::one(),
                        "invalid state-equation marking"
                    );
                    marking_terms += 1;
                }
            }
            ensure!(
                marking_terms == 1 && !negative.bound.is_positive(),
                "invalid initial marking equation"
            );
            // Nonnegativity of the reconstructed marking lifts to the negative
            // state equation, leaving a permissible negative marking column.
            result.push(
                Row {
                    coefficients: effects.clone(),
                    bound: negative.bound.clone(),
                },
                vec![(2 * p, BigInt::one())],
                deadline,
            )?;
            result.markings.push(Marking {
                initial: -&negative.bound,
                effects,
            });
        }
        for (index, row) in original.rows.iter().enumerate().skip(prefix) {
            in_time(deadline)?;
            let mut coefficients = BTreeMap::<usize, BigInt>::new();
            let mut bound = row.bound.clone();
            let mut lift = vec![(index, BigInt::one())];
            for (variable, coefficient) in &row.coefficients {
                in_time(deadline)?;
                if coefficient.is_zero() {
                    continue;
                }
                if *variable < edges {
                    *coefficients.entry(*variable).or_default() += coefficient;
                } else {
                    let place = variable - edges;
                    let marking = result
                        .markings
                        .get(place)
                        .context("invalid marking variable")?;
                    bound -= coefficient * &marking.initial;
                    for (edge, effect) in &marking.effects {
                        in_time(deadline)?;
                        *coefficients.entry(*edge).or_default() += coefficient * effect;
                    }
                    lift.push((
                        2 * place + usize::from(coefficient.is_negative()),
                        coefficient.abs(),
                    ));
                }
            }
            result.push(
                Row {
                    coefficients: coefficients.into_iter().collect(),
                    bound,
                },
                lift,
                deadline,
            )?;
        }
        in_time(deadline)?;
        Ok(result)
    }

    fn push(&mut self, row: Row, lift: Vec<(usize, BigInt)>, deadline: Instant) -> Result<()> {
        let mut merged = BTreeMap::<usize, BigInt>::new();
        for (i, a) in row.coefficients {
            in_time(deadline)?;
            *merged.entry(i).or_default() += a;
        }
        let coefficients: Vec<_> = merged.into_iter().filter(|(_, a)| !a.is_zero()).collect();
        if !coefficients.is_empty() || row.bound.is_positive() {
            self.system.rows.push(Row {
                coefficients,
                bound: row.bound,
            });
            self.lifts.push(lift);
        }
        in_time(deadline)
    }

    /// Translates a candidate. The canonical master must still check that the
    /// lifted multipliers form a contradiction before any implicit pricing.
    pub fn lift(
        &self,
        multipliers: &[(usize, String)],
        deadline: Instant,
    ) -> Result<Vec<(usize, String)>> {
        in_time(deadline)?;
        let mut lifted = BTreeMap::<usize, Q>::new();
        let mut previous = None;
        for (index, weight) in multipliers {
            in_time(deadline)?;
            ensure!(
                previous.is_none_or(|p| p < *index),
                "unordered or duplicate reduced multiplier"
            );
            previous = Some(*index);
            let weight: Q = weight.parse()?;
            ensure!(weight.is_positive(), "nonpositive reduced multiplier");
            for (original, factor) in self
                .lifts
                .get(*index)
                .context("invalid reduced proof row")?
            {
                in_time(deadline)?;
                *lifted.entry(*original).or_default() += &weight * factor;
            }
        }
        let mut result = Vec::with_capacity(lifted.len());
        for (index, weight) in lifted {
            in_time(deadline)?;
            if !weight.is_zero() {
                result.push((index, weight.to_string()));
            }
        }
        in_time(deadline)?;
        Ok(result)
    }

    pub fn reconstruct(
        &self,
        original: &System,
        counts: &[Q],
        deadline: Instant,
    ) -> Result<Vec<Q>> {
        in_time(deadline)?;
        ensure!(
            counts.len() == self.system.variables,
            "invalid count-model dimension"
        );
        let mut values = Vec::with_capacity(original.variables);
        for count in counts {
            in_time(deadline)?;
            ensure!(!count.is_negative(), "negative count-model value");
            values.push(count.clone());
        }
        for marking in &self.markings {
            in_time(deadline)?;
            let mut value = Q::from_integer(marking.initial.clone());
            for (edge, effect) in &marking.effects {
                in_time(deadline)?;
                value += &counts[*edge] * effect;
            }
            ensure!(!value.is_negative(), "negative reconstructed marking");
            values.push(value);
        }
        ensure!(
            values.len() == original.variables,
            "invalid reconstructed model dimension"
        );
        for row in &original.rows {
            in_time(deadline)?;
            let mut lhs = Q::zero();
            for (i, a) in &row.coefficients {
                in_time(deadline)?;
                lhs += values.get(*i).context("invalid canonical model variable")? * a;
            }
            ensure!(
                lhs >= Q::from_integer(row.bound.clone()),
                "reconstructed model violates canonical row"
            );
        }
        in_time(deadline)?;
        Ok(values)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        control::Edge,
        finite_control::{self, FiniteControl},
        model::{Constraint, Problem, Transition},
        token_cut::{self, Cut},
    };
    use std::time::Duration;

    fn deadline() -> Instant {
        Instant::now() + Duration::from_secs(5)
    }

    fn weighted() -> Problem {
        Problem {
            places: vec!["p".into(), "q".into(), "untouched".into()],
            initial: vec![2, 0, 7],
            transitions: vec![
                Transition {
                    name: "forward".into(),
                    pre: vec![(0, 2)],
                    post: vec![(1, 2)],
                },
                Transition {
                    name: "back".into(),
                    pre: vec![(1, 2)],
                    post: vec![(0, 2)],
                },
                Transition {
                    name: "read".into(),
                    pre: vec![(0, 1)],
                    post: vec![(0, 1)],
                },
            ],
            target: vec![],
        }
    }

    fn master(p: &Problem, graph: &FiniteControl, terminal: usize) -> System {
        let mut system = token_cut::master(p, graph, terminal).unwrap();
        for place in 0..p.places.len() {
            for mask in 0..1 << graph.modes.len() {
                let cut = Cut {
                    place,
                    modes: (0..graph.modes.len())
                        .filter(|q| mask & (1 << q) != 0)
                        .collect(),
                };
                system.rows.push(
                    token_cut::bounded_cut_row(
                        p,
                        graph,
                        terminal,
                        &cut,
                        &[Some(2.into()), Some(2.into()), Some(7.into())],
                    )
                    .unwrap(),
                );
            }
        }
        system
    }

    fn holds(system: &System, values: &[Q]) -> bool {
        values.len() == system.variables
            && values.iter().all(|x| !x.is_negative())
            && system.rows.iter().all(|row| {
                row.coefficients
                    .iter()
                    .map(|(i, a)| &values[*i] * a)
                    .sum::<Q>()
                    >= Q::from_integer(row.bound.clone())
            })
    }

    fn original_values(p: &Problem, graph: &FiniteControl, counts: &[Q]) -> Vec<Q> {
        let mut marking: Vec<_> = p
            .initial
            .iter()
            .map(|&n| Q::from_integer(n.into()))
            .collect();
        for (e, edge) in graph.edges.iter().enumerate() {
            let tr = &p.transitions[edge.transition];
            for &(i, n) in &tr.pre {
                marking[i] -= &counts[e] * BigInt::from(n);
            }
            for &(i, n) in &tr.post {
                marking[i] += &counts[e] * BigInt::from(n);
            }
        }
        counts.iter().cloned().chain(marking).collect()
    }

    #[test]
    fn elimination_preserves_every_sampled_weighted_count_model() {
        let mut p = weighted();
        let finite = vec![Some(2.into()), Some(2.into()), Some(7.into())];
        for controls in [vec![], vec![0], vec![0, 1]] {
            let graph = finite_control::build(&p, &controls, &finite, None).unwrap();
            assert!(graph.edges.len() <= 4);
            for coefficients in [vec![1, -1, 0], vec![-2, 3, -1], vec![0, 0, 1]] {
                for equality in [false, true] {
                    p.target = vec![Constraint {
                        coefficients: coefficients.clone(),
                        bound: 1,
                        equality,
                    }];
                    for q in 0..graph.modes.len() {
                        let original = master(&p, &graph, q);
                        let reduced =
                            CountsMaster::new(&original, p.places.len(), deadline()).unwrap();
                        for code in 0..4usize.pow(graph.edges.len() as u32) {
                            let counts: Vec<_> = (0..graph.edges.len())
                                .map(|e| {
                                    Q::new(((code / 4usize.pow(e as u32)) % 4).into(), 2.into())
                                })
                                .collect();
                            let full = original_values(&p, &graph, &counts);
                            let expected = holds(&original, &full);
                            assert_eq!(holds(&reduced.system, &counts), expected);
                            let reconstructed = reduced.reconstruct(&original, &counts, deadline());
                            assert_eq!(reconstructed.is_ok(), expected);
                            if expected {
                                assert_eq!(reconstructed.unwrap(), full);
                            }
                        }
                    }
                }
            }
        }
    }

    #[test]
    fn reduced_and_original_lp_models_and_refutations_agree() {
        let mut p = weighted();
        let finite = vec![Some(2.into()), Some(2.into()), Some(7.into())];
        let mut models = 0;
        let mut proofs = 0;
        for controls in [vec![], vec![0], vec![0, 1]] {
            let graph = finite_control::build(&p, &controls, &finite, None).unwrap();
            for target in -1..=3 {
                p.target = vec![Constraint {
                    coefficients: vec![1, 0, 0],
                    bound: target,
                    equality: true,
                }];
                for q in 0..graph.modes.len() {
                    let original = master(&p, &graph, q);
                    let reduced = CountsMaster::new(&original, p.places.len(), deadline()).unwrap();
                    if let Some(proof) = original.refute(deadline()) {
                        original.check(&proof).unwrap();
                        let reduced_proof = reduced.system.refute(deadline()).unwrap();
                        let lifted = reduced.lift(&reduced_proof, deadline()).unwrap();
                        original.check(&lifted).unwrap();
                        proofs += 1;
                    } else {
                        let full = original.rational_model(deadline()).unwrap();
                        let counts = reduced
                            .system
                            .rational_model_with_objective(&reduced.objective, deadline())
                            .unwrap();
                        let reconstructed =
                            reduced.reconstruct(&original, &counts, deadline()).unwrap();
                        assert!(holds(&original, &reconstructed));
                        assert_eq!(full.iter().sum::<Q>(), reconstructed.iter().sum::<Q>());
                        models += 1;
                    }
                }
            }
        }
        assert!(models > 0 && proofs > 0);
    }

    #[test]
    fn consuming_two_tokens_preserves_the_negative_objective_coefficient() {
        let p = Problem {
            places: vec!["x".into()],
            initial: vec![2],
            transitions: vec![Transition {
                name: "consume".into(),
                pre: vec![(0, 2)],
                post: vec![],
            }],
            target: vec![],
        };
        let graph = finite_control::build(&p, &[], &[], None).unwrap();
        let original = token_cut::master(&p, &graph, 0).unwrap();
        let reduced = CountsMaster::new(&original, 1, deadline()).unwrap();
        assert_eq!(reduced.objective, vec![BigInt::from(-1)]);
        let counts = reduced
            .system
            .rational_model_with_objective(&reduced.objective, deadline())
            .unwrap();
        assert_eq!(counts, vec![Q::one()]);
        let full = reduced.reconstruct(&original, &counts, deadline()).unwrap();
        assert_eq!(full, vec![Q::one(), Q::zero()]);
        assert_eq!(original.rational_model(deadline()).unwrap(), full);
        assert_eq!(
            reduced.system.rational_model(deadline()).unwrap(),
            vec![Q::zero()]
        );
    }

    #[test]
    fn every_lift_is_a_nonnegative_combination_with_exact_bound_and_count_columns() {
        let mut p = weighted();
        p.target = vec![Constraint {
            coefficients: vec![2, -3, 1],
            bound: 3,
            equality: true,
        }];
        let graph = finite_control::build(&p, &[0], &[Some(2.into())], None).unwrap();
        let original = master(&p, &graph, 1);
        let reduced = CountsMaster::new(&original, p.places.len(), deadline()).unwrap();
        let mut positive_equation_used = false;
        let mut negative_equation_used = false;
        let mut cut_used = false;
        for (index, row) in reduced.system.rows.iter().enumerate() {
            let lifted = reduced.lift(&[(index, "1".into())], deadline()).unwrap();
            let mut coefficients = vec![Q::zero(); original.variables];
            let mut bound = Q::zero();
            for (i, weight) in lifted {
                let weight: Q = weight.parse().unwrap();
                assert!(weight.is_positive());
                positive_equation_used |= i < 2 * p.places.len() && i % 2 == 1;
                negative_equation_used |= i < 2 * p.places.len() && i % 2 == 0;
                cut_used |=
                    i >= 2 * p.places.len() + 2 * graph.places.len() + 2 + 2 * graph.modes.len();
                for (variable, a) in &original.rows[i].coefficients {
                    coefficients[*variable] += &weight * a;
                }
                bound += &weight * &original.rows[i].bound;
            }
            assert_eq!(bound, Q::from_integer(row.bound.clone()));
            let mut expected = vec![Q::zero(); graph.edges.len()];
            for (i, a) in &row.coefficients {
                expected[*i] += Q::from_integer(a.clone());
            }
            assert_eq!(&coefficients[..graph.edges.len()], expected);
            assert!(
                coefficients[graph.edges.len()..]
                    .iter()
                    .all(|a| !a.is_positive())
            );
        }
        assert!(positive_equation_used && negative_equation_used && cut_used);
    }

    #[test]
    fn a_dropped_nonnegativity_row_returns_when_an_active_column_changes_it() {
        let p = Problem {
            places: vec!["x".into()],
            initial: vec![0],
            transitions: vec![Transition {
                name: "consume".into(),
                pre: vec![(0, 1)],
                post: vec![],
            }],
            target: vec![],
        };
        let mut graph = finite_control::build_without_stutters(&p, &[], &[], None).unwrap();
        let original = token_cut::master(&p, &graph, 0).unwrap();
        let reduced = CountsMaster::new(&original, 1, deadline()).unwrap();
        assert!(reduced.system.rows.is_empty());
        graph.edges.push(Edge {
            source: 0,
            target: 0,
            transition: 0,
        });
        let original = token_cut::master(&p, &graph, 0).unwrap();
        let reduced = CountsMaster::new(&original, 1, deadline()).unwrap();
        assert_eq!(reduced.system.rows.len(), 1);
        assert_eq!(
            reduced.system.rows[0].coefficients,
            vec![(0, BigInt::from(-1))]
        );
        assert!(
            reduced
                .reconstruct(&original, &[Q::one()], deadline())
                .is_err()
        );
        assert!(
            reduced
                .reconstruct(&original, &[Q::zero()], deadline())
                .is_ok()
        );
    }

    #[test]
    fn malformed_candidates_equations_and_expired_deadlines_are_rejected() {
        let p = weighted();
        let graph = finite_control::build(&p, &[], &[], None).unwrap();
        let original = token_cut::master(&p, &graph, 0).unwrap();
        let reduced = CountsMaster::new(&original, p.places.len(), deadline()).unwrap();
        for bad in [
            vec![(0, "-1".into())],
            vec![(0, "0".into())],
            vec![(usize::MAX, "1".into())],
            vec![(0, "1".into()), (0, "1".into())],
        ] {
            assert!(reduced.lift(&bad, deadline()).is_err());
        }
        assert!(
            original
                .check(&reduced.lift(&[], deadline()).unwrap())
                .is_err()
        );
        assert!(
            original
                .check(&reduced.lift(&[(0, "1".into())], deadline()).unwrap())
                .is_err()
        );
        assert!(reduced.reconstruct(&original, &[], deadline()).is_err());
        let mut counts = vec![Q::zero(); graph.edges.len()];
        counts[0] = -Q::one();
        assert!(reduced.reconstruct(&original, &counts, deadline()).is_err());
        let expired = Instant::now();
        assert!(CountsMaster::new(&original, p.places.len(), expired).is_err());
        assert!(reduced.lift(&[], expired).is_err());
        assert!(
            reduced
                .reconstruct(&original, &vec![Q::zero(); graph.edges.len()], expired)
                .is_err()
        );
        assert!(
            reduced
                .system
                .rational_model_with_objective(&reduced.objective, expired)
                .is_err()
        );
        assert!(
            reduced
                .system
                .rational_model_with_objective(&[], deadline())
                .is_err()
        );
        let mut broken = original.clone();
        broken.rows[1].bound += 1;
        assert!(CountsMaster::new(&broken, p.places.len(), deadline()).is_err());
        assert!(CountsMaster::new(&original, usize::MAX, deadline()).is_err());
    }
}
