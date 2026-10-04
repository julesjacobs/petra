//! Remove traps that the target requires empty, preserving every successful trace.
use crate::model::{Constraint, Problem, Transition};
use anyhow::{Context, Result, ensure};
use serde_json::{Map, Value};
use std::time::Instant;

#[derive(Debug)]
pub enum Preparation {
    Marked { trap: Vec<usize> },
    Reduced(Prepared),
}

#[derive(Debug)]
pub struct Prepared {
    pub problem: Problem,
    pub places: Vec<usize>,
    pub transitions: Vec<usize>,
    pub trap: Vec<usize>,
}

struct Budget {
    deadline: Instant,
    remaining: usize,
}
impl Budget {
    fn tick(&mut self, work: usize) -> Result<()> {
        ensure!(Instant::now() < self.deadline, "target-zero trap deadline");
        self.remaining = self
            .remaining
            .checked_sub(work)
            .context("target-zero trap work limit")?;
        Ok(())
    }
}

fn validate(p: &Problem, budget: &mut Budget) -> Result<Vec<bool>> {
    let n = p.places.len();
    budget.tick(n.saturating_add(1))?;
    ensure!(p.initial.len() == n, "initial marking dimension mismatch");
    let mut zero = vec![false; n];
    for c in &p.target {
        budget.tick(1)?;
        ensure!(c.coefficients.len() == n, "constraint dimension mismatch");
        let (mut positive, mut negative) = (false, false);
        for &a in &c.coefficients {
            budget.tick(1)?;
            positive |= a > 0;
            negative |= a < 0;
        }
        if c.bound == 0 && ((!positive) || (c.equality && !negative)) {
            for (i, &a) in c.coefficients.iter().enumerate() {
                budget.tick(1)?;
                zero[i] |= a != 0;
            }
        }
    }
    budget.tick(n)?;
    let mut seen = vec![0usize; n];
    let mut generation = 0usize;
    for t in &p.transitions {
        budget.tick(1)?;
        for arcs in [&t.pre, &t.post] {
            generation = generation.checked_add(1).context("too many arc lists")?;
            for &(place, weight) in arcs {
                budget.tick(1)?;
                ensure!(place < n && weight > 0, "invalid arc");
                ensure!(seen[place] != generation, "repeated arc");
                seen[place] = generation;
            }
        }
    }
    Ok(zero)
}

fn checked_trap(
    p: &Problem,
    trap: &[usize],
    zero: &[bool],
    budget: &mut Budget,
) -> Result<(Vec<bool>, bool)> {
    budget.tick(p.places.len().saturating_add(trap.len()))?;
    let mut included = vec![false; p.places.len()];
    let mut previous = None;
    let mut marked = false;
    for &place in trap {
        budget.tick(1)?;
        ensure!(
            place < included.len() && previous.is_none_or(|old| old < place),
            "invalid trap indices"
        );
        ensure!(zero[place], "target does not force trap place to zero");
        previous = Some(place);
        included[place] = true;
        marked |= p.initial[place] > 0;
    }
    for t in &p.transitions {
        budget.tick(1)?;
        let (mut consumes, mut produces) = (false, false);
        for &(place, _) in &t.pre {
            budget.tick(1)?;
            consumes |= included[place];
        }
        for &(place, _) in &t.post {
            budget.tick(1)?;
            produces |= included[place];
        }
        ensure!(!consumes || produces, "transition can empty proposed trap");
    }
    Ok((included, marked))
}

fn project(
    p: &Problem,
    trap: Vec<usize>,
    included: &[bool],
    budget: &mut Budget,
) -> Result<Prepared> {
    budget.tick(p.places.len())?;
    let mut mapping = vec![None; p.places.len()];
    let mut places = Vec::new();
    let mut net = Problem {
        places: vec![],
        initial: vec![],
        transitions: vec![],
        target: vec![],
    };
    for (place, &removed) in included.iter().enumerate() {
        budget.tick(1)?;
        if !removed {
            budget.tick(p.places[place].len().saturating_add(1))?;
            mapping[place] = Some(places.len());
            places.push(place);
            net.places.push(p.places[place].clone());
            net.initial.push(p.initial[place]);
        }
    }
    let mut transitions = Vec::new();
    for (id, t) in p.transitions.iter().enumerate() {
        budget.tick(1)?;
        let mut removed = false;
        for &(place, _) in &t.post {
            budget.tick(1)?;
            removed |= included[place];
        }
        if removed {
            continue;
        }
        budget.tick(t.name.len().saturating_add(1))?;
        let mut projected = Transition {
            name: t.name.clone(),
            pre: vec![],
            post: vec![],
        };
        for (original, arcs) in [(&t.pre, &mut projected.pre), (&t.post, &mut projected.post)] {
            for &(place, weight) in original {
                budget.tick(1)?;
                arcs.push((
                    mapping[place].context("retained transition touches trap")?,
                    weight,
                ));
            }
        }
        transitions.push(id);
        net.transitions.push(projected);
    }
    for c in &p.target {
        budget.tick(1)?;
        let mut coefficients = Vec::new();
        for &place in &places {
            budget.tick(1)?;
            coefficients.push(c.coefficients[place]);
        }
        net.target.push(Constraint {
            coefficients,
            bound: c.bound,
            equality: c.equality,
        });
    }
    budget.tick(0)?;
    Ok(Prepared {
        problem: net,
        places,
        transitions,
        trap,
    })
}

