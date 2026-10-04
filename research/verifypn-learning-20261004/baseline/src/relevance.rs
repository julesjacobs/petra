//! Checked backward relevance for ordinary Petri-net reachability.
//!
//! Omitted transitions have nonpositive incidence on retained places and zero
//! incidence on target support. Removing them from a firing sequence therefore
//! preserves target values and cannot disable a retained transition.
use crate::model::{Constraint, Problem, Transition};
use anyhow::{Context, Result, ensure};
use serde_json::{Map, Value};
use std::{collections::HashMap, time::Instant};

#[derive(Debug)]
pub struct Prepared {
    pub problem: Problem,
    pub places: Vec<usize>,
    pub transitions: Vec<usize>,
}

struct Budget {
    deadline: Instant,
    remaining: usize,
}
impl Budget {
    fn tick(&mut self, work: usize) -> Result<()> {
        ensure!(Instant::now() < self.deadline, "relevance time limit");
        self.remaining = self
            .remaining
            .checked_sub(work)
            .context("relevance work limit")?;
        Ok(())
    }
}

fn validate(p: &Problem, budget: &mut Budget) -> Result<Vec<bool>> {
    budget.tick(p.places.len().saturating_add(1))?;
    ensure!(
        p.initial.len() == p.places.len(),
        "initial marking dimension mismatch"
    );
    let mut support = vec![false; p.places.len()];
    for c in &p.target {
        budget.tick(1)?;
        ensure!(
            c.coefficients.len() == p.places.len(),
            "constraint dimension mismatch"
        );
        for (place, &a) in c.coefficients.iter().enumerate() {
            budget.tick(1)?;
            support[place] |= a != 0;
        }
    }
    let mut seen = vec![0usize; p.places.len()];
    let mut generation = 0usize;
    for t in &p.transitions {
        budget.tick(1)?;
        for arcs in [&t.pre, &t.post] {
            generation = generation.checked_add(1).context("too many arc lists")?;
            for &(place, weight) in arcs {
                budget.tick(1)?;
                ensure!(place < p.places.len() && weight > 0, "invalid arc");
                ensure!(seen[place] != generation, "repeated arc");
                seen[place] = generation;
            }
        }
    }
    Ok(support)
}

fn incidence(t: &Transition, budget: &mut Budget) -> Result<HashMap<usize, i128>> {
    let mut delta = HashMap::new();
    for &(place, weight) in &t.pre {
        budget.tick(1)?;
        delta.insert(place, -i128::from(weight));
    }
    for &(place, weight) in &t.post {
        budget.tick(1)?;
        *delta.entry(place).or_default() += i128::from(weight);
    }
    Ok(delta)
}

pub fn prepare(p: &Problem, deadline: Instant, max_work: usize) -> Result<Prepared> {
    let mut budget = Budget {
        deadline,
        remaining: max_work,
    };
    let support = validate(p, &mut budget)?;
    budget.tick(p.places.len().saturating_add(p.transitions.len()))?;
    let mut producers = vec![Vec::new(); p.places.len()];
    let mut kept_places = support.clone();
    let mut kept_transitions = vec![false; p.transitions.len()];
    let mut pending = Vec::new();
    for (id, t) in p.transitions.iter().enumerate() {
        budget.tick(1)?;
        for (place, delta) in incidence(t, &mut budget)? {
            budget.tick(1)?;
            if delta > 0 {
                producers[place].push(id);
            }
            if delta != 0 && support[place] && !kept_transitions[id] {
                kept_transitions[id] = true;
                pending.push(id);
            }
        }
    }
    // Target places are already marked, but their producers were seeded above.
    while let Some(t) = pending.pop() {
        budget.tick(1)?;
        for &(place, _) in &p.transitions[t].pre {
            budget.tick(1)?;
            if !std::mem::replace(&mut kept_places[place], true) {
                for &producer in &producers[place] {
                    budget.tick(1)?;
                    if !std::mem::replace(&mut kept_transitions[producer], true) {
                        pending.push(producer);
                    }
                }
            }
        }
    }
    let mut places = Vec::new();
    let mut transitions = Vec::new();
    for (i, kept) in kept_places.into_iter().enumerate() {
        budget.tick(1)?;
        if kept {
            places.push(i);
        }
    }
    for (i, kept) in kept_transitions.into_iter().enumerate() {
        budget.tick(1)?;
        if kept {
            transitions.push(i);
        }
    }
    checked(p, places, transitions, &support, &mut budget)
}

