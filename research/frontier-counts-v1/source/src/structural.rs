//! Marked traps and initially empty siphons strengthen the rational state equation.
use crate::{
    model::{Constraint, Problem},
    search::Outcome,
    state_equation,
};
use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};
use std::{
    collections::HashSet,
    time::{Duration, Instant},
};

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TrapCertificate {
    pub kind: String,
    pub traps: Vec<Vec<usize>>,
    pub certificate: Vec<String>,
}

pub fn verify_trap(p: &Problem, trap: &[usize]) -> Result<()> {
    let mut included = vec![false; p.places.len()];
    for &place in trap {
        ensure!(place < included.len(), "trap place out of range");
        ensure!(!included[place], "duplicate trap place");
        included[place] = true;
    }
    ensure!(
        trap.iter().any(|&i| p.initial[i] > 0),
        "trap is not initially marked"
    );
    for transition in &p.transitions {
        ensure!(
            !transition.pre.iter().any(|&(i, _)| included[i])
                || transition.post.iter().any(|&(i, _)| included[i]),
            "transition can empty the proposed trap"
        );
    }
    Ok(())
}

fn strengthen(p: &Problem, traps: &[Vec<usize>]) -> Problem {
    let mut strengthened = p.clone();
    for trap in traps {
        let mut coefficients = vec![0; p.places.len()];
        for &i in trap {
            coefficients[i] = 1;
        }
        strengthened.target.push(Constraint {
            coefficients,
            bound: 1,
            equality: false,
        });
    }
    strengthened
}

pub fn verify_certificate(p: &Problem, proof: &serde_json::Value) -> Result<()> {
    p.validate()?;
    let proof: TrapCertificate = serde_json::from_value(proof.clone())?;
    ensure!(proof.kind == "marked-traps", "wrong structural proof kind");
    for trap in &proof.traps {
        verify_trap(p, trap)?;
    }
    state_equation::verify_certificate(&strengthen(p, &proof.traps), &proof.certificate)
}

// Every marked trap contains an initially marked place. A violated trap condition
// forces at least one output place into any extension, which gives the branches.
fn enumerate(
    p: &Problem,
    start: Instant,
    timeout: Duration,
    limit: usize,
) -> (Vec<Vec<usize>>, usize) {
    let mut stack: Vec<Vec<usize>> = p
        .initial
        .iter()
        .enumerate()
        .filter(|&(_, &v)| v > 0)
        .map(|(i, _)| vec![i])
        .collect();
    let mut seen = HashSet::new();
    let mut traps: Vec<Vec<usize>> = Vec::new();
    while let Some(candidate) = stack.pop() {
        if seen.len() >= limit || start.elapsed() >= timeout {
            break;
        }
        if !seen.insert(candidate.clone()) {
            continue;
        }
        if traps
            .iter()
            .any(|t| t.iter().all(|i| candidate.binary_search(i).is_ok()))
        {
            continue;
        }
        let violated = p.transitions.iter().find(|t| {
            t.pre
                .iter()
                .any(|(i, _)| candidate.binary_search(i).is_ok())
                && !t
                    .post
                    .iter()
                    .any(|(i, _)| candidate.binary_search(i).is_ok())
        });
        match violated {
            None => {
                traps.retain(|t| !candidate.iter().all(|i| t.binary_search(i).is_ok()));
                traps.push(candidate);
            }
            Some(t) => {
                for &(place, _) in &t.post {
                    if stack.len() >= limit {
                        break;
                    }
                    let mut extension = candidate.clone();
                    let index = extension.binary_search(&place).unwrap_err();
                    extension.insert(index, place);
                    stack.push(extension);
                }
            }
        }
    }
    (traps, seen.len())
}

