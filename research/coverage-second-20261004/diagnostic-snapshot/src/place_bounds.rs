//! Certified finite bounds from nonnegative, nonincreasing place potentials.
//!
//! For every original transition, the checker proves `w * post <= w * pre`.
//! Induction over firing sequences gives `w * m <= w * initial` for every
//! reachable marking. Nonnegativity then gives the global bound
//! `m[p] <= floor((w * initial) / w[p])` whenever `w[p] > 0`.
//! A verified potential therefore supplies bounds for all its positive places.
use crate::{
    linear::{Row, System},
    model::Problem,
};
use anyhow::{Context, Result, ensure};
use num_bigint::BigInt;
use num_rational::BigRational as Q;
use num_traits::{Signed, Zero};
use serde::{Deserialize, Serialize};
use std::{collections::BTreeMap, time::Instant};

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Potential {
    pub weights: Vec<(usize, String)>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Certificate {
    pub kind: String,
    pub potentials: Vec<Potential>,
}

impl Default for Certificate {
    fn default() -> Self {
        Self {
            kind: "place-bounds-v1".into(),
            potentials: vec![],
        }
    }
}

fn check_potential(problem: &Problem, potential: &Potential) -> Result<Vec<Option<BigInt>>> {
    ensure!(!potential.weights.is_empty(), "empty place potential");
    let mut weights = vec![Q::zero(); problem.places.len()];
    let mut previous = None;
    for (place, value) in &potential.weights {
        ensure!(
            previous.is_none_or(|p| p < *place),
            "unordered or duplicate potential place"
        );
        previous = Some(*place);
        let weight: Q = value.parse().context("invalid rational potential weight")?;
        ensure!(weight.is_positive(), "nonpositive potential weight");
        *weights.get_mut(*place).context("invalid potential place")? = weight;
    }
    for transition in &problem.transitions {
        let pre: Q = transition
            .pre
            .iter()
            .map(|(p, n)| &weights[*p] * BigInt::from(*n))
            .sum();
        let post: Q = transition
            .post
            .iter()
            .map(|(p, n)| &weights[*p] * BigInt::from(*n))
            .sum();
        ensure!(post <= pre, "place potential increases on a transition");
    }
    let initial: Q = weights
        .iter()
        .zip(&problem.initial)
        .map(|(w, n)| w * BigInt::from(*n))
        .sum();
    Ok(weights
        .iter()
        .map(|weight| {
            if weight.is_zero() {
                None
            } else {
                // All quantities are nonnegative, so integer division is floor.
                Some((&initial / weight).to_integer())
            }
        })
        .collect())
}

fn merge_bounds(bounds: &mut [Option<BigInt>], candidate: Vec<Option<BigInt>>) {
    for (bound, proposed) in bounds.iter_mut().zip(candidate) {
        if let Some(proposed) = proposed
            && bound.as_ref().is_none_or(|current| proposed < *current)
        {
            *bound = Some(proposed);
        }
    }
}

/// Return the strongest bound provided by these potentials for each place.
/// `None` says only that this certificate supplies no bound for that place.
pub fn check(problem: &Problem, certificate: &Certificate) -> Result<Vec<Option<BigInt>>> {
    problem.validate()?;
    ensure!(
        certificate.kind == "place-bounds-v1",
        "invalid place-bound certificate kind"
    );
    let mut bounds = vec![None; problem.places.len()];
    for potential in &certificate.potentials {
        merge_bounds(&mut bounds, check_potential(problem, potential)?);
    }
    Ok(bounds)
}

/// Propose normalized nonincreasing potentials, keeping only exact proofs.
/// Discovery can miss bounds and does not decide boundedness.
/// Each still-uncovered coordinate receives a share of the remaining time;
/// failed proposals are tried once and never certify absence of a bound.
pub fn discover(problem: &Problem, deadline: Instant) -> Certificate {
    let mut certificate = Certificate::default();
    if problem.validate().is_err() || Instant::now() >= deadline {
        return certificate;
    }
    let mut system = System {
        variables: problem.places.len(),
        rows: vec![],
    };
    for transition in &problem.transitions {
        if Instant::now() >= deadline {
            return certificate;
        }
        let mut coefficients = BTreeMap::<usize, BigInt>::new();
        for &(place, count) in &transition.pre {
            *coefficients.entry(place).or_default() += count;
        }
        for &(place, count) in &transition.post {
            *coefficients.entry(place).or_default() -= count;
        }
        system.rows.push(Row {
            coefficients: coefficients
                .into_iter()
                .filter(|(_, value)| !value.is_zero())
                .collect(),
            bound: BigInt::zero(),
        });
    }
    let mut bounds = vec![None; problem.places.len()];
    for place in 0..problem.places.len() {
        if Instant::now() >= deadline {
            break;
        }
        if bounds[place].is_some() {
            continue;
        }
        let remaining = bounds[place..]
            .iter()
            .filter(|bound| bound.is_none())
            .count();
        let slice = deadline.saturating_duration_since(Instant::now())
            / u32::try_from(remaining).unwrap_or(u32::MAX);
        let candidate_deadline = (Instant::now() + slice).min(deadline);
        system.rows.push(Row {
            coefficients: vec![(place, BigInt::from(1))],
            bound: BigInt::from(1),
        });
        let candidate = system.rational_model(candidate_deadline);
        system.rows.pop();
        let Some(candidate) = candidate else {
            continue;
        };
        let potential = Potential {
            weights: candidate
                .into_iter()
                .enumerate()
                .filter(|(_, weight)| !weight.is_zero())
                .map(|(place, weight)| (place, weight.to_string()))
                .collect(),
        };
        if let Ok(candidate_bounds) = check_potential(problem, &potential) {
            merge_bounds(&mut bounds, candidate_bounds);
            certificate.potentials.push(potential);
        }
    }
    certificate
}