pub fn prepare(p: &Problem, deadline: Instant, max_work: usize) -> Result<Preparation> {
    let mut budget = Budget {
        deadline,
        remaining: max_work,
    };
    let zero = validate(p, &mut budget)?;
    budget.tick(
        p.places
            .len()
            .saturating_mul(2)
            .saturating_add(p.transitions.len()),
    )?;
    let mut included = zero.clone();
    let mut producers = vec![Vec::new(); p.places.len()];
    let mut remaining_post = vec![0usize; p.transitions.len()];
    let mut pending = Vec::new();
    for (id, t) in p.transitions.iter().enumerate() {
        budget.tick(1)?;
        for &(place, _) in &t.post {
            budget.tick(1)?;
            if included[place] {
                remaining_post[id] += 1;
                producers[place].push(id);
            }
        }
        if remaining_post[id] == 0 {
            pending.push(id);
        }
    }
    while let Some(id) = pending.pop() {
        budget.tick(1)?;
        for &(place, _) in &p.transitions[id].pre {
            budget.tick(1)?;
            if !std::mem::replace(&mut included[place], false) {
                continue;
            }
            for &producer in &producers[place] {
                budget.tick(1)?;
                remaining_post[producer] -= 1;
                if remaining_post[producer] == 0 {
                    pending.push(producer);
                }
            }
        }
    }
    let mut trap = Vec::new();
    for (place, &keep) in included.iter().enumerate() {
        budget.tick(1)?;
        if keep {
            trap.push(place);
        }
    }
    let (included, marked) = checked_trap(p, &trap, &zero, &mut budget)?;
    if marked {
        budget.tick(0)?;
        Ok(Preparation::Marked { trap })
    } else {
        Ok(Preparation::Reduced(project(
            p,
            trap,
            &included,
            &mut budget,
        )?))
    }
}

fn proof_trap(
    proof: &Value,
    kind: &str,
    fields: &[&str],
    bound: usize,
    budget: &mut Budget,
) -> Result<Vec<usize>> {
    budget.tick(1)?;
    let object = proof.as_object().context("trap proof is not an object")?;
    ensure!(
        object.len() == fields.len() && fields.iter().all(|key| object.contains_key(*key)),
        "invalid trap proof fields"
    );
    ensure!(proof["kind"] == kind, "wrong trap proof kind");
    let values = proof["trap"].as_array().context("trap is not an array")?;
    ensure!(values.len() <= bound, "trap too long");
    budget.tick(values.len())?;
    let mut trap = Vec::with_capacity(values.len());
    for value in values {
        budget.tick(1)?;
        trap.push(usize::try_from(
            value.as_u64().context("invalid trap index")?,
        )?);
    }
    Ok(trap)
}

/// The caller must independently check the returned inner proof on the projected net.
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
    let zero = validate(p, &mut budget)?;
    let trap = proof_trap(
        proof,
        "target-zero-trap-v1",
        &["kind", "trap", "inner"],
        p.places.len(),
        &mut budget,
    )?;
    let inner = proof
        .get("inner")
        .filter(|value| value.is_object())
        .context("inner proof is not an object")?;
    let (included, marked) = checked_trap(p, &trap, &zero, &mut budget)?;
    ensure!(!marked, "reduction trap is initially marked");
    Ok((project(p, trap, &included, &mut budget)?, inner))
}

pub fn verify_marked(p: &Problem, proof: &Value, deadline: Instant, max_work: usize) -> Result<()> {
    let mut budget = Budget {
        deadline,
        remaining: max_work,
    };
    let zero = validate(p, &mut budget)?;
    let trap = proof_trap(
        proof,
        "target-zero-trap-marked-v1",
        &["kind", "trap"],
        p.places.len(),
        &mut budget,
    )?;
    let (_, marked) = checked_trap(p, &trap, &zero, &mut budget)?;
    ensure!(marked, "marked-trap proof is initially empty");
    budget.tick(0)
}

impl Prepared {
    pub fn wrap_proof(&self, inner: Value, deadline: Instant, max_work: usize) -> Result<Value> {
        let mut budget = Budget {
            deadline,
            remaining: max_work,
        };
        budget.tick(self.trap.len().saturating_add(1))?;
        ensure!(inner.is_object(), "inner proof is not an object");
        let mut values = Vec::with_capacity(self.trap.len());
        let mut previous = None;
        for &place in &self.trap {
            budget.tick(1)?;
            ensure!(
                previous.is_none_or(|old| old < place),
                "invalid trap indices"
            );
            previous = Some(place);
            values.push(Value::from(place));
        }
        let mut object = Map::new();
        object.insert("kind".into(), Value::from("target-zero-trap-v1"));
        object.insert("trap".into(), Value::Array(values));
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
        validate(original, &mut budget)?;
        budget.tick(original.initial.len().saturating_add(trace.len()))?;
        let mut marking = original.initial.clone();
        let mut lifted = Vec::with_capacity(trace.len());
        for &reduced in trace {
            budget.tick(1)?;
            let id = *self
                .transitions
                .get(reduced)
                .context("invalid reduced witness transition")?;
            let t = original
                .transitions
                .get(id)
                .context("invalid original witness transition")?;
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
            for (&coefficient, &tokens) in c.coefficients.iter().zip(&marking) {
                budget.tick(1)?;
                value = value
                    .checked_add(i128::from(coefficient) * i128::from(tokens))
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
