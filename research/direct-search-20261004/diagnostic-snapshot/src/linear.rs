//! Sparse Farkas certificates. Floating-point optimization only proposes proofs.
use crate::{model::Problem, search::Outcome};
use anyhow::{Context, Result, ensure};
use microlp::{ComparisonOp, OptimizationDirection};
use num_bigint::BigInt;
use num_rational::BigRational as Q;
use num_traits::{Signed, ToPrimitive, Zero};
use serde::{Deserialize, Serialize};
use std::{
    collections::BTreeMap,
    time::{Duration, Instant},
};

/// Variables are nonnegative; each row means `coefficients * x >= bound`.
#[derive(Clone)]
pub struct Row {
    pub coefficients: Vec<(usize, BigInt)>,
    pub bound: BigInt,
}

#[derive(Clone)]
pub struct System {
    pub variables: usize,
    pub rows: Vec<Row>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Certificate {
    pub kind: String,
    pub multipliers: Vec<(usize, String)>,
}

impl System {
    /// Numerical optimization proposes a model; every accepted row is checked exactly.
    pub fn rational_model(&self, deadline: Instant) -> Option<Vec<Q>> {
        self.rational_model_inner(None, deadline).ok()
    }

    pub(crate) fn rational_model_with_objective(
        &self,
        objective: &[BigInt],
        deadline: Instant,
    ) -> Result<Vec<Q>> {
        ensure!(
            objective.len() == self.variables,
            "invalid primal objective dimension"
        );
        self.rational_model_inner(Some(objective), deadline)
    }

    fn rational_model_inner(
        &self,
        objective: Option<&[BigInt]>,
        deadline: Instant,
    ) -> Result<Vec<Q>> {
        let in_time = || -> Result<()> {
            ensure!(Instant::now() < deadline, "primal model deadline exhausted");
            Ok(())
        };
        in_time()?;
        let mut lp = microlp::Problem::new(OptimizationDirection::Minimize);
        let variables: Vec<_> = (0..self.variables)
            .map(|i| -> Result<_> {
                in_time()?;
                let cost = match objective {
                    Some(costs) => costs[i]
                        .to_f64()
                        .context("unrepresentable primal objective")?,
                    None => 1.0,
                };
                ensure!(cost.is_finite(), "nonfinite primal objective");
                Ok(lp.add_var(cost, (0.0, f64::INFINITY)))
            })
            .collect::<Result<_>>()?;
        for row in &self.rows {
            in_time()?;
            let mut merged = BTreeMap::<usize, BigInt>::new();
            for (index, coefficient) in &row.coefficients {
                in_time()?;
                variables.get(*index).context("invalid primal variable")?;
                *merged.entry(*index).or_default() += coefficient;
            }
            let mut coefficients = Vec::with_capacity(merged.len());
            for (index, coefficient) in merged {
                in_time()?;
                if coefficient.is_zero() {
                    continue;
                }
                let value = coefficient
                    .to_f64()
                    .context("unrepresentable primal coefficient")?;
                ensure!(value.is_finite(), "nonfinite primal coefficient");
                coefficients.push((variables[index], value));
            }
            if coefficients.is_empty() {
                ensure!(
                    !row.bound.is_positive(),
                    "contradictory constant primal row"
                );
                continue;
            }
            let bound = row.bound.to_f64().context("unrepresentable primal bound")?;
            ensure!(bound.is_finite(), "nonfinite primal bound");
            lp.add_constraint(coefficients, ComparisonOp::Ge, bound);
        }
        lp.set_time_limit(deadline.saturating_duration_since(Instant::now()));
        let outcome = lp
            .solve()
            .context("numerical primal solve failed to produce a model")?;
        let solution = outcome.into_solution().map_err(|interrupted| {
            anyhow::anyhow!(
                "primal solve interrupted: {:?}",
                interrupted.termination_reason()
            )
        })?;
        let values: Vec<_> = variables.iter().map(|&v| solution.var_value(v)).collect();
        for denominator in [16, 256, 4096, 65536, 1_000_000] {
            in_time()?;
            let candidate = values
                .iter()
                .map(|&value| {
                    in_time()?;
                    approximate_nonnegative(value, denominator)
                        .context("primal rational reconstruction failed")
                })
                .collect::<Result<Vec<_>>>()?;
            let mut valid = true;
            for row in &self.rows {
                in_time()?;
                let mut lhs = Q::zero();
                for (index, coefficient) in &row.coefficients {
                    in_time()?;
                    lhs += &candidate[*index] * coefficient;
                }
                if lhs < Q::from_integer(row.bound.clone()) {
                    valid = false;
                    break;
                }
            }
            if valid {
                in_time()?;
                return Ok(candidate);
            }
        }
        anyhow::bail!("no exactly checked rational reconstruction of primal model")
    }

