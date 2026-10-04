//! Exact finite projections of counters with independently certified bounds.
use crate::{
    control::{Control, Edge},
    model::Problem,
};
use anyhow::{Context, Result, ensure};
use num_bigint::BigInt;
use num_traits::ToPrimitive;
use std::{collections::HashMap, time::Instant};

pub const MAX_MODES: usize = 4096;
pub const MAX_EDGES: usize = 8192;
pub const MAX_IMPLICIT_VISITS: usize = 20_000_000;

/// The moment relaxation needs only edges and exact selected coordinates.
pub trait Graph {
    fn places(&self) -> &[usize];
    fn mode_count(&self) -> usize;
    fn initial(&self) -> usize;
    fn edges(&self) -> &[Edge];
    fn value(&self, mode: usize, place: usize) -> Option<u64>;
    fn validate(&self, problem: &Problem) -> Result<()>;
}

impl Graph for Control {
    fn places(&self) -> &[usize] {
        &self.places
    }
    fn mode_count(&self) -> usize {
        self.modes.len()
    }
    fn initial(&self) -> usize {
        self.initial
    }
    fn edges(&self) -> &[Edge] {
        &self.edges
    }
    fn value(&self, mode: usize, place: usize) -> Option<u64> {
        self.places.binary_search(&place).ok()?;
        Some(u64::from(*self.modes.get(mode)? == place))
    }
    fn validate(&self, problem: &Problem) -> Result<()> {
        ensure!(
            self.initial < self.modes.len()
                && self.modes.iter().all(|&i| i < problem.places.len())
                && self.places.iter().all(|&i| i < problem.places.len()),
            "invalid control coordinate"
        );
        Ok(())
    }
}

#[derive(Clone, Debug)]
pub struct FiniteControl {
    pub places: Vec<usize>,
    pub modes: Vec<Vec<u64>>,
    pub edges: Vec<Edge>,
}

impl Graph for FiniteControl {
    fn places(&self) -> &[usize] {
        &self.places
    }
    fn mode_count(&self) -> usize {
        self.modes.len()
    }
    fn initial(&self) -> usize {
        0
    }
    fn edges(&self) -> &[Edge] {
        &self.edges
    }
    fn value(&self, mode: usize, place: usize) -> Option<u64> {
        let i = self.places.binary_search(&place).ok()?;
        self.modes.get(mode)?.get(i).copied()
    }
    fn validate(&self, problem: &Problem) -> Result<()> {
        ensure!(
            !self.modes.is_empty()
                && self.places.windows(2).all(|w| w[0] < w[1])
                && self.places.iter().all(|&i| i < problem.places.len())
                && self.modes.iter().all(|m| m.len() == self.places.len()),
            "invalid finite control coordinate"
        );
        Ok(())
    }
}

/// Bounds must have been checked against the original problem. Failure returns
/// no graph: a prefix of this traversal cannot support a reachability proof.
pub fn build(
    problem: &Problem,
    places: &[usize],
    bounds: &[Option<BigInt>],
    deadline: Option<Instant>,
) -> Result<FiniteControl> {
    build_with_limits(problem, places, bounds, MAX_MODES, MAX_EDGES, deadline)
}

pub fn build_with_limits(
    problem: &Problem,
    places: &[usize],
    bounds: &[Option<BigInt>],
    max_modes: usize,
    max_edges: usize,
    deadline: Option<Instant>,
) -> Result<FiniteControl> {
    build_internal(
        problem, places, bounds, max_modes, max_edges, deadline, false,
    )
}

/// Complete canonical modes, retaining every mode-changing edge. Self-loops
/// must be regenerated from the original net by users of this representation.
pub fn build_without_stutters(
    problem: &Problem,
    places: &[usize],
    bounds: &[Option<BigInt>],
    deadline: Option<Instant>,
) -> Result<FiniteControl> {
    build_internal(
        problem, places, bounds, MAX_MODES, MAX_EDGES, deadline, true,
    )
}

