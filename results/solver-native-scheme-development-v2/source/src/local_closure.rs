//! Negative proofs from necessary local targets and checked abstract closures.
//!
//! Dropping nonpositive terms from a >= row weakens it on nonnegative markings.
//! Projected executions drop foreign guards and therefore overapproximate the
//! original executions. A closed projected set excluding the weakened target
//! proves original unreachability; projected positive answers prove nothing.
use crate::{cegar, model::Problem, projection, search::Outcome};
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use std::{
    collections::BTreeMap,
    time::{Duration, Instant},
};

pub fn necessary_projection(p: &Problem, places: &[usize]) -> Result<Problem> {
    p.validate()?;
    ensure!(
        places.iter().all(|&i| i < p.places.len()) && places.windows(2).all(|w| w[0] < w[1]),
        "invalid local projection"
    );
    let mut selected = vec![false; p.places.len()];
    for &place in places {
        selected[place] = true;
    }
    let mut weakened = p.clone();
    weakened.target.clear();
    for original in &p.target {
        let mut directions = vec![original.clone()];
        if original.equality
            && let Some(bound) = original.bound.checked_neg()
            && let Some(coefficients) = original
                .coefficients
                .iter()
                .map(|a| a.checked_neg())
                .collect::<Option<Vec<_>>>()
        {
            let mut opposite = original.clone();
            opposite.coefficients = coefficients;
            opposite.bound = bound;
            directions.push(opposite);
        }
        for mut row in directions {
            row.equality = false;
            if row
                .coefficients
                .iter()
                .zip(&selected)
                .any(|(&a, &keep)| !keep && a > 0)
            {
                continue;
            }
            for (a, &keep) in row.coefficients.iter_mut().zip(&selected) {
                if !keep {
                    *a = 0;
                }
            }
            weakened.target.push(row);
        }
    }
    projection::project(&weakened, places)
}

pub fn verify_certificate(p: &Problem, proof: &Value) -> Result<()> {
    ensure!(proof["kind"] == "local-closure-v1", "wrong proof kind");
    let places: Vec<usize> = serde_json::from_value(proof["places"].clone())?;
    let closure = proof.get("closure").context("missing local closure")?;
    cegar::verify_certificate(&necessary_projection(p, &places)?, closure)
}

fn components(p: &Problem) -> Vec<Vec<usize>> {
    fn root(parent: &mut [usize], mut i: usize) -> usize {
        while parent[i] != i {
            parent[i] = parent[parent[i]];
            i = parent[i];
        }
        i
    }
    let mut parent: Vec<_> = (0..p.places.len()).collect();
    for t in &p.transitions {
        let mut pre = t.pre.clone();
        let mut post = t.post.clone();
        pre.sort_unstable();
        post.sort_unstable();
        if pre == post {
            continue;
        }
        let mut places = pre.iter().chain(&post).map(|&(place, _)| place);
        if let Some(first) = places.next() {
            for place in places {
                let a = root(&mut parent, first);
                let b = root(&mut parent, place);
                parent[b] = a;
            }
        }
    }
    let mut groups = BTreeMap::<usize, Vec<usize>>::new();
    for place in 0..p.places.len() {
        groups
            .entry(root(&mut parent, place))
            .or_default()
            .push(place);
    }
    let mut groups: Vec<_> = groups.into_values().collect();
    groups.sort_by(|a, b| a.len().cmp(&b.len()).then_with(|| a.cmp(b)));
    groups
}

pub fn solve(p: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    let start = Instant::now();
    if let Err(error) = p.validate() {
        return Outcome::unknown("local-closure", &error.to_string(), 0);
    }
    let mut candidates = Vec::new();
    for places in components(p) {
        if start.elapsed() >= timeout {
            break;
        }
        if let Ok(local) = necessary_projection(p, &places)
            && local
                .target
                .iter()
                .any(|row| row.bound > 0 || row.coefficients.iter().any(|&a| a != 0))
        {
            candidates.push((places, local));
        }
    }
    let count = candidates.len();
    let mut states = 0usize;
    for (index, (places, local)) in candidates.into_iter().enumerate() {
        let remaining = timeout.saturating_sub(start.elapsed());
        if remaining.is_zero() {
            break;
        }
        let slice = remaining.div_f64((count - index) as f64);
        let out = cegar::solve(&local, slice, max_states);
        states = states.saturating_add(out.states);
        if out.verdict == "unreachable" {
            let proof = json!({"kind": "local-closure-v1", "places": places, "closure": out.proof});
            if verify_certificate(p, &proof).is_ok() {
                let mut result = Outcome::unknown(
                    "local-closure",
                    "checked necessary local target closure",
                    states,
                );
                result.verdict = "unreachable";
                result.proof = Some(proof);
                return result;
            }
        }
    }
    Outcome::unknown("local-closure", "local closures inconclusive", states)
}