    pub fn integer_model(&self, deadline: Instant, cap: u32) -> Option<Vec<u64>> {
        if Instant::now() >= deadline || cap > i32::MAX as u32 {
            return None;
        }
        let mut lp = microlp::Problem::new(OptimizationDirection::Minimize);
        let variables: Vec<_> = (0..self.variables)
            .map(|_| lp.add_integer_var(1.0, (0, cap as i32)))
            .collect();
        lp.add_constraint(
            variables.iter().map(|&v| (v, 1.0)),
            ComparisonOp::Le,
            f64::from(cap),
        );
        for row in &self.rows {
            if Instant::now() >= deadline {
                return None;
            }
            let mut coefficients = vec![];
            for (i, a) in &row.coefficients {
                let value = a.to_f64()?;
                if !value.is_finite() {
                    return None;
                }
                coefficients.push((*variables.get(*i)?, value));
            }
            let bound = row.bound.to_f64()?;
            if !bound.is_finite() {
                return None;
            }
            lp.add_constraint(coefficients, ComparisonOp::Ge, bound);
        }
        lp.set_time_limit(deadline.saturating_duration_since(Instant::now()));
        let solution = lp.solve().ok()?.into_solution().ok()?;
        let values: Vec<u64> = variables
            .iter()
            .map(|&v| {
                let value = solution.var_value(v).round();
                (value.is_finite() && (0.0..=f64::from(cap)).contains(&value))
                    .then_some(value as u64)
            })
            .collect::<Option<_>>()?;
        if values.iter().sum::<u64>() > u64::from(cap) {
            return None;
        }
        for row in &self.rows {
            let lhs: BigInt = row.coefficients.iter().map(|(i, a)| a * values[*i]).sum();
            if lhs < row.bound {
                return None;
            }
        }
        Some(values)
    }

    pub fn check(&self, multipliers: &[(usize, String)]) -> Result<()> {
        let mut lhs = vec![Q::zero(); self.variables];
        let mut rhs = Q::zero();
        let mut previous = None;
        for (index, weight) in multipliers {
            ensure!(
                previous.is_none_or(|p| p < *index),
                "unordered or duplicate multiplier"
            );
            previous = Some(*index);
            let row = self.rows.get(*index).context("invalid Farkas row")?;
            let weight: Q = weight.parse()?;
            ensure!(weight.is_positive(), "nonpositive Farkas multiplier");
            for (variable, coefficient) in &row.coefficients {
                let entry = lhs.get_mut(*variable).context("invalid variable")?;
                *entry += &weight * coefficient;
            }
            rhs += weight * &row.bound;
        }
        ensure!(
            lhs.iter().all(|x| !x.is_positive()) && rhs.is_positive(),
            "invalid sparse Farkas contradiction"
        );
        Ok(())
    }

