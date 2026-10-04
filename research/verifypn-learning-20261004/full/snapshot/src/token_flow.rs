//! Reference token-moment relaxation over a certified one-token controller.
use crate::{
    control::{self, Control},
    linear::{Row, System},
    model::Problem,
    search::Outcome,
};
use anyhow::{Result, ensure};
use num_bigint::BigInt;
use num_traits::Zero;
use serde::{Deserialize, Serialize};
use std::{
    collections::BTreeMap,
    time::{Duration, Instant},
};

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Certificate {
    pub kind: String,
    pub controls: Vec<usize>,
    pub terminals: Vec<Vec<(usize, String)>>,
}

pub(crate) fn row(terms: impl IntoIterator<Item = (usize, BigInt)>, bound: BigInt) -> Row {
    let mut coefficients = BTreeMap::<usize, BigInt>::new();
    for (i, coefficient) in terms {
        *coefficients.entry(i).or_default() += coefficient;
    }
    Row {
        coefficients: coefficients
            .into_iter()
            .filter(|(_, a)| !a.is_zero())
            .collect(),
        bound,
    }
}

pub(crate) fn equality(system: &mut System, row: Row) {
    system.rows.push(Row {
        coefficients: row.coefficients.iter().map(|(i, a)| (*i, -a)).collect(),
        bound: -&row.bound,
    });
    system.rows.push(row);
}

/// Variable order: edge counts, final marking, then edge-major source moments.
/// A source moment sums the marking immediately before all occurrences of an edge.
/// All variables are nonnegative, with no candidate-search count bound.
pub fn relaxation(p: &Problem, graph: &Control, terminal: usize) -> Result<System> {
    ensure!(terminal < graph.modes.len(), "invalid terminal mode");
    let edges = graph.edges.len();
    let places = p.places.len();
    let variables = edges
        .checked_mul(places + 1)
        .and_then(|n| n.checked_add(places))
        .ok_or_else(|| anyhow::anyhow!("token-flow dimension overflow"))?;
    ensure!(variables <= 100_000, "token-flow dimension limit");
    let mut system = System {
        variables,
        rows: vec![],
    };
    let marking = |i| edges + i;
    let moment = |e, i| edges + places + e * places + i;
    let mut effects = vec![BTreeMap::<usize, BigInt>::new(); p.transitions.len()];
    for (t, transition) in p.transitions.iter().enumerate() {
        for &(i, w) in &transition.pre {
            *effects[t].entry(i).or_default() -= w;
        }
        for &(i, w) in &transition.post {
            *effects[t].entry(i).or_default() += w;
        }
    }
    for i in 0..places {
        let mut terms = vec![(marking(i), 1.into())];
        for (e, edge) in graph.edges.iter().enumerate() {
            if let Some(delta) = effects[edge.transition].get(&i) {
                terms.push((e, -delta));
            }
        }
        equality(&mut system, row(terms, p.initial[i].into()));
    }
    for &i in &graph.places {
        equality(
            &mut system,
            row(
                [(marking(i), 1.into())],
                u8::from(graph.modes[terminal] == i).into(),
            ),
        );
    }
    for c in &p.target {
        let target = row(
            c.coefficients
                .iter()
                .enumerate()
                .map(|(i, &a)| (marking(i), a.into())),
            c.bound.into(),
        );
        if c.equality {
            equality(&mut system, target);
        } else {
            system.rows.push(target);
        }
    }
    for q in 0..graph.modes.len() {
        let mut counts = vec![];
        for (e, edge) in graph.edges.iter().enumerate() {
            if edge.source == q {
                counts.push((e, 1.into()));
            }
            if edge.target == q {
                counts.push((e, (-1).into()));
            }
        }
        let rhs = i32::from(q == graph.initial) - i32::from(q == terminal);
        equality(&mut system, row(counts, rhs.into()));
        for i in 0..places {
            let mut terms = vec![];
            if q == terminal {
                terms.push((marking(i), 1.into()));
            }
            for (e, edge) in graph.edges.iter().enumerate() {
                if edge.source == q {
                    terms.push((moment(e, i), 1.into()));
                }
                if edge.target == q {
                    terms.push((moment(e, i), (-1).into()));
                    if let Some(delta) = effects[edge.transition].get(&i) {
                        terms.push((e, -delta));
                    }
                }
            }
            let rhs = if q == graph.initial {
                p.initial[i].into()
            } else {
                BigInt::zero()
            };
            equality(&mut system, row(terms, rhs));
        }
    }
    for (e, edge) in graph.edges.iter().enumerate() {
        for &(i, weight) in &p.transitions[edge.transition].pre {
            system.rows.push(row(
                [(moment(e, i), 1.into()), (e, -BigInt::from(weight))],
                BigInt::zero(),
            ));
        }
        for &i in &graph.places {
            let value = u8::from(graph.modes[edge.source] == i);
            equality(
                &mut system,
                row(
                    [(moment(e, i), 1.into()), (e, -BigInt::from(value))],
                    BigInt::zero(),
                ),
            );
        }
    }
    Ok(system)
}

pub fn verify_certificate(p: &Problem, value: &serde_json::Value) -> Result<()> {
    let certificate: Certificate = serde_json::from_value(value.clone())?;
    ensure!(certificate.kind == "token-moment-v1", "wrong proof kind");
    let graph = control::build(p, &certificate.controls, 8192)?;
    ensure!(
        certificate.terminals.len() == graph.modes.len(),
        "terminal coverage mismatch"
    );
    for (q, multipliers) in certificate.terminals.iter().enumerate() {
        relaxation(p, &graph, q)?.check(multipliers)?;
    }
    Ok(())
}

pub fn solve(p: &Problem, timeout: Duration) -> Outcome {
    let deadline = Instant::now() + timeout;
    let mut out = Outcome::unknown("token-moment", "no certified control abstraction", 0);
    if timeout.is_zero() || p.validate().is_err() {
        return out;
    }
    if p.accepts(&p.initial).unwrap_or(false) {
        out.verdict = "reachable";
        out.marking = Some(p.initial.clone());
        out.reason = "initial marking satisfies target".into();
        return out;
    }
    let Some(graph) = control::discover(p, Instant::now() + timeout / 5, 8192) else {
        return out;
    };
    let controls = graph.places.clone();
    let mut terminals = vec![];
    for q in 0..graph.modes.len() {
        if Instant::now() >= deadline {
            break;
        }
        let Ok(system) = relaxation(p, &graph, q) else {
            break;
        };
        let remaining = deadline.saturating_duration_since(Instant::now());
        let budget = remaining / (graph.modes.len() - q) as u32;
        let Some(proof) = system.refute(Instant::now() + budget) else {
            break;
        };
        terminals.push(proof);
    }
    out.reason = format!(
        "{} of {} terminal modes refuted; {} control edges",
        terminals.len(),
        graph.modes.len(),
        graph.edges.len()
    );
    if terminals.len() == graph.modes.len() {
        let proof = serde_json::to_value(Certificate {
            kind: "token-moment-v1".into(),
            controls,
            terminals,
        })
        .unwrap();
        if verify_certificate(p, &proof).is_ok() {
            out.verdict = "unreachable";
            out.proof = Some(proof);
        }
    }
    out
}
