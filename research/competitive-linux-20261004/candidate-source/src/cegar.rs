//! Finite threshold abstraction with concrete counterexample replay.
use crate::{model::Problem, search::Outcome};
use anyhow::{Result, ensure};
use num_bigint::BigInt;
use serde_json::{Value, json};
use std::{
    collections::{HashMap, HashSet},
    time::{Duration, Instant},
};

fn abstract_marking(m: &[u64], k: &[u64]) -> Vec<u64> {
    m.iter().zip(k).map(|(&x, &cap)| x.min(cap)).collect()
}

fn target_possible(p: &Problem, s: &[u64], k: &[u64]) -> bool {
    p.target.iter().all(|c| {
        let base: BigInt = c
            .coefficients
            .iter()
            .zip(s)
            .map(|(&a, &x)| BigInt::from(a) * x)
            .sum();
        let upper_infinite = c
            .coefficients
            .iter()
            .zip(s)
            .zip(k)
            .any(|((&a, &x), &cap)| x == cap && a > 0);
        let lower_infinite = c
            .coefficients
            .iter()
            .zip(s)
            .zip(k)
            .any(|((&a, &x), &cap)| x == cap && a < 0);
        (upper_infinite || base >= BigInt::from(c.bound))
            && (!c.equality || lower_infinite || base <= BigInt::from(c.bound))
    })
}

// Enumerate a Cartesian product incrementally so one transition cannot allocate
// an exponential intermediate list before the caller checks its budget.
fn successors(
    p: &Problem,
    s: &[u64],
    k: &[u64],
    t: usize,
    mut visit: impl FnMut(Vec<u64>) -> bool,
) -> bool {
    let mut pre = vec![0; k.len()];
    let mut post = vec![0; k.len()];
    for &(i, w) in &p.transitions[t].pre {
        pre[i] = w;
    }
    for &(i, w) in &p.transitions[t].post {
        post[i] = w;
    }
    let mut lo = Vec::with_capacity(k.len());
    let mut hi = Vec::with_capacity(k.len());
    for i in 0..k.len() {
        if s[i] < k[i] && s[i] < pre[i] {
            return true;
        }
        let lower = u128::from(s[i].max(pre[i])) - u128::from(pre[i]) + u128::from(post[i]);
        let lower = lower.min(u128::from(k[i])) as u64;
        lo.push(lower);
        hi.push(if s[i] == k[i] { k[i] } else { lower });
    }
    let mut next = lo.clone();
    loop {
        if !visit(next.clone()) {
            return false;
        }
        let mut i = 0;
        while i < next.len() && next[i] == hi[i] {
            next[i] = lo[i];
            i += 1;
        }
        if i == next.len() {
            return true;
        }
        next[i] += 1;
    }
}

pub fn verify_certificate(p: &Problem, proof: &Value) -> Result<()> {
    ensure!(proof["kind"] == "threshold-closure-v1", "wrong proof kind");
    let k: Vec<u64> = serde_json::from_value(proof["thresholds"].clone())?;
    let states: Vec<Vec<u64>> = serde_json::from_value(proof["states"].clone())?;
    ensure!(k.len() == p.places.len(), "invalid thresholds");
    ensure!(
        states
            .iter()
            .all(|s| s.len() == k.len() && s.iter().zip(&k).all(|(x, cap)| x <= cap)),
        "invalid states"
    );
    let set: HashSet<_> = states.into_iter().collect();
    ensure!(
        set.contains(&abstract_marking(&p.initial, &k)),
        "missing initial state"
    );
    for s in &set {
        ensure!(!target_possible(p, s, &k), "abstract target in closure");
        for t in 0..p.transitions.len() {
            ensure!(
                successors(p, s, &k, t, |next| set.contains(&next)),
                "closure missing successor"
            );
        }
    }
    Ok(())
}