pub fn solve(p: &Problem, timeout: Duration, max_rows: usize) -> Outcome {
    let start = Instant::now();
    let (traps, examined) = enumerate(p, start, timeout / 4, max_rows.saturating_mul(8));
    if traps.is_empty() {
        return Outcome::unknown(
            "marked-traps",
            "no marked trap found within limits",
            examined,
        );
    }
    let mut result = state_equation::solve(
        &strengthen(p, &traps),
        timeout.saturating_sub(start.elapsed()),
        max_rows,
    );
    result.method = "marked-traps".into();
    result.states = examined;
    if result.verdict == "unreachable" {
        let proof = TrapCertificate {
            kind: "marked-traps".into(),
            traps,
            certificate: result.certificate.take().unwrap(),
        };
        let proof = serde_json::to_value(proof).unwrap();
        if let Err(error) = verify_certificate(p, &proof) {
            return Outcome::unknown(
                "marked-traps",
                &format!("certificate verification failed: {error}"),
                examined,
            );
        }
        result.reason = "marked traps and exact rational Farkas certificate".into();
        result.proof = Some(proof);
    }
    result
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SupportCertificate {
    pub kind: String,
    pub empty_siphon: Vec<usize>,
    pub certificate: Vec<String>,
}

fn restrict_support(p: &Problem, empty_siphon: &[usize]) -> Problem {
    let mut strengthened = p.clone();
    let mut coefficients = vec![0; p.places.len()];
    for &i in empty_siphon {
        coefficients[i] = 1;
    }
    strengthened.target.push(Constraint {
        coefficients,
        bound: 0,
        equality: true,
    });
    strengthened
}

pub fn verify_support_certificate(p: &Problem, proof: &serde_json::Value) -> Result<()> {
    p.validate()?;
    let proof: SupportCertificate = serde_json::from_value(proof.clone())?;
    ensure!(proof.kind == "empty-siphon", "wrong support proof kind");
    let mut included = vec![false; p.places.len()];
    for &i in &proof.empty_siphon {
        ensure!(i < included.len(), "siphon place out of range");
        ensure!(!included[i], "duplicate siphon place");
        ensure!(p.initial[i] == 0, "siphon initially marked");
        included[i] = true;
    }
    for t in &p.transitions {
        ensure!(
            !t.post.iter().any(|&(i, _)| included[i]) || t.pre.iter().any(|&(i, _)| included[i]),
            "transition can mark empty siphon"
        );
    }
    state_equation::verify_certificate(
        &restrict_support(p, &proof.empty_siphon),
        &proof.certificate,
    )
}

pub fn solve_support(p: &Problem, timeout: Duration, max_rows: usize) -> Outcome {
    let start = Instant::now();
    let mut supported: Vec<_> = p.initial.iter().map(|&x| x > 0).collect();
    loop {
        let mut changed = false;
        for t in &p.transitions {
            if start.elapsed() >= timeout {
                return Outcome::unknown("support", "time limit", 0);
            }
            if t.pre.iter().all(|&(i, _)| supported[i]) {
                for &(i, _) in &t.post {
                    changed |= !supported[i];
                    supported[i] = true;
                }
            }
        }
        if !changed {
            break;
        }
    }
    let empty_siphon: Vec<_> = supported
        .iter()
        .enumerate()
        .filter(|&(_, &v)| !v)
        .map(|(i, _)| i)
        .collect();
    if empty_siphon.is_empty() {
        return Outcome::unknown("support", "every place has qualitative support", 0);
    }
    let mut result = state_equation::solve(
        &restrict_support(p, &empty_siphon),
        timeout.saturating_sub(start.elapsed()),
        max_rows,
    );
    result.method = "support".into();
    if result.verdict == "unreachable" {
        let proof = SupportCertificate {
            kind: "empty-siphon".into(),
            empty_siphon,
            certificate: result.certificate.take().unwrap(),
        };
        let proof = serde_json::to_value(proof).unwrap();
        if let Err(error) = verify_support_certificate(p, &proof) {
            return Outcome::unknown(
                "support",
                &format!("certificate verification failed: {error}"),
                0,
            );
        }
        result.reason = "initially empty siphon and exact rational Farkas certificate".into();
        result.proof = Some(proof);
    }
    result
}
