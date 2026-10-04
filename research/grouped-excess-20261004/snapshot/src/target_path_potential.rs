//! Total-mass bounds on target-reaching paths, encoded as ordinary slack guards.
//! These bounds are not global invariants of the original net.
use crate::model::{Constraint, Problem, Transition};
use anyhow::{Context, Result, ensure};
use serde_json::{Map, Value};
use std::{collections::HashSet, time::Instant};

#[derive(Debug)]
pub enum Preparation {
    Infeasible,
    Reduced(Prepared),
}

#[derive(Debug)]
pub struct Prepared {
    pub problem: Problem,
    pub bound: i128,
    pub slack: u64,
}

struct Budget {
    deadline: Instant,
    remaining: usize,
}
impl Budget {
    fn tick(&mut self, work: usize) -> Result<()> {
        ensure!(
            Instant::now() < self.deadline,
            "target-path potential deadline"
        );
        self.remaining = self
            .remaining
            .checked_sub(work)
            .context("target-path potential work limit")?;
        Ok(())
    }
}

struct Candidate {
    bound: i128,
    slack: u64,
    increases: Vec<u64>,
}
enum Inference {
    Infeasible,
    Useful(Candidate),
}

fn infer(p: &Problem, budget: &mut Budget) -> Result<Option<Inference>> {
    let n = p.places.len();
    budget.tick(
        n.saturating_mul(2)
            .saturating_add(p.transitions.len())
            .saturating_add(1),
    )?;
    ensure!(p.initial.len() == n, "initial marking dimension mismatch");
    let mut upper = vec![None::<i128>; n];
    for c in &p.target {
        budget.tick(1)?;
        ensure!(c.coefficients.len() == n, "constraint dimension mismatch");
        let mut term = None;
        let mut multiple = false;
        for (place, &a) in c.coefficients.iter().enumerate() {
            budget.tick(1)?;
            if a != 0 {
                multiple |= term.is_some();
                term = Some((place, i128::from(a)));
            }
        }
        if !multiple
            && let Some((place, a)) = term
            && (c.equality || a < 0)
        {
            let b = i128::from(c.bound);
            let (numerator, denominator) = if a < 0 { (-b, -a) } else { (b, a) };
            let bound = numerator.div_euclid(denominator);
            upper[place] = Some(upper[place].map_or(bound, |old| old.min(bound)));
        }
    }
    let mut seen = vec![0usize; n];
    let mut generation = 0usize;
    let mut deltas = Vec::new();
    let mut decreasing = false;
    let mut growing = false;
    for t in &p.transitions {
        budget.tick(1)?;
        let mut sums = [0i128; 2];
        for (side, arcs) in [&t.pre, &t.post].into_iter().enumerate() {
            generation = generation.checked_add(1).context("too many arc lists")?;
            for &(place, weight) in arcs {
                budget.tick(1)?;
                ensure!(place < n && weight > 0, "invalid arc");
                ensure!(seen[place] != generation, "repeated arc");
                seen[place] = generation;
                sums[side] = sums[side]
                    .checked_add(i128::from(weight))
                    .context("incidence sum overflow")?;
            }
        }
        let delta = sums[1]
            .checked_sub(sums[0])
            .context("incidence difference overflow")?;
        decreasing |= delta < 0;
        growing |= delta > 0;
        deltas.push(delta);
    }
    budget.tick(0)?;
    if n == 0 || decreasing {
        return Ok(None);
    }
    let mut bound = 0i128;
    let mut initial = 0i128;
    for (upper, &tokens) in upper.into_iter().zip(&p.initial) {
        budget.tick(1)?;
        let Some(upper) = upper else {
            return Ok(None);
        };
        bound = bound
            .checked_add(upper)
            .context("target mass bound overflow")?;
        initial = initial
            .checked_add(i128::from(tokens))
            .context("initial mass overflow")?;
    }
    budget.tick(0)?;
    if bound < initial {
        return Ok(Some(Inference::Infeasible));
    }
    if !growing {
        return Ok(None);
    }
    let slack = u64::try_from(
        bound
            .checked_sub(initial)
            .context("slack subtraction overflow")?,
    )
    .context("initial slack is not representable")?;
    let mut increases = Vec::new();
    for delta in deltas {
        budget.tick(1)?;
        increases.push(u64::try_from(delta).context("slack arc is not representable")?);
    }
    budget.tick(0)?;
    Ok(Some(Inference::Useful(Candidate {
        bound,
        slack,
        increases,
    })))
}

fn augment(p: &Problem, candidate: Candidate, budget: &mut Budget) -> Result<Prepared> {
    let n = p.places.len();
    budget.tick(n.saturating_add(1))?;
    let mut names = HashSet::new();
    let mut net = Problem {
        places: vec![],
        initial: vec![],
        transitions: vec![],
        target: vec![],
    };
    for (name, &tokens) in p.places.iter().zip(&p.initial) {
        budget.tick(name.len().saturating_mul(2).saturating_add(1))?;
        names.insert(name.as_str());
        net.places.push(name.clone());
        net.initial.push(tokens);
    }
    let mut slack_name = "__target_path_slack".to_string();
    loop {
        budget.tick(slack_name.len().saturating_add(1))?;
        if !names.contains(slack_name.as_str()) {
            break;
        }
        slack_name.push('_');
    }
    net.places.push(slack_name);
    net.initial.push(candidate.slack);
    for (t, &increase) in p.transitions.iter().zip(&candidate.increases) {
        budget.tick(t.name.len().saturating_add(1))?;
        let mut augmented = Transition {
            name: t.name.clone(),
            pre: vec![],
            post: vec![],
        };
        for (arcs, out) in [(&t.pre, &mut augmented.pre), (&t.post, &mut augmented.post)] {
            for &arc in arcs {
                budget.tick(1)?;
                out.push(arc);
            }
        }
        if increase > 0 {
            budget.tick(1)?;
            augmented.pre.push((n, increase));
        }
        net.transitions.push(augmented);
    }
    for c in &p.target {
        budget.tick(1)?;
        let mut coefficients = Vec::new();
        for &a in &c.coefficients {
            budget.tick(1)?;
            coefficients.push(a);
        }
        coefficients.push(0);
        net.target.push(Constraint {
            coefficients,
            bound: c.bound,
            equality: c.equality,
        });
    }
    budget.tick(0)?;
    Ok(Prepared {
        problem: net,
        bound: candidate.bound,
        slack: candidate.slack,
    })
}

