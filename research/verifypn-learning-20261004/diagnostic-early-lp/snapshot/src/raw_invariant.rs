//! Exact checking of credited serial-component invariants on original raw nets.
use crate::raw_target::{LinearSet, RawQuery};
use anyhow::{Result, ensure};
use num_bigint::BigInt;
use num_traits::Zero;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashMap, HashSet};
use std::time::Instant;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Certificate {
    pub format: String,
    pub control_places: Vec<usize>,
    pub credits: Vec<Credit>,
    pub initial_node: usize,
    pub initial_coefficients: Vec<(usize, u64)>,
    pub nodes: Vec<Node>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Credit {
    pub place: usize,
    pub terms: Vec<(usize, u64)>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Node {
    pub control: Vec<u64>,
    pub component: usize,
    pub edges: Vec<Edge>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Edge {
    pub transition: usize,
    pub target: usize,
    pub base_coefficients: Vec<(usize, u64)>,
    pub period_coefficients: Vec<Vec<(usize, u64)>>,
}

struct Budget {
    deadline: Instant,
    remaining: usize,
}
impl Budget {
    fn tick(&mut self) -> Result<()> {
        ensure!(
            Instant::now() < self.deadline,
            "raw invariant checking deadline"
        );
        ensure!(self.remaining > 0, "raw invariant checking work limit");
        self.remaining -= 1;
        Ok(())
    }
}

type Vector = BTreeMap<usize, BigInt>;

fn add(vector: &mut Vector, place: usize, amount: BigInt) {
    let value = vector.entry(place).or_default();
    *value += amount;
    if value.is_zero() {
        vector.remove(&place);
    }
}

fn vector(terms: &[(usize, u64)], budget: &mut Budget) -> Result<Vector> {
    let mut result = Vector::new();
    for &(place, weight) in terms {
        budget.tick()?;
        add(&mut result, place, weight.into());
    }
    Ok(result)
}

fn combination(
    component: &LinearSet,
    coefficients: &[(usize, u64)],
    with_base: bool,
    budget: &mut Budget,
) -> Result<Vector> {
    let mut result = if with_base {
        vector(&component.base, budget)?
    } else {
        Vector::new()
    };
    let mut previous = None;
    for &(index, coefficient) in coefficients {
        budget.tick()?;
        ensure!(
            coefficient > 0 && previous.is_none_or(|last| last < index),
            "coefficients must be sorted, unique, and positive"
        );
        let period = component
            .periods
            .get(index)
            .ok_or_else(|| anyhow::anyhow!("invalid coefficient period index"))?;
        previous = Some(index);
        for &(place, weight) in period {
            budget.tick()?;
            add(&mut result, place, BigInt::from(weight) * coefficient);
        }
    }
    Ok(result)
}

struct Transition {
    pre: Vec<(usize, u64)>,
    delta: Vector,
    credited: Vector,
}

/// Proves that every completed marking's response vector belongs to the excluded
/// serial language. Limits count structural/arithmetic work, not only edges.
/// Exhaustion or any malformed obligation is an error, never partial acceptance.
pub fn check(
    q: &RawQuery,
    certificate: &Certificate,
    deadline: Instant,
    max_obligations: usize,
) -> Result<()> {
    let mut budget = Budget {
        deadline,
        remaining: max_obligations,
    };
    budget.tick()?;
    q.validate()?;
    ensure!(
        q.target.excluded_automaton.is_none(),
        "component invariants require a semilinear target"
    );
    budget.tick()?;
    ensure!(
        certificate.format == "raw-component-invariant-v1",
        "wrong certificate format"
    );
    ensure!(
        certificate
            .control_places
            .windows(2)
            .all(|pair| pair[0] < pair[1]),
        "control places must be sorted and unique"
    );
    let mut controls = HashMap::new();
    for (index, &place) in certificate.control_places.iter().enumerate() {
        budget.tick()?;
        ensure!(place < q.places.len(), "invalid control place");
        controls.insert(place, index);
    }
    let zeros: HashSet<_> = q.target.zero_places.iter().copied().collect();
    let responses: HashSet<_> = q.target.response_places.iter().copied().collect();
    let mut credits = HashMap::new();
    for credit in &certificate.credits {
        budget.tick()?;
        ensure!(
            zeros.contains(&credit.place),
            "credits require completion-zero places"
        );
        ensure!(
            credits.insert(credit.place, &credit.terms).is_none(),
            "duplicate credit column"
        );
        let mut used = HashSet::new();
        for &(place, weight) in &credit.terms {
            budget.tick()?;
            ensure!(
                responses.contains(&place) && weight > 0 && used.insert(place),
                "invalid or duplicate credit term"
            );
        }
    }
    let mut identities = HashSet::new();
    for node in &certificate.nodes {
        budget.tick()?;
        ensure!(
            node.control.len() == controls.len(),
            "control dimension mismatch"
        );
        ensure!(
            node.component < q.target.excluded_semilinear.len(),
            "invalid serial component"
        );
        ensure!(
            identities.insert((&node.control, node.component)),
            "duplicate invariant node"
        );
    }
    let initial = certificate
        .nodes
        .get(certificate.initial_node)
        .ok_or_else(|| anyhow::anyhow!("invalid initial node"))?;
    for (&place, &value) in certificate.control_places.iter().zip(&initial.control) {
        budget.tick()?;
        ensure!(value == q.initial[place], "wrong initial control");
    }
    let mut initial_credit = Vector::new();
    for &place in &q.target.response_places {
        budget.tick()?;
        add(&mut initial_credit, place, q.initial[place].into());
    }
    for credit in &certificate.credits {
        for &(place, weight) in &credit.terms {
            budget.tick()?;
            add(
                &mut initial_credit,
                place,
                BigInt::from(q.initial[credit.place]) * weight,
            );
        }
    }
    ensure!(
        initial_credit
            == combination(
                &q.target.excluded_semilinear[initial.component],
                &certificate.initial_coefficients,
                true,
                &mut budget
            )?,
        "initial credited marking outside component"
    );

    let mut transitions = Vec::with_capacity(q.transitions.len());
    for transition in &q.transitions {
        budget.tick()?;
        let mut projected = Transition {
            pre: vec![],
            delta: Vector::new(),
            credited: Vector::new(),
        };
        for (sign, arcs) in [(-1i32, &transition.pre), (1i32, &transition.post)] {
            for &(place, weight) in arcs {
                budget.tick()?;
                let amount = BigInt::from(weight) * sign;
                if let Some(&index) = controls.get(&place) {
                    if sign == -1 {
                        projected.pre.push((index, weight));
                    }
                    add(&mut projected.delta, index, amount.clone());
                }
                if responses.contains(&place) {
                    add(&mut projected.credited, place, amount.clone());
                }
                if let Some(terms) = credits.get(&place) {
                    for &(response, coefficient) in terms.iter() {
                        budget.tick()?;
                        add(&mut projected.credited, response, &amount * coefficient);
                    }
                }
            }
        }
        transitions.push(projected);
    }
    let presets: Vec<_> = transitions.iter().map(|t| t.pre.as_slice()).collect();
    let transition_index =
        crate::successors::TransitionIndex::from_presets(controls.len(), &presets);
    let mut candidates = vec![];
    for node in &certificate.nodes {
        budget.tick()?;
        let source = &q.target.excluded_semilinear[node.component];
        let mut edges = HashMap::new();
        for edge in &node.edges {
            budget.tick()?;
            ensure!(
                edge.transition < transitions.len(),
                "invalid transition index"
            );
            ensure!(
                edges.insert(edge.transition, edge).is_none(),
                "duplicate transition edge"
            );
        }
        for _ in &node.control {
            budget.tick()?;
        }
        transition_index.candidates(&node.control, &mut candidates);
        for &index in &candidates {
            budget.tick()?;
            let transition = &transitions[index];
            if transition.delta.is_empty() && transition.credited.is_empty() {
                ensure!(!edges.contains_key(&index), "extra stuttering edge");
                continue;
            }
            let enabled = transition
                .pre
                .iter()
                .all(|&(place, weight)| node.control[place] >= weight);
            if !enabled {
                ensure!(
                    !edges.contains_key(&index),
                    "edge for disabled projected transition"
                );
                continue;
            }
            let edge = edges
                .remove(&index)
                .ok_or_else(|| anyhow::anyhow!("missing transition edge"))?;
            let target = certificate
                .nodes
                .get(edge.target)
                .ok_or_else(|| anyhow::anyhow!("invalid edge target"))?;
            for (place, (&before, &after)) in node.control.iter().zip(&target.control).enumerate() {
                budget.tick()?;
                let expected = BigInt::from(before)
                    + transition.delta.get(&place).cloned().unwrap_or_default();
                ensure!(
                    expected == BigInt::from(after),
                    "wrong projected successor control"
                );
            }
            let destination = &q.target.excluded_semilinear[target.component];
            let mut shifted = vector(&source.base, &mut budget)?;
            for (&place, value) in &transition.credited {
                budget.tick()?;
                add(&mut shifted, place, value.clone());
            }
            ensure!(
                shifted == combination(destination, &edge.base_coefficients, true, &mut budget)?,
                "invalid shifted base map"
            );
            ensure!(
                edge.period_coefficients.len() == source.periods.len(),
                "source period dimension mismatch"
            );
            for (period, coefficients) in source.periods.iter().zip(&edge.period_coefficients) {
                ensure!(
                    vector(period, &mut budget)?
                        == combination(destination, coefficients, false, &mut budget)?,
                    "invalid period map"
                );
            }
        }
        ensure!(
            edges.is_empty(),
            "extra disabled or stuttering transition edge"
        );
    }
    budget.tick()?;
    Ok(())
}