fn checked(
    p: &Problem,
    places: Vec<usize>,
    transitions: Vec<usize>,
    support: &[bool],
    budget: &mut Budget,
) -> Result<Prepared> {
    budget.tick(p.places.len().saturating_add(p.transitions.len()))?;
    let mut place_map = vec![None; p.places.len()];
    let mut retained = vec![false; p.transitions.len()];
    let mut previous = None;
    for (i, &place) in places.iter().enumerate() {
        budget.tick(1)?;
        ensure!(
            place < p.places.len() && previous.is_none_or(|old| old < place),
            "invalid relevance places"
        );
        place_map[place] = Some(i);
        previous = Some(place);
    }
    previous = None;
    for &t in &transitions {
        budget.tick(1)?;
        ensure!(
            t < p.transitions.len() && previous.is_none_or(|old| old < t),
            "invalid relevance transitions"
        );
        retained[t] = true;
        previous = Some(t);
    }
    for (place, &needed) in support.iter().enumerate() {
        budget.tick(1)?;
        ensure!(
            !needed || place_map[place].is_some(),
            "relevance omits target place"
        );
    }
    for (id, t) in p.transitions.iter().enumerate() {
        budget.tick(1)?;
        if retained[id] {
            for &(place, _) in &t.pre {
                budget.tick(1)?;
                ensure!(
                    place_map[place].is_some(),
                    "relevance omits retained input place"
                );
            }
        } else {
            for (place, delta) in incidence(t, budget)? {
                budget.tick(1)?;
                ensure!(
                    !support[place] || delta == 0,
                    "omitted transition changes target support"
                );
                ensure!(
                    place_map[place].is_none() || delta <= 0,
                    "omitted transition produces retained tokens"
                );
            }
        }
    }
    let mut net = Problem {
        places: Vec::new(),
        initial: Vec::new(),
        transitions: Vec::new(),
        target: Vec::new(),
    };
    for &place in &places {
        budget.tick(p.places[place].len().saturating_add(1))?;
        net.places.push(p.places[place].clone());
        net.initial.push(p.initial[place]);
    }
    for &id in &transitions {
        let original = &p.transitions[id];
        budget.tick(original.name.len().saturating_add(1))?;
        let mut t = Transition {
            name: original.name.clone(),
            pre: Vec::new(),
            post: Vec::new(),
        };
        for (arcs, projected) in [(&original.pre, &mut t.pre), (&original.post, &mut t.post)] {
            for &(place, weight) in arcs {
                budget.tick(1)?;
                if let Some(mapped) = place_map[place] {
                    projected.push((mapped, weight));
                }
            }
        }
        net.transitions.push(t);
    }
    for c in &p.target {
        budget.tick(1)?;
        let mut coefficients = Vec::with_capacity(places.len());
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
    })
}

fn mapping(value: &Value, bound: usize, budget: &mut Budget) -> Result<Vec<usize>> {
    let values = value
        .as_array()
        .context("relevance mapping is not an array")?;
    budget.tick(values.len())?;
    ensure!(values.len() <= bound, "relevance mapping too long");
    let mut ids = Vec::with_capacity(values.len());
    for value in values {
        budget.tick(1)?;
        ids.push(usize::try_from(
            value.as_u64().context("invalid relevance index")?,
        )?);
    }
    Ok(ids)
}

/// Check the reduction only. The caller must verify `inner` on the returned net.
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
    budget.tick(1)?;
    ensure!(
        proof["kind"] == "relevance-v1",
        "wrong relevance proof kind"
    );
    ensure!(
        proof.as_object().is_some_and(|fields| fields.len() == 4),
        "invalid relevance proof fields"
    );
    let support = validate(p, &mut budget)?;
    let places = mapping(&proof["places"], p.places.len(), &mut budget)?;
    let transitions = mapping(&proof["transitions"], p.transitions.len(), &mut budget)?;
    let inner = proof
        .get("inner")
        .context("missing relevance inner proof")?;
    let prepared = checked(p, places, transitions, &support, &mut budget)?;
    Ok((prepared, inner))
}

impl Prepared {
    pub fn wrap_proof(&self, inner: Value, deadline: Instant, max_work: usize) -> Result<Value> {
        let mut budget = Budget {
            deadline,
            remaining: max_work,
        };
        budget.tick(1)?;
        let mut fields = Map::new();
        for (name, ids) in [("places", &self.places), ("transitions", &self.transitions)] {
            budget.tick(ids.len())?;
            let mut values = Vec::with_capacity(ids.len());
            for &id in ids {
                budget.tick(1)?;
                values.push(Value::from(id));
            }
            fields.insert(name.into(), Value::Array(values));
        }
        fields.insert("kind".into(), Value::from("relevance-v1"));
        fields.insert("inner".into(), inner);
        let proof = Value::Object(fields);
        budget.tick(0)?;
        Ok(proof)
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
                .context("invalid original transition")?;
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