pub fn solve(p: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    let start = Instant::now();
    let mut k = vec![2; p.places.len()];
    let mut total = 0;
    let mut rounds = 0;
    loop {
        rounds += 1;
        let initial = abstract_marking(&p.initial, &k);
        let mut ids = HashMap::from([(initial.clone(), 0)]);
        let mut states = vec![initial];
        let mut parents = vec![None::<(usize, usize)>];
        let mut head = 0;
        let mut refine = None;
        while head < states.len() {
            if start.elapsed() >= timeout || total >= max_states {
                return Outcome::unknown(
                    "cegar",
                    &format!("abstraction budget after {rounds} rounds"),
                    total,
                );
            }
            total += 1;
            let s = states[head].clone();
            if target_possible(p, &s, &k) {
                let mut trace = vec![];
                let mut cursor = head;
                while let Some((prev, t)) = parents[cursor] {
                    if start.elapsed() >= timeout {
                        return Outcome::unknown("cegar", "path reconstruction deadline", total);
                    }
                    trace.push(t);
                    cursor = prev;
                }
                trace.reverse();
                let mut m = p.initial.clone();
                let mut peak = m.clone();
                let mut valid = true;
                for &t in &trace {
                    if start.elapsed() >= timeout {
                        return Outcome::unknown("cegar", "concrete replay deadline", total);
                    }
                    match p.fire(&m, t) {
                        Ok(Some(next)) => {
                            m = next;
                            for (a, &b) in peak.iter_mut().zip(&m) {
                                *a = (*a).max(b);
                            }
                        }
                        Ok(None) => {
                            valid = false;
                            break;
                        }
                        Err(_) => {
                            return Outcome::unknown("cegar", "concrete replay overflow", total);
                        }
                    }
                }
                if valid && p.check_witness(&trace).is_ok() {
                    return Outcome {
                        verdict: "reachable",
                        method: "cegar".into(),
                        reason: format!("replayed abstract path after {rounds} rounds"),
                        states: total,
                        trace,
                        marking: Some(m),
                        certificate: None,
                        proof: None,
                    };
                }
                // Make each concretely visited value exact in the next abstraction.
                // Doubling also separates choices after the first disabled step.
                let mut changed = false;
                for (cap, &value) in k.iter_mut().zip(&peak) {
                    if value >= *cap {
                        let Some(new) = cap
                            .checked_mul(2)
                            .and_then(|x| value.checked_add(1).map(|y| x.max(y)))
                        else {
                            return Outcome::unknown("cegar", "threshold overflow", total);
                        };
                        *cap = new;
                        changed = true;
                    }
                }
                if !changed {
                    // The spurious path may introduce high values absent from its
                    // concrete prefix; split those coordinates as well.
                    for cap in &mut k {
                        let Some(new) = cap.checked_mul(2) else {
                            return Outcome::unknown("cegar", "threshold overflow", total);
                        };
                        *cap = new;
                    }
                }
                refine = Some(());
                break;
            }
            for t in 0..p.transitions.len() {
                if start.elapsed() >= timeout {
                    return Outcome::unknown("cegar", "transition scan deadline", total);
                }
                let complete = successors(p, &s, &k, t, |next| {
                    if start.elapsed() >= timeout {
                        return false;
                    }
                    if !ids.contains_key(&next) {
                        if states.len() >= max_states {
                            return false;
                        }
                        ids.insert(next.clone(), states.len());
                        states.push(next);
                        parents.push(Some((head, t)));
                    }
                    true
                });
                if !complete {
                    return Outcome::unknown("cegar", "abstract successor budget", total);
                }
            }
            head += 1;
        }
        if refine.is_none() {
            return Outcome {
                verdict: "unreachable",
                method: "cegar".into(),
                reason: format!("finite abstract closure excludes target after {rounds} rounds"),
                states: total,
                trace: vec![],
                marking: None,
                certificate: None,
                proof: Some(json!({"kind":"threshold-closure-v1","thresholds":k,"states":states})),
            };
        }
    }
}
