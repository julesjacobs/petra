//! Inductive unions of boxes, partitioned by exact bounded control coordinates.
use crate::{
    integer_equation,
    model::{Constraint, Problem},
    search::Outcome,
    state_equation,
};
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{
    collections::{HashMap, VecDeque},
    time::{Duration, Instant},
};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Region {
    pub lower: Vec<u64>,
    pub upper: Vec<Option<u64>>,
}

fn contains(outer: &Region, inner: &Region) -> bool {
    outer.lower.iter().zip(&inner.lower).all(|(a, b)| a <= b)
        && outer
            .upper
            .iter()
            .zip(&inner.upper)
            .all(|(a, b)| match (a, b) {
                (None, _) => true,
                (Some(a), Some(b)) => a >= b,
                _ => false,
            })
}

fn image(p: &Problem, b: &Region, t: usize) -> Result<Option<Region>> {
    let mut next = b.clone();
    for &(i, w) in &p.transitions[t].pre {
        if next.upper[i].is_some_and(|hi| hi < w) {
            return Ok(None);
        }
        next.lower[i] = next.lower[i].max(w) - w;
        next.upper[i] = next.upper[i].map(|hi| hi - w);
    }
    for &(i, w) in &p.transitions[t].post {
        next.lower[i] = next.lower[i]
            .checked_add(w)
            .context("interval lower overflow")?;
        next.upper[i] = next.upper[i].and_then(|hi| hi.checked_add(w));
    }
    Ok(Some(next))
}

fn key(b: &Region, controls: &[usize]) -> Vec<u64> {
    controls.iter().map(|&i| b.lower[i]).collect()
}

fn exact(marking: &[u64]) -> Region {
    Region {
        lower: marking.to_vec(),
        upper: marking.iter().copied().map(Some).collect(),
    }
}

fn controls(p: &Problem, deadline: Instant) -> Vec<usize> {
    let n = p.places.len();
    let mut bounded = vec![false; n];
    // Small nonnegative place sums are cheap candidates for finite control.
    if n <= 12 {
        for mask in 1usize..(1usize << n) {
            if Instant::now() >= deadline {
                break;
            }
            let initial: u128 = p
                .initial
                .iter()
                .enumerate()
                .filter(|(i, _)| mask & (1 << i) != 0)
                .map(|(_, x)| u128::from(*x))
                .sum();
            if initial > 2 {
                continue;
            }
            if p.transitions.iter().all(|t| {
                let weight = |arcs: &[(usize, u64)]| -> u128 {
                    arcs.iter()
                        .filter(|(i, _)| mask & (1 << i) != 0)
                        .map(|(_, w)| u128::from(*w))
                        .sum()
                };
                weight(&t.post) <= weight(&t.pre)
            }) {
                for (i, flag) in bounded.iter_mut().enumerate() {
                    *flag |= mask & (1 << i) != 0;
                }
            }
        }
    }
    let mut selected: Vec<_> = bounded
        .iter()
        .enumerate()
        .filter(|(_, b)| **b)
        .map(|(i, _)| i)
        .collect();
    selected.sort_by_key(|&i| (!p.target.iter().any(|c| c.coefficients[i] != 0), i));
    selected.truncate(6);
    selected.sort_unstable();
    selected
}

fn discover(
    p: &Problem,
    controls: &[usize],
    deadline: Instant,
    limit: usize,
) -> Result<Vec<Region>> {
    let mut boxes = vec![exact(&p.initial)];
    let mut ids = HashMap::from([(key(&boxes[0], controls), 0usize)]);
    let mut queue = VecDeque::from([0usize]);
    let mut increases = vec![vec![0u8; p.places.len()]];
    let mut decreases = vec![vec![0u8; p.places.len()]];
    let mut steps = 0;
    while let Some(id) = queue.pop_front() {
        let current = boxes[id].clone();
        for t in 0..p.transitions.len() {
            steps += 1;
            ensure!(
                Instant::now() < deadline && steps <= limit,
                "interval work limit"
            );
            let Some(next) = image(p, &current, t)? else {
                continue;
            };
            let k = key(&next, controls);
            if let Some(&j) = ids.get(&k) {
                let mut changed = false;
                for i in 0..p.places.len() {
                    if next.lower[i] < boxes[j].lower[i] {
                        decreases[j][i] = decreases[j][i].saturating_add(1);
                        boxes[j].lower[i] = if decreases[j][i] >= 2 {
                            0
                        } else {
                            next.lower[i]
                        };
                        changed = true;
                    }
                    if let Some(hi) = boxes[j].upper[i]
                        && next.upper[i].is_none_or(|v| v > hi)
                    {
                        increases[j][i] = increases[j][i].saturating_add(1);
                        boxes[j].upper[i] = if increases[j][i] >= 2 {
                            None
                        } else {
                            next.upper[i]
                        };
                        changed = true;
                    }
                }
                if changed {
                    queue.push_back(j);
                }
            } else {
                ensure!(boxes.len() < 256, "control partition limit");
                ids.insert(k, boxes.len());
                queue.push_back(boxes.len());
                boxes.push(next);
                increases.push(vec![0; p.places.len()]);
                decreases.push(vec![0; p.places.len()]);
            }
        }
    }
    Ok(boxes)
}