pub fn prepare(p: &Problem, deadline: Instant, max_work: usize) -> Result<Option<Preparation>> {
    let mut budget = Budget {
        deadline,
        remaining: max_work,
    };
    match infer(p, &mut budget)? {
        None => Ok(None),
        Some(Inference::Infeasible) => Ok(Some(Preparation::Infeasible)),
        Some(Inference::Useful(candidate)) => Ok(Some(Preparation::Reduced(augment(
            p,
            candidate,
            &mut budget,
        )?))),
    }
}

fn fields(proof: &Value, kind: &str, keys: &[&str], budget: &mut Budget) -> Result<()> {
    budget.tick(1)?;
    let object = proof
        .as_object()
        .context("potential proof is not an object")?;
    ensure!(
        object.len() == keys.len() && keys.iter().all(|key| object.contains_key(*key)),
        "invalid potential proof fields"
    );
    ensure!(proof["kind"] == kind, "wrong potential proof kind");
    Ok(())
}

/// Reconstruct the net; the caller must independently validate its inner proof.
pub fn verify_reduction<'a>(
    p: &Problem,
    proof: &'a Value,
    deadline: Instant,
    max_work: usize,
) -> Result<(Prepared, &'a Value)> {
    let mut budget = Budget {
        deadline,
        remaining: max_work,
    };
    fields(
        proof,
        "target-path-potential-v1",
        &["kind", "inner"],
        &mut budget,
    )?;
    let inner = proof
        .get("inner")
        .filter(|v| v.is_object())
        .context("inner proof is not an object")?;
    let Some(Inference::Useful(candidate)) = infer(p, &mut budget)? else {
        anyhow::bail!("no usable target-path potential");
    };
    Ok((augment(p, candidate, &mut budget)?, inner))
}

pub fn verify_infeasible(
    p: &Problem,
    proof: &Value,
    deadline: Instant,
    max_work: usize,
) -> Result<()> {
    let mut budget = Budget {
        deadline,
        remaining: max_work,
    };
    fields(
        proof,
        "target-path-potential-infeasible-v1",
        &["kind"],
        &mut budget,
    )?;
    ensure!(
        matches!(infer(p, &mut budget)?, Some(Inference::Infeasible)),
        "initial mass does not contradict a checked target-path bound"
    );
    budget.tick(0)
}

impl Prepared {
    pub fn wrap_proof(&self, inner: Value, deadline: Instant, max_work: usize) -> Result<Value> {
        let mut budget = Budget {
            deadline,
            remaining: max_work,
        };
        budget.tick(1)?;
        ensure!(inner.is_object(), "inner proof is not an object");
        let mut object = Map::new();
        object.insert("kind".into(), Value::from("target-path-potential-v1"));
        object.insert("inner".into(), inner);
        budget.tick(0)?;
        Ok(Value::Object(object))
    }

    pub fn lift_witness(
        &self,
        original: &Problem,
        trace: &[usize],
        deadline: Instant,
        max_work: usize,
    ) -> Result<(Vec<usize>, Vec<u64>)> {
        let mut budget = Budget {
            deadline,
            remaining: max_work,
        };
        ensure!(
            matches!(infer(original, &mut budget)?, Some(Inference::Useful(_))),
            "no usable target-path potential"
        );
        budget.tick(original.initial.len().saturating_add(trace.len()))?;
        let mut marking = original.initial.clone();
        let mut lifted = Vec::with_capacity(trace.len());
        for &id in trace {
            budget.tick(1)?;
            let t = original
                .transitions
                .get(id)
                .context("invalid witness transition")?;
            for &(place, weight) in &t.pre {
                budget.tick(1)?;
                ensure!(marking[place] >= weight, "lifted witness disabled");
            }
            for &(place, weight) in &t.pre {
                budget.tick(1)?;
                marking[place] -= weight;
            }
            for &(place, weight) in &t.post {
                budget.tick(1)?;
                marking[place] = marking[place]
                    .checked_add(weight)
                    .context("lifted counter overflow")?;
            }
            lifted.push(id);
        }
        for c in &original.target {
            budget.tick(1)?;
            let mut value = 0i128;
            for (&a, &tokens) in c.coefficients.iter().zip(&marking) {
                budget.tick(1)?;
                value = value
                    .checked_add(i128::from(a) * i128::from(tokens))
                    .context("lifted target overflow")?;
            }
            ensure!(
                if c.equality {
                    value == i128::from(c.bound)
                } else {
                    value >= i128::from(c.bound)
                },
                "lifted witness misses target"
            );
        }
        budget.tick(0)?;
        Ok((lifted, marking))
    }
}