    pub fn refute(&self, deadline: Instant) -> Option<Vec<(usize, String)>> {
        if self.rows.is_empty() || Instant::now() >= deadline {
            return None;
        }
        if let Some(index) = self
            .rows
            .iter()
            .position(|r| r.coefficients.iter().all(|(_, v)| v.is_zero()) && r.bound.is_positive())
        {
            return Some(vec![(index, "1".into())]);
        }
        let mut lp = microlp::Problem::new(OptimizationDirection::Maximize);
        let mut columns = vec![vec![]; self.variables];
        let scale = self
            .rows
            .iter()
            .map(|r| r.bound.abs().to_f64())
            .collect::<Option<Vec<_>>>()?
            .into_iter()
            .fold(1.0_f64, f64::max);
        if !scale.is_finite() {
            return None;
        }
        let mut weights = Vec::with_capacity(self.rows.len());
        for row in &self.rows {
            if Instant::now() >= deadline {
                return None;
            }
            let weight = lp.add_var(row.bound.to_f64()? / scale, (0.0, 1.0));
            weights.push(weight);
            for (variable, coefficient) in &row.coefficients {
                let value = coefficient.to_f64()?;
                if !value.is_finite() {
                    return None;
                }
                columns.get_mut(*variable)?.push((weight, value));
            }
        }
        lp.add_constraint(weights.iter().map(|&v| (v, 1.0)), ComparisonOp::Eq, 1.0);
        for column in columns {
            if Instant::now() >= deadline {
                return None;
            }
            if !column.is_empty() {
                lp.add_constraint(column, ComparisonOp::Le, 0.0);
            }
        }
        lp.set_time_limit(deadline.saturating_duration_since(Instant::now()));
        let solution = lp.solve().ok()?.into_solution().ok()?;
        // Optimality is unnecessary: any positive, exactly checked dual works.
        let values: Vec<_> = weights.iter().map(|&v| solution.var_value(v)).collect();
        for denominator in [16, 256, 4096, 65536, 1_000_000] {
            if Instant::now() >= deadline {
                return None;
            }
            let mut multipliers = vec![];
            for (i, &value) in values.iter().enumerate() {
                let weight = approximate(value, denominator)?;
                if !weight.is_zero() {
                    multipliers.push((i, weight.to_string()));
                }
            }
            if self.check(&multipliers).is_ok() {
                return Some(multipliers);
            }
        }
        None
    }
}

fn approximate_nonnegative(value: f64, limit: u64) -> Option<Q> {
    if !value.is_finite() || value < -1e-8 {
        return None;
    }
    let value = value.max(0.0);
    let integer = value.floor();
    Some(Q::from_float(integer)? + approximate(value - integer, limit)?)
}

fn approximate(value: f64, limit: u64) -> Option<Q> {
    if !value.is_finite() || !(-1e-8..=1.0 + 1e-8).contains(&value) {
        return None;
    }
    let value = value.clamp(0.0, 1.0);
    if value <= 1e-10 {
        return Some(Q::zero());
    }
    let (mut p0, mut q0, mut p1, mut q1) = (0u64, 1u64, 1u64, 0u64);
    let mut x = value;
    loop {
        let a = x.floor() as u64;
        let Some(q2) = a.checked_mul(q1).and_then(|y| q0.checked_add(y)) else {
            break;
        };
        if q2 > limit {
            break;
        }
        let p2 = a.checked_mul(p1)?.checked_add(p0)?;
        (p0, q0, p1, q1) = (p1, q1, p2, q2);
        let fractional = x - a as f64;
        if fractional < 1e-12 {
            return Some(Q::new(p1.into(), q1.into()));
        }
        x = 1.0 / fractional;
    }
    let k = (limit - q0) / q1;
    let (p2, q2) = (p0 + k * p1, q0 + k * q1);
    let (p, q) = if (p2 as f64 / q2 as f64 - value).abs() < (p1 as f64 / q1 as f64 - value).abs() {
        (p2, q2)
    } else {
        (p1, q1)
    };
    Some(Q::new(p.into(), q.into()))
}

pub fn state_equation(p: &Problem) -> System {
    let mut places = vec![BTreeMap::<usize, BigInt>::new(); p.places.len()];
    for (t, transition) in p.transitions.iter().enumerate() {
        for &(i, w) in &transition.pre {
            *places[i].entry(t).or_default() -= w;
        }
        for &(i, w) in &transition.post {
            *places[i].entry(t).or_default() += w;
        }
    }
    let mut rows: Vec<_> = places
        .iter()
        .zip(&p.initial)
        .map(|(a, m)| Row {
            coefficients: a
                .iter()
                .filter(|(_, v)| !v.is_zero())
                .map(|(&i, v)| (i, v.clone()))
                .collect(),
            bound: -BigInt::from(*m),
        })
        .collect();
    for c in &p.target {
        let mut coefficients = BTreeMap::<usize, BigInt>::new();
        let mut bound = BigInt::from(c.bound);
        for (i, &a) in c.coefficients.iter().enumerate().filter(|(_, a)| **a != 0) {
            bound -= BigInt::from(a) * p.initial[i];
            for (t, delta) in &places[i] {
                *coefficients.entry(*t).or_default() += delta * a;
            }
        }
        let coefficients: Vec<_> = coefficients
            .into_iter()
            .filter(|(_, v)| !v.is_zero())
            .collect();
        if c.equality {
            rows.push(Row {
                coefficients: coefficients.iter().map(|(i, v)| (*i, -v)).collect(),
                bound: -&bound,
            });
        }
        rows.push(Row {
            coefficients,
            bound,
        });
    }
    System {
        variables: p.transitions.len(),
        rows,
    }
}

pub fn verify_certificate(p: &Problem, value: &serde_json::Value) -> Result<()> {
    p.validate()?;
    let proof: Certificate = serde_json::from_value(value.clone())?;
    ensure!(proof.kind == "sparse-farkas-v1", "wrong proof kind");
    let target_rows: Vec<_> = p
        .target
        .iter()
        .flat_map(|target| {
            target
                .equality
                .then_some((target, -1))
                .into_iter()
                .chain(std::iter::once((target, 1)))
        })
        .collect();
    let mut weights = vec![Q::zero(); p.places.len()];
    let mut rhs = Q::zero();
    let mut previous = None;
    for (index, weight) in proof.multipliers {
        ensure!(
            previous.is_none_or(|row| row < index),
            "unordered or duplicate multiplier"
        );
        previous = Some(index);
        let weight: Q = weight.parse()?;
        ensure!(weight.is_positive(), "nonpositive Farkas multiplier");
        if let Some(entry) = weights.get_mut(index) {
            *entry += weight;
        } else {
            let (target, sign) = target_rows
                .get(index - p.places.len())
                .context("invalid Farkas row")?;
            let weight = weight * BigInt::from(*sign);
            rhs += &weight * BigInt::from(target.bound);
            for (entry, &coefficient) in weights.iter_mut().zip(&target.coefficients) {
                if coefficient != 0 {
                    *entry += &weight * BigInt::from(coefficient);
                }
            }
        }
    }
    for (weight, &initial) in weights.iter().zip(&p.initial) {
        if initial != 0 {
            rhs -= weight * BigInt::from(initial);
        }
    }
    ensure!(rhs.is_positive(), "invalid sparse Farkas contradiction");
    for transition in &p.transitions {
        let sum = |arcs: &[(usize, u64)]| -> Q {
            arcs.iter()
                .filter(|(place, _)| !weights[*place].is_zero())
                .map(|&(place, count)| &weights[place] * BigInt::from(count))
                .sum()
        };
        ensure!(
            sum(&transition.post) <= sum(&transition.pre),
            "invalid sparse Farkas contradiction"
        );
    }
    Ok(())
}

pub fn solve(p: &Problem, timeout: Duration) -> Outcome {
    let start = Instant::now();
    if timeout.is_zero() || p.validate().is_err() {
        return Outcome::unknown("sparse-state-equation", "no budget or invalid net", 0);
    }
    let system = state_equation(p);
    let Some(multipliers) = system.refute(start + timeout) else {
        return Outcome::unknown(
            "sparse-state-equation",
            "no exact dual certificate within limits",
            0,
        );
    };
    let proof = serde_json::to_value(Certificate {
        kind: "sparse-farkas-v1".into(),
        multipliers,
    })
    .unwrap();
    let mut out = Outcome::unknown(
        "sparse-state-equation",
        "exact sparse Farkas certificate",
        0,
    );
    out.verdict = "unreachable";
    out.proof = Some(proof);
    out
}
