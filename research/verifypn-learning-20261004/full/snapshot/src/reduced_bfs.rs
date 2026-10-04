//! Bounded composition of checked reductions and explicit reachability search.
use crate::{
    buffer_agglomeration,
    model::Problem,
    relevance,
    search::{self, Outcome},
};
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::time::{Duration, Instant};

pub const MAX_CLOSURE_STATES: usize = 200_000;
const WORK: usize = 20_000_000;
const ROUNDS: usize = 4;

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Closure {
    kind: String,
    states: usize,
}

pub fn verify_closure(p: &Problem, proof: &Value, deadline: Instant) -> Result<()> {
    let proof: Closure = serde_json::from_value(proof.clone())?;
    ensure!(proof.kind == "finite-closure-v1", "invalid closure kind");
    ensure!(
        (1..=MAX_CLOSURE_STATES).contains(&proof.states),
        "invalid closure bound"
    );
    p.validate()?;
    let result = search::solve(
        p,
        false,
        deadline.saturating_duration_since(Instant::now()),
        proof.states,
    );
    ensure!(
        result.verdict == "unreachable" && result.states == proof.states,
        "finite closure was not verified"
    );
    Ok(())
}

enum Reduction {
    Buffer(Problem, buffer_agglomeration::Prepared),
    Relevance(Problem, relevance::Prepared),
}

impl Reduction {
    fn lift(&self, out: &mut Outcome, deadline: Instant) -> Result<()> {
        if out.verdict == "reachable" {
            let (trace, marking) = match self {
                Self::Buffer(original, prepared) => {
                    prepared.lift_witness(original, &out.trace, deadline, WORK)?
                }
                Self::Relevance(original, prepared) => {
                    prepared.lift_witness(original, &out.trace, deadline, WORK)?
                }
            };
            out.trace = trace;
            out.marking = Some(marking);
        } else {
            let inner = out.proof.take().context("missing closure proof")?;
            out.proof = Some(match self {
                Self::Buffer(_, prepared) => prepared.wrap_proof(inner, deadline, WORK)?,
                Self::Relevance(_, prepared) => prepared.wrap_proof(inner, deadline, WORK)?,
            });
        }
        Ok(())
    }
}

pub fn solve(p: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    let start = Instant::now();
    let deadline = start + timeout;
    let unknown = |reason: &str, states| Outcome::unknown("reduced-bfs", reason, states);
    if p.validate().is_err() || timeout.is_zero() || max_states == 0 {
        return unknown("invalid net or exhausted budget", 0);
    }
    let preparation_deadline = start + (timeout / 5).min(Duration::from_millis(200));
    let mut current = p.clone();
    let mut reductions = Vec::new();
    for _ in 0..ROUNDS {
        let before = reductions.len();
        if let Ok(Some(prepared)) =
            buffer_agglomeration::prepare(&current, preparation_deadline, WORK)
        {
            let next = prepared.problem.clone();
            reductions.push(Reduction::Buffer(current, prepared));
            current = next;
        }
        if let Ok(prepared) = relevance::prepare(&current, preparation_deadline, WORK)
            && (prepared.places.len() != current.places.len()
                || prepared.transitions.len() != current.transitions.len())
        {
            let next = prepared.problem.clone();
            reductions.push(Reduction::Relevance(current, prepared));
            current = next;
        }
        if reductions.len() == before || Instant::now() >= preparation_deadline {
            break;
        }
    }
    // Reserve time for witness lifting and proof serialization.
    let search_budget = deadline.saturating_duration_since(Instant::now()) * 9 / 10;
    let mut out = search::solve(
        &current,
        false,
        search_budget,
        max_states.min(MAX_CLOSURE_STATES),
    );
    if out.verdict == "unknown" {
        return unknown(&out.reason, out.states);
    }
    if out.verdict == "unreachable" {
        out.proof = Some(json!({"kind":"finite-closure-v1", "states":out.states}));
    }
    for reduction in reductions.iter().rev() {
        if let Err(error) = reduction.lift(&mut out, deadline) {
            return unknown(&error.to_string(), out.states);
        }
    }
    if Instant::now() >= deadline {
        return unknown("reduction lifting deadline", out.states);
    }
    out.method = "reduced-bfs".into();
    out
}
