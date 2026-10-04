//! Property-directed place projections, checked by finite abstract closures.
use crate::{
    cegar,
    model::{Constraint, Problem, Transition},
    search::Outcome,
};
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use std::{
    collections::{BTreeSet, HashSet},
    time::{Duration, Instant},
};

pub fn project(p: &Problem, selected: &[usize]) -> Result<Problem> {
    ensure!(
        selected.iter().all(|&i| i < p.places.len()) && selected.windows(2).all(|w| w[0] < w[1]),
        "invalid projection"
    );
    let mut ids = vec![None; p.places.len()];
    for (i, &j) in selected.iter().enumerate() {
        ids[j] = Some(i);
    }
    ensure!(
        p.target.iter().all(|c| c
            .coefficients
            .iter()
            .enumerate()
            .all(|(i, &a)| a == 0 || ids[i].is_some())),
        "projection omits target coordinate"
    );
    let mut transitions = vec![];
    let mut seen = HashSet::new();
    for t in &p.transitions {
        let arcs = |a: &[(usize, u64)]| {
            let mut out: Vec<_> = a
                .iter()
                .filter_map(|&(i, w)| ids[i].map(|j| (j, w)))
                .collect();
            out.sort_unstable();
            out
        };
        let pre = arcs(&t.pre);
        let post = arcs(&t.post);
        if pre == post || !seen.insert((pre.clone(), post.clone())) {
            continue;
        }
        transitions.push(Transition {
            name: format!("p{}", transitions.len()),
            pre,
            post,
        });
    }
    Ok(Problem {
        places: selected.iter().map(|&i| p.places[i].clone()).collect(),
        initial: selected.iter().map(|&i| p.initial[i]).collect(),
        transitions,
        target: p
            .target
            .iter()
            .map(|c| Constraint {
                coefficients: selected.iter().map(|&i| c.coefficients[i]).collect(),
                bound: c.bound,
                equality: c.equality,
            })
            .collect(),
    })
}

pub fn verify_certificate(p: &Problem, proof: &Value) -> Result<()> {
    p.validate()?;
    ensure!(proof["kind"] == "projected-closure-v1", "wrong proof kind");
    let selected: Vec<usize> = serde_json::from_value(proof["places"].clone())?;
    let inner = proof.get("closure").context("missing closure")?;
    cegar::verify_certificate(&project(p, &selected)?, inner)
}

fn lift(p: &Problem, q: &Problem, selected: &[usize], trace: &[usize]) -> Option<Vec<usize>> {
    let mut ids = vec![None; p.places.len()];
    for (i, &j) in selected.iter().enumerate() {
        ids[j] = Some(i);
    }
    let mut candidates = vec![vec![]; q.transitions.len()];
    for (original, t) in p.transitions.iter().enumerate() {
        let arcs = |a: &[(usize, u64)]| {
            let mut v: Vec<_> = a
                .iter()
                .filter_map(|&(i, w)| ids[i].map(|j| (j, w)))
                .collect();
            v.sort_unstable();
            v
        };
        let pre = arcs(&t.pre);
        let post = arcs(&t.post);
        if let Some(i) = q
            .transitions
            .iter()
            .position(|t| t.pre == pre && t.post == post)
        {
            candidates[i].push(original);
        }
    }
    let mut marking = p.initial.clone();
    let mut lifted = vec![];
    for &t in trace {
        let (original, next) = candidates[t]
            .iter()
            .find_map(|&i| p.fire(&marking, i).ok().flatten().map(|m| (i, m)))?;
        marking = next;
        lifted.push(original);
    }
    p.check_witness(&lifted).ok()?;
    Some(lifted)
}

pub fn solve(p: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    let start = Instant::now();
    let mut selected: BTreeSet<_> = p
        .target
        .iter()
        .flat_map(|c| {
            c.coefficients
                .iter()
                .enumerate()
                .filter(|(_, v)| **v != 0)
                .map(|(i, _)| i)
        })
        .collect();
    for round in 0..3 {
        if selected.len() > 24 {
            break;
        }
        let places: Vec<_> = selected.iter().copied().collect();
        let Ok(q) = project(p, &places) else {
            break;
        };
        let remaining = timeout.saturating_sub(start.elapsed());
        let out = cegar::solve(&q, remaining / (3 - round), max_states.min(20_000));
        if out.verdict == "reachable"
            && let Some(trace) = lift(p, &q, &places, &out.trace)
            && let Ok(marking) = p.check_witness(&trace)
        {
            return Outcome {
                verdict: "reachable",
                method: "projected-cegar".into(),
                reason: "projected witness lifted and replayed on original net".into(),
                states: out.states,
                trace,
                marking: Some(marking),
                certificate: None,
                proof: None,
            };
        }
        if out.verdict == "unreachable" {
            let proof = json!({"kind":"projected-closure-v1","places":places,"closure":out.proof});
            if verify_certificate(p, &proof).is_ok() {
                let mut result = Outcome::unknown(
                    "projected-cegar",
                    "checked projected abstract closure",
                    out.states,
                );
                result.verdict = "unreachable";
                result.proof = Some(proof);
                return result;
            }
        }
        let old = selected.clone();
        for t in &p.transitions {
            let affects = old.iter().any(|&i| {
                let weight = |arcs: &[(usize, u64)]| {
                    arcs.iter().find(|&&(j, _)| j == i).map_or(0, |&(_, w)| w)
                };
                weight(&t.pre) != weight(&t.post)
            });
            if affects {
                selected.extend(t.pre.iter().map(|&(i, _)| i));
            }
        }
        if selected == old || start.elapsed() >= timeout {
            break;
        }
    }
    Outcome::unknown("projected-cegar", "projection search inconclusive", 0)
}