fn build_internal(
    problem: &Problem,
    places: &[usize],
    bounds: &[Option<BigInt>],
    max_modes: usize,
    max_edges: usize,
    deadline: Option<Instant>,
    omit_stutters: bool,
) -> Result<FiniteControl> {
    let in_time = || deadline.is_none_or(|limit| Instant::now() < limit);
    ensure!(in_time(), "finite control deadline exhausted");
    problem.validate()?;
    ensure!(
        max_modes > 0 && max_modes <= MAX_MODES && max_edges <= MAX_EDGES,
        "invalid finite control limits"
    );
    ensure!(
        places.windows(2).all(|w| w[0] < w[1]) && places.iter().all(|&p| p < problem.places.len()),
        "finite control places must be sorted, unique, and in range"
    );
    let upper: Vec<u64> = places
        .iter()
        .map(|&p| {
            let bound = bounds
                .get(p)
                .and_then(Option::as_ref)
                .and_then(ToPrimitive::to_u64)
                .context("missing representable finite bound")?;
            ensure!(
                problem.initial[p] <= bound,
                "initial marking exceeds finite bound"
            );
            Ok(bound)
        })
        .collect::<Result<_>>()?;
    let mut coordinate = vec![None; problem.places.len()];
    for (i, &place) in places.iter().enumerate() {
        coordinate[place] = Some(i);
    }
    let mut transitions = Vec::with_capacity(problem.transitions.len());
    for transition in &problem.transitions {
        ensure!(in_time(), "finite control deadline exhausted");
        let project = |arcs: &[(usize, u64)]| -> Vec<(usize, u64)> {
            arcs.iter()
                .filter_map(|&(p, w)| coordinate[p].map(|i| (i, w)))
                .collect()
        };
        transitions.push((project(&transition.pre), project(&transition.post)));
    }
    let initial: Vec<_> = places.iter().map(|&p| problem.initial[p]).collect();
    let mut graph = FiniteControl {
        places: places.to_vec(),
        modes: vec![initial.clone()],
        edges: vec![],
    };
    let mut indices = HashMap::from([(initial, 0)]);
    let mut source = 0;
    let mut visits = 0usize;
    while source < graph.modes.len() {
        ensure!(in_time(), "finite control deadline exhausted");
        for (transition, (pre, post)) in transitions.iter().enumerate() {
            ensure!(in_time(), "finite control deadline exhausted");
            if omit_stutters {
                ensure!(
                    visits < MAX_IMPLICIT_VISITS,
                    "finite control visit limit exhausted"
                );
                visits += 1;
            }
            if pre.iter().any(|&(i, w)| graph.modes[source][i] < w) {
                continue;
            }
            let mut next = graph.modes[source].clone();
            for &(i, w) in pre {
                next[i] -= w;
            }
            let mut exceeds = false;
            for &(i, w) in post {
                // Subtraction from the bound avoids overflowing the successor.
                if w > upper[i] - next[i] {
                    exceeds = true;
                    break;
                }
                next[i] = next[i]
                    .checked_add(w)
                    .context("finite successor overflow")?;
            }
            if exceeds {
                continue;
            }
            if omit_stutters && next == graph.modes[source] {
                continue;
            }
            ensure!(
                graph.edges.len() < max_edges,
                "finite control edge limit exhausted"
            );
            let target = if let Some(&q) = indices.get(&next) {
                q
            } else {
                ensure!(
                    graph.modes.len() < max_modes,
                    "finite control mode limit exhausted"
                );
                let q = graph.modes.len();
                indices.insert(next.clone(), q);
                graph.modes.push(next);
                q
            };
            graph.edges.push(Edge {
                source,
                target,
                transition,
            });
        }
        source += 1;
    }
    ensure!(in_time(), "finite control deadline exhausted");
    Ok(graph)
}