fn strengthen(p: &Problem, region: &Region) -> Result<Problem> {
    let mut q = p.clone();
    for i in 0..p.places.len() {
        let mut coefficients = vec![0; p.places.len()];
        coefficients[i] = 1;
        q.target.push(Constraint {
            coefficients: coefficients.clone(),
            bound: i64::try_from(region.lower[i])?,
            equality: false,
        });
        if let Some(hi) = region.upper[i] {
            coefficients[i] = -1;
            q.target.push(Constraint {
                coefficients,
                bound: -i64::try_from(hi)?,
                equality: false,
            });
        }
    }
    Ok(q)
}

pub fn verify_certificate(p: &Problem, proof: &Value) -> Result<()> {
    p.validate()?;
    ensure!(proof["kind"] == "interval-invariant-v1", "wrong proof kind");
    let controls: Vec<usize> = serde_json::from_value(proof["controls"].clone())?;
    let boxes: Vec<Region> = serde_json::from_value(proof["regions"].clone())?;
    let exclusions = proof["exclusions"]
        .as_array()
        .context("missing exclusions")?;
    ensure!(
        !boxes.is_empty() && exclusions.len() == boxes.len(),
        "invalid regions"
    );
    ensure!(
        controls.iter().all(|&i| i < p.places.len()) && controls.windows(2).all(|w| w[0] < w[1]),
        "invalid controls"
    );
    let mut ids = HashMap::new();
    for (j, b) in boxes.iter().enumerate() {
        ensure!(
            b.lower.len() == p.places.len() && b.upper.len() == p.places.len(),
            "invalid dimensions"
        );
        ensure!(
            b.lower
                .iter()
                .zip(&b.upper)
                .all(|(&lo, hi)| hi.is_none_or(|v| lo <= v)),
            "empty interval"
        );
        ensure!(
            controls.iter().all(|&i| b.upper[i] == Some(b.lower[i])),
            "inexact control"
        );
        ensure!(
            ids.insert(key(b, &controls), j).is_none(),
            "duplicate control region"
        );
    }
    let initial = exact(&p.initial);
    ensure!(
        ids.get(&key(&initial, &controls))
            .is_some_and(|&i| contains(&boxes[i], &initial)),
        "initial marking excluded"
    );
    for (b, exclusion) in boxes.iter().zip(exclusions) {
        for t in 0..p.transitions.len() {
            if let Some(next) = image(p, b, t)? {
                ensure!(
                    ids.get(&key(&next, &controls))
                        .is_some_and(|&i| contains(&boxes[i], &next)),
                    "invariant not inductive"
                );
            }
        }
        let q = strengthen(p, b)?;
        if exclusion["kind"] == "integer-cuts-v1" {
            integer_equation::verify_certificate(&q, exclusion)?;
        } else {
            ensure!(exclusion["kind"] == "farkas", "invalid exclusion kind");
            state_equation::verify_certificate(
                &q,
                &serde_json::from_value::<Vec<String>>(exclusion["certificate"].clone())?,
            )?;
        }
    }
    Ok(())
}

pub fn solve(p: &Problem, timeout: Duration, max_work: usize, max_rows: usize) -> Outcome {
    let deadline = Instant::now() + timeout;
    let unknown = |reason: &str| Outcome::unknown("interval-invariant", reason, 0);
    if p.validate().is_err() {
        return unknown("invalid problem");
    }
    let cs = controls(p, Instant::now() + timeout / 10);
    let Ok(boxes) = discover(p, &cs, deadline, max_work) else {
        return unknown("interval discovery limited");
    };
    let mut exclusions = vec![];
    for (i, b) in boxes.iter().enumerate() {
        let Ok(q) = strengthen(p, b) else {
            return unknown("interval bound exceeds arithmetic range");
        };
        let budget = deadline.saturating_duration_since(Instant::now()) / (boxes.len() - i) as u32;
        let out = integer_equation::solve(&q, budget, max_rows);
        if out.verdict != "unreachable" {
            return unknown("invariant does not exclude target within budget");
        }
        if let Some(proof) = out.proof {
            exclusions.push(proof);
        } else if let Some(certificate) = out.certificate {
            exclusions.push(json!({"kind":"farkas", "certificate":certificate}));
        } else {
            return unknown("missing arithmetic certificate");
        }
    }
    let proof = json!({"kind":"interval-invariant-v1", "controls":cs,"regions":boxes,"exclusions":exclusions});
    if let Err(error) = verify_certificate(p, &proof) {
        return unknown(&format!("certificate check failed: {error}"));
    }
    let mut result = unknown("checked inductive interval partition and arithmetic exclusions");
    result.verdict = "unreachable";
    result.proof = Some(proof);
    result.states = boxes.len();
    result
}
