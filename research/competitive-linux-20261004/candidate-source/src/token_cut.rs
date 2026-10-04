//! Lazy exact per-place flow cuts for the fixed-control token-moment relaxation.
use crate::{
    control,
    count_plan::{Realization, realize},
    finite_control::{self, Graph},
    flow,
    linear::{Row, System},
    model::Problem,
    place_bounds,
    search::Outcome,
    token_flow::{equality, row},
};
use anyhow::{Result, ensure};
use num_bigint::BigInt;
use num_rational::BigRational as Q;
use num_traits::{One, Signed, ToPrimitive, Zero};
use serde::{Deserialize, Serialize};
use std::time::{Duration, Instant};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Cut {
    pub place: usize,
    pub modes: Vec<usize>,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Terminal {
    pub cuts: Vec<Cut>,
    pub multipliers: Vec<(usize, String)>,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Certificate {
    pub kind: String,
    pub controls: Vec<usize>,
    pub terminals: Vec<Terminal>,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BoundedCertificate {
    pub kind: String,
    pub controls: Vec<usize>,
    pub bounds: place_bounds::Certificate,
    pub terminals: Vec<Terminal>,
}

fn effect(p: &Problem, t: usize, i: usize) -> BigInt {
    let tr = &p.transitions[t];
    BigInt::from(
        tr.post
            .iter()
            .find(|&&(j, _)| j == i)
            .map_or(0, |&(_, w)| w),
    ) - BigInt::from(tr.pre.iter().find(|&&(j, _)| j == i).map_or(0, |&(_, w)| w))
}

fn bounds(
    p: &Problem,
    graph: &impl Graph,
    e: usize,
    i: usize,
    finite: &[Option<BigInt>],
) -> (BigInt, Option<BigInt>) {
    let edge = &graph.edges()[e];
    if let Some(value) = graph.value(edge.source, i) {
        let value = BigInt::from(value);
        (value.clone(), Some(value))
    } else {
        let pre = p.transitions[edge.transition]
            .pre
            .iter()
            .find(|&&(j, _)| j == i)
            .map_or(0, |&(_, w)| w);
        // A transition requiring more than the invariant bound is disabled.
        // Keeping it with upper=pre is a safe relaxation and avoids negative capacities.
        (
            pre.into(),
            finite
                .get(i)
                .and_then(Clone::clone)
                .map(|upper| upper.max(pre.into())),
        )
    }
}

/// Nonnegative variables: edge counts followed by final markings.
/// Equalities use their negative row first, then their positive row.
pub fn master(p: &Problem, graph: &impl Graph, terminal: usize) -> Result<System> {
    master_with_deadline(p, graph, terminal, None)
}

pub(crate) fn master_with_deadline(
    p: &Problem,
    graph: &impl Graph,
    terminal: usize,
    deadline: Option<Instant>,
) -> Result<System> {
    let in_time = || deadline.is_none_or(|limit| Instant::now() < limit);
    ensure!(in_time(), "token-cut master deadline exhausted");
    ensure!(terminal < graph.mode_count(), "invalid terminal mode");
    let edges = graph.edges().len();
    let variables = edges
        .checked_add(p.places.len())
        .ok_or_else(|| anyhow::anyhow!("token-cut dimension overflow"))?;
    ensure!(variables <= 100_000, "token-cut dimension limit");
    ensure!(graph.mode_count() <= 100_000, "token-cut mode limit");
    p.validate()?;
    graph.validate(p)?;
    let mut system = System {
        variables,
        rows: vec![],
    };
    let mut markings = vec![Vec::new(); p.places.len()];
    let mut modes = vec![Vec::new(); graph.mode_count()];
    for (e, edge) in graph.edges().iter().enumerate() {
        ensure!(in_time(), "token-cut master deadline exhausted");
        ensure!(
            edge.transition < p.transitions.len()
                && edge.source < graph.mode_count()
                && edge.target < graph.mode_count(),
            "invalid control edge"
        );
        let transition = &p.transitions[edge.transition];
        for &(i, count) in &transition.pre {
            markings[i].push((e, BigInt::from(count)));
        }
        for &(i, count) in &transition.post {
            markings[i].push((e, -BigInt::from(count)));
        }
        if edge.source != edge.target {
            modes[edge.source].push((e, BigInt::one()));
            modes[edge.target].push((e, -BigInt::one()));
        }
    }
    for (i, mut terms) in markings.into_iter().enumerate() {
        ensure!(in_time(), "token-cut master deadline exhausted");
        terms.push((edges + i, BigInt::one()));
        equality(&mut system, row(terms, p.initial[i].into()));
    }
    for &i in graph.places() {
        ensure!(in_time(), "token-cut master deadline exhausted");
        equality(
            &mut system,
            row(
                [(edges + i, 1.into())],
                graph
                    .value(terminal, i)
                    .ok_or_else(|| anyhow::anyhow!("missing selected value"))?
                    .into(),
            ),
        );
    }
    for c in &p.target {
        ensure!(in_time(), "token-cut master deadline exhausted");
        let target = row(
            c.coefficients
                .iter()
                .enumerate()
                .filter(|(_, a)| **a != 0)
                .map(|(i, &a)| (edges + i, a.into())),
            c.bound.into(),
        );
        if c.equality {
            equality(&mut system, target);
        } else {
            system.rows.push(target);
        }
    }
    for (q, terms) in modes.into_iter().enumerate() {
        ensure!(in_time(), "token-cut master deadline exhausted");
        equality(
            &mut system,
            row(
                terms,
                (i32::from(q == graph.initial()) - i32::from(q == terminal)).into(),
            ),
        );
    }
    Ok(system)
}

pub fn cut_row(p: &Problem, graph: &impl Graph, terminal: usize, cut: &Cut) -> Result<Row> {
    bounded_cut_row(p, graph, terminal, cut, &[])
}

pub fn bounded_cut_row(
    p: &Problem,
    graph: &impl Graph,
    terminal: usize,
    cut: &Cut,
    finite: &[Option<BigInt>],
) -> Result<Row> {
    bounded_cut_row_with_deadline(p, graph, terminal, cut, finite, None)
}

pub(crate) fn bounded_cut_row_with_deadline(
    p: &Problem,
    graph: &impl Graph,
    terminal: usize,
    cut: &Cut,
    finite: &[Option<BigInt>],
    deadline: Option<Instant>,
) -> Result<Row> {
    let in_time = || deadline.is_none_or(|limit| Instant::now() < limit);
    ensure!(in_time(), "token-cut row deadline exhausted");
    ensure!(
        terminal < graph.mode_count() && cut.place < p.places.len(),
        "invalid cut coordinate"
    );
    ensure!(
        cut.modes.windows(2).all(|w| w[0] < w[1])
            && cut.modes.iter().all(|&q| q < graph.mode_count()),
        "invalid cut modes"
    );
    let inside = |q| cut.modes.binary_search(&q).is_ok();
    let mut terms = vec![];
    if inside(terminal) {
        terms.push((graph.edges().len() + cut.place, 1.into()));
    }
    for (e, edge) in graph.edges().iter().enumerate() {
        ensure!(in_time(), "token-cut row deadline exhausted");
        let delta = effect(p, edge.transition, cut.place);
        let (lower, upper) = bounds(p, graph, e, cut.place, finite);
        let coefficient = match (inside(edge.source), inside(edge.target)) {
            (true, true) => -delta,
            (false, true) => -lower - delta,
            (true, false) => {
                // A finite flow-computation substitute for infinity is not a marking bound.
                upper.ok_or_else(|| anyhow::anyhow!("cut crosses an unbounded edge"))?
            }
            (false, false) => BigInt::zero(),
        };
        terms.push((e, coefficient));
    }
    Ok(row(
        terms,
        if inside(graph.initial()) {
            p.initial[cut.place].into()
        } else {
            BigInt::zero()
        },
    ))
}

pub(crate) struct ScaledCandidate {
    scale: BigInt,
    values: Vec<BigInt>,
}

pub(crate) fn scaled(values: &[Q], deadline: Instant) -> Option<ScaledCandidate> {
    if Instant::now() >= deadline {
        return None;
    }
    let mut scale = BigInt::one();
    for value in values {
        if value.is_negative() || Instant::now() >= deadline {
            return None;
        }
        let (mut a, mut b) = (scale.clone(), value.denom().clone());
        while !b.is_zero() {
            (a, b) = (b.clone(), a % b);
        }
        scale = scale / a * value.denom();
        if scale.bits() > 4096 {
            return None;
        }
    }
    let mut integers = Vec::with_capacity(values.len());
    for value in values {
        if Instant::now() >= deadline {
            return None;
        }
        integers.push(value.numer() * (&scale / value.denom()));
    }
    Some(ScaledCandidate {
        scale,
        values: integers,
    })
}

#[derive(Debug, PartialEq, Eq)]
pub enum Separation {
    Feasible,
    Cut(Cut),
    Unknown,
}

pub fn separate_place(
    p: &Problem,
    graph: &impl Graph,
    terminal: usize,
    place: usize,
    values: &[Q],
    deadline: Instant,
) -> Separation {
    separate_bounded_place(p, graph, terminal, place, values, &[], deadline)
}

pub fn separate_bounded_place(
    p: &Problem,
    graph: &impl Graph,
    terminal: usize,
    place: usize,
    values: &[Q],
    finite: &[Option<BigInt>],
    deadline: Instant,
) -> Separation {
    if terminal >= graph.mode_count()
        || place >= p.places.len()
        || graph.edges().len().checked_add(p.places.len()) != Some(values.len())
    {
        return Separation::Unknown;
    }
    let Some(candidate) = scaled(values, deadline) else {
        return Separation::Unknown;
    };
    candidate.separate_place(p, graph, terminal, place, finite, deadline)
}

impl ScaledCandidate {
    pub(crate) fn separate_place(
        &self,
        p: &Problem,
        graph: &impl Graph,
        terminal: usize,
        place: usize,
        finite: &[Option<BigInt>],
        deadline: Instant,
    ) -> Separation {
        if Instant::now() >= deadline
            || terminal >= graph.mode_count()
            || graph.initial() >= graph.mode_count()
            || place >= p.places.len()
            || p.initial.len() != p.places.len()
            || graph.edges().len().checked_add(p.places.len()) != Some(self.values.len())
        {
            return Separation::Unknown;
        }
        let mut demands = vec![BigInt::zero(); graph.mode_count()];
        demands[graph.initial()] += &self.scale * p.initial[place];
        demands[terminal] -= &self.values[graph.edges().len() + place];
        let mut edges = vec![];
        for (e, edge) in graph.edges().iter().enumerate() {
            if Instant::now() >= deadline
                || edge.source >= graph.mode_count()
                || edge.target >= graph.mode_count()
                || edge.transition >= p.transitions.len()
            {
                return Separation::Unknown;
            }
            let (lower, upper) = bounds(p, graph, e, place, finite);
            demands[edge.source] -= &lower * &self.values[e];
            demands[edge.target] += (&lower + effect(p, edge.transition, place)) * &self.values[e];
            edges.push(flow::Edge {
                source: edge.source,
                target: edge.target,
                capacity: upper.map(|u| (u - lower) * &self.values[e]),
            });
        }
        match flow::separate(graph.mode_count(), &edges, &demands, deadline) {
            flow::Answer::Feasible => Separation::Feasible,
            flow::Answer::Cut(modes) => {
                let cut = Cut { place, modes };
                let Ok(row) = bounded_cut_row(p, graph, terminal, &cut, finite) else {
                    return Separation::Unknown;
                };
                let lhs: BigInt = row
                    .coefficients
                    .iter()
                    .map(|(i, a)| &self.values[*i] * a)
                    .sum();
                if lhs < row.bound * &self.scale {
                    Separation::Cut(cut)
                } else {
                    Separation::Unknown
                }
            }
            flow::Answer::Unknown => Separation::Unknown,
        }
    }
}

pub fn verify_certificate(p: &Problem, value: &serde_json::Value) -> Result<()> {
    let proof: Certificate = serde_json::from_value(value.clone())?;
    ensure!(proof.kind == "token-cut-v1", "wrong proof kind");
    let graph = control::build(p, &proof.controls, 8192)?;
    ensure!(
        proof.terminals.len() == graph.mode_count(),
        "terminal coverage mismatch"
    );
    for (q, terminal) in proof.terminals.iter().enumerate() {
        let mut system = master(p, &graph, q)?;
        for cut in &terminal.cuts {
            system.rows.push(cut_row(p, &graph, q, cut)?);
        }
        system.check(&terminal.multipliers)?;
    }
    Ok(())
}

pub fn verify_bounded_certificate(p: &Problem, value: &serde_json::Value) -> Result<()> {
    let proof: BoundedCertificate = serde_json::from_value(value.clone())?;
    ensure!(proof.kind == "bounded-token-cut-v1", "wrong proof kind");
    let finite = place_bounds::check(p, &proof.bounds)?;
    let graph = control::build(p, &proof.controls, 8192)?;
    ensure!(
        proof.terminals.len() == graph.mode_count(),
        "terminal coverage mismatch"
    );
    for (q, terminal) in proof.terminals.iter().enumerate() {
        let mut system = master(p, &graph, q)?;
        for cut in &terminal.cuts {
            system
                .rows
                .push(bounded_cut_row(p, &graph, q, cut, &finite)?);
        }
        system.check(&terminal.multipliers)?;
    }
    Ok(())
}

/// Reconstruct every finite mode and every cut from the original net.
pub fn verify_finite_certificate(p: &Problem, value: &serde_json::Value) -> Result<()> {
    let proof: BoundedCertificate = serde_json::from_value(value.clone())?;
    ensure!(proof.kind == "finite-token-cut-v1", "wrong proof kind");
    let finite = place_bounds::check(p, &proof.bounds)?;
    let graph = finite_control::build(p, &proof.controls, &finite, None)?;
    ensure!(
        proof.terminals.len() == graph.mode_count(),
        "terminal coverage mismatch"
    );
    for (q, terminal) in proof.terminals.iter().enumerate() {
        let mut system = master(p, &graph, q)?;
        for cut in &terminal.cuts {
            system
                .rows
                .push(bounded_cut_row(p, &graph, q, cut, &finite)?);
        }
        system.check(&terminal.multipliers)?;
    }
    Ok(())
}

/// Bounded-counter refinement is incomplete; every definitive answer is checked.
pub fn solve_finite(p: &Problem, timeout: Duration) -> Outcome {
    let start = Instant::now();
    let deadline = start + timeout;
    let mut out = Outcome::unknown("finite-token-cut", "finite projection budget exhausted", 0);
    if timeout.is_zero() || p.validate().is_err() {
        return out;
    }
    if p.accepts(&p.initial).unwrap_or(false) {
        out.verdict = "reachable";
        out.marking = Some(p.initial.clone());
        out.reason = "initial marking satisfies target".into();
        return out;
    }
    let discovery_deadline = start + timeout / 5;
    let mut seeds = crate::capacity::target_places(std::slice::from_ref(&p.target));
    for place in 0..p.places.len() {
        if seeds.len() == 64 {
            break;
        }
        if !seeds.contains(&place) {
            seeds.push(place);
        }
    }
    let mut proof =
        crate::capacity::discover(p, "", &seeds, start + timeout / 10, 2_000_000).certificate();
    proof
        .potentials
        .extend(place_bounds::discover(p, discovery_deadline).potentials);
    let Ok(finite) = place_bounds::check(p, &proof) else {
        return out;
    };
    let selections = selections(p, &finite, deadline);
    let rounds = selections.len();
    let mut attempts = 0;
    for (round, controls) in selections.into_iter().enumerate() {
        if Instant::now() >= deadline {
            break;
        }
        let remaining = deadline.saturating_duration_since(Instant::now());
        let round_deadline = (Instant::now() + remaining / (rounds - round) as u32).min(deadline);
        let graph = match finite_control::build(p, &controls, &finite, Some(round_deadline)) {
            Ok(graph) => graph,
            Err(error) => {
                out.reason = error.to_string();
                continue;
            }
        };
        attempts += 1;
        let (next, terminals) = solve_graph(p, &graph, &finite, round_deadline, out);
        out = next;
        if out.verdict == "reachable" {
            return out;
        }
        if let Some(terminals) = terminals {
            let certificate = serde_json::to_value(BoundedCertificate {
                kind: "finite-token-cut-v1".into(),
                controls,
                bounds: proof,
                terminals,
            })
            .unwrap();
            if verify_finite_certificate(p, &certificate).is_ok() {
                out.verdict = "unreachable";
                out.proof = Some(certificate);
            }
            return out;
        }
    }
    out.reason = format!("{attempts} finite projections; {}", out.reason);
    out
}

pub(crate) fn selections(
    p: &Problem,
    finite: &[Option<BigInt>],
    deadline: Instant,
) -> Vec<Vec<usize>> {
    const MAX_SELECTED: usize = 16;
    const MAX_CANDIDATES: usize = 4096;
    let fallback = || vec![vec![]];
    let mut work = 2_000_000usize;
    let mut take = |count| {
        if Instant::now() >= deadline {
            return false;
        }
        if let Some(next) = work.checked_sub(count) {
            work = next;
            true
        } else {
            false
        }
    };
    if !take(p.places.len()) {
        return fallback();
    }
    let mut target = vec![false; p.places.len()];
    for constraint in &p.target {
        for (i, &coefficient) in constraint.coefficients.iter().enumerate() {
            if !take(1) {
                return fallback();
            }
            target[i] |= coefficient != 0;
        }
    }
    let mut adjacent = target.clone();
    for t in &p.transitions {
        if !take(
            t.pre
                .len()
                .saturating_add(t.post.len())
                .saturating_mul(2)
                .saturating_add(1),
        ) {
            return fallback();
        }
        if t.pre.iter().chain(&t.post).any(|&(i, _)| target[i]) {
            for &(i, _) in t.pre.iter().chain(&t.post) {
                adjacent[i] = true;
            }
        }
    }
    let mut candidates = std::collections::BinaryHeap::new();
    for (i, bound) in finite.iter().enumerate() {
        if !take(1) {
            break;
        }
        let Some(width) = bound
            .as_ref()
            .and_then(ToPrimitive::to_usize)
            .and_then(|n| n.checked_add(1))
        else {
            continue;
        };
        if width > finite_control::MAX_MODES {
            continue;
        }
        candidates.push((width == 1, !target[i], !adjacent[i], width, i));
        if candidates.len() > MAX_CANDIDATES {
            candidates.pop();
        }
    }
    if !take(candidates.len().saturating_mul(12)) {
        return fallback();
    }
    let candidates = candidates.into_sorted_vec();
    let mut result = fallback();
    for limit in [16, 256, finite_control::MAX_MODES] {
        let mut selected = vec![];
        let mut product = 1usize;
        for &(_, _, _, width, place) in &candidates {
            if !take(1) || selected.len() == MAX_SELECTED {
                break;
            }
            let Some(next) = product.checked_mul(width).filter(|&n| n <= limit) else {
                continue;
            };
            product = next;
            selected.push(place);
            selected.sort_unstable();
            if selected.len().is_power_of_two() && !result.contains(&selected) {
                result.push(selected.clone());
            }
        }
        if !result.contains(&selected) {
            result.push(selected);
        }
    }
    result
}

pub(crate) fn witness(
    p: &Problem,
    graph: &impl Graph,
    values: &[Q],
    deadline: Instant,
    states: &mut usize,
) -> Option<Vec<usize>> {
    let mut counts = vec![0u64; p.transitions.len()];
    for (e, edge) in graph.edges().iter().enumerate() {
        if !values[e].is_integer() {
            return None;
        }
        counts[edge.transition] =
            counts[edge.transition].checked_add(values[e].to_integer().to_u64()?)?;
    }
    if counts.iter().try_fold(0u64, |a, &b| a.checked_add(b))? > 8192 {
        return None;
    }
    if let Realization::Witness(trace) = realize(p, &counts, deadline, 200_000, states)
        && p.check_witness(&trace).is_ok()
    {
        return Some(trace);
    }
    None
}

pub fn solve(p: &Problem, timeout: Duration) -> Outcome {
    solve_with_bounds(p, timeout, false)
}

pub fn solve_bounded(p: &Problem, timeout: Duration) -> Outcome {
    solve_with_bounds(p, timeout, true)
}

fn solve_with_bounds(p: &Problem, timeout: Duration, bounded: bool) -> Outcome {
    let deadline = Instant::now() + timeout;
    let mut out = Outcome::unknown(
        if bounded {
            "bounded-token-cut"
        } else {
            "token-cut"
        },
        "no certified control abstraction",
        0,
    );
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
    let bound_proof = if bounded {
        place_bounds::discover(p, (Instant::now() + timeout / 5).min(deadline))
    } else {
        place_bounds::Certificate::default()
    };
    let Ok(finite) = place_bounds::check(p, &bound_proof) else {
        return out;
    };
    let (mut out, terminals) = solve_graph(p, &graph, &finite, deadline, out);
    if let Some(terminals) = terminals {
        let proof = if bounded {
            serde_json::to_value(BoundedCertificate {
                kind: "bounded-token-cut-v1".into(),
                controls: graph.places().to_vec(),
                bounds: bound_proof,
                terminals,
            })
            .unwrap()
        } else {
            serde_json::to_value(Certificate {
                kind: "token-cut-v1".into(),
                controls: graph.places().to_vec(),
                terminals,
            })
            .unwrap()
        };
        let checked = if bounded {
            verify_bounded_certificate(p, &proof)
        } else {
            verify_certificate(p, &proof)
        };
        if checked.is_ok() {
            out.verdict = "unreachable";
            out.proof = Some(proof);
        }
    }
    out
}

fn solve_graph(
    p: &Problem,
    graph: &impl Graph,
    finite: &[Option<BigInt>],
    deadline: Instant,
    mut out: Outcome,
) -> (Outcome, Option<Vec<Terminal>>) {
    let mut terminals = vec![];
    let mut cached_cuts = vec![];
    let mut total_cuts = 0;
    let mut models = 0;
    for q in 0..graph.mode_count() {
        if Instant::now() >= deadline {
            break;
        }
        let remaining = deadline.saturating_duration_since(Instant::now());
        let terminal_deadline = Instant::now() + remaining / (graph.mode_count() - q) as u32;
        let Ok(mut system) = master(p, graph, q) else {
            break;
        };
        let mut cuts = cached_cuts.clone();
        for cut in &cuts {
            if Instant::now() >= deadline {
                out.reason = "flow-cut reconstruction deadline exhausted".into();
                return (out, None);
            }
            let Ok(row) = bounded_cut_row(p, graph, q, cut, finite) else {
                out.reason = "invalid cached flow cut".into();
                return (out, None);
            };
            system.rows.push(row);
        }
        let mut multipliers = None;
        for _ in 0..128 {
            if Instant::now() >= terminal_deadline {
                break;
            }
            let remaining = terminal_deadline.saturating_duration_since(Instant::now());
            if let Some(proof) = system.refute(Instant::now() + remaining / 2) {
                multipliers = Some(proof);
                break;
            }
            let Some(values) = system.rational_model(terminal_deadline) else {
                break;
            };
            models += 1;
            let mut added = false;
            let candidate = scaled(&values, terminal_deadline);
            for i in 0..p.places.len() {
                let Some(candidate) = &candidate else {
                    break;
                };
                if let Separation::Cut(cut) =
                    candidate.separate_place(p, graph, q, i, finite, terminal_deadline)
                {
                    let Ok(row) = bounded_cut_row(p, graph, q, &cut, finite) else {
                        break;
                    };
                    system.rows.push(row);
                    cached_cuts.push(cut.clone());
                    cuts.push(cut);
                    added = true;
                    total_cuts += 1;
                }
                if Instant::now() >= terminal_deadline {
                    break;
                }
            }
            if !added {
                if let Some(trace) = witness(p, graph, &values, terminal_deadline, &mut out.states)
                {
                    out.verdict = "reachable";
                    out.marking = p.check_witness(&trace).ok();
                    out.trace = trace;
                    out.reason = "flow-guided counts realized and replayed".into();
                    return (out, None);
                }
                break;
            }
        }
        terminals.push(multipliers.map(|multipliers| Terminal { cuts, multipliers }));
    }
    out.reason = format!(
        "{} of {} terminal modes refuted; {total_cuts} flow cuts, {models} exact models",
        terminals.iter().filter(|p| p.is_some()).count(),
        graph.mode_count()
    );
    let complete = terminals.len() == graph.mode_count() && terminals.iter().all(Option::is_some);
    (
        out,
        complete.then(|| terminals.into_iter().flatten().collect()),
    )
}

#[cfg(test)]
mod scaling_tests {
    use super::*;
    use crate::control::Control;
    use crate::model::Transition;

    fn deadline() -> Instant {
        Instant::now() + Duration::from_secs(5)
    }

    #[test]
    fn finite_selection_limits_zero_bound_width_and_deadline() {
        let p = Problem {
            places: vec![String::new(); 100],
            initial: vec![0; 100],
            transitions: vec![],
            target: vec![],
        };
        let finite = vec![Some(BigInt::zero()); 100];
        let selected = selections(&p, &finite, deadline());
        assert_eq!(selected.last().unwrap().len(), 16);
        assert!(
            selected
                .iter()
                .all(|s| s.len() <= 16 && s.windows(2).all(|w| w[0] < w[1]))
        );
        assert_eq!(
            selections(&p, &finite, Instant::now()),
            vec![Vec::<usize>::new()]
        );
        let finite = vec![Some(BigInt::from(3)); 100];
        let selected = selections(&p, &finite, deadline());
        assert!(
            selected
                .iter()
                .all(|s| 4usize.pow(s.len() as u32) <= finite_control::MAX_MODES)
        );
    }

    #[test]
    fn finite_selection_keeps_varying_controls_before_zero_bound_targets() {
        let p = Problem {
            places: (0..18).map(|i| format!("p{i}")).collect(),
            initial: vec![0; 18],
            transitions: vec![],
            target: vec![crate::model::Constraint {
                coefficients: (0..18).map(|i| i64::from(i < 16)).collect(),
                bound: 0,
                equality: true,
            }],
        };
        let mut finite = vec![Some(BigInt::zero()); 16];
        finite.extend([Some(1.into()), Some(1.into())]);
        let selected = selections(&p, &finite, deadline());
        assert_eq!(selected[1], vec![16]);
        assert_eq!(selected[2], vec![16, 17]);
        assert!(selected.last().unwrap().contains(&16));
        assert!(selected.last().unwrap().contains(&17));
        assert!(selected.iter().any(|s| s.contains(&0)));
    }

    fn fixture() -> (Problem, Control) {
        let p = Problem {
            places: ["a", "b", "x", "y"].map(String::from).to_vec(),
            initial: vec![1, 0, 2, 0],
            transitions: vec![
                Transition {
                    name: "advance".into(),
                    pre: vec![(0, 1), (3, 2)],
                    post: vec![(1, 1), (3, 2)],
                },
                Transition {
                    name: "return".into(),
                    pre: vec![(1, 1), (2, 1)],
                    post: vec![(0, 1), (3, 1)],
                },
            ],
            target: vec![],
        };
        let graph = control::build(&p, &[0, 1], 100).unwrap();
        (p, graph)
    }

    #[test]
    fn shared_scaling_matches_standalone_rational_separation() {
        let (p, graph) = fixture();
        let mut feasible = 0;
        let mut cuts = 0;
        for denominator in [2, 3, 7] {
            for numerator in 0..=2 * denominator {
                for terminal in 0..graph.mode_count() {
                    let returns = Q::new(numerator.into(), denominator.into());
                    let counts: Vec<_> = graph
                        .edges
                        .iter()
                        .map(|edge| {
                            &returns
                                + Q::from_integer(if edge.transition == 0 {
                                    terminal.into()
                                } else {
                                    0.into()
                                })
                        })
                        .collect();
                    let mut values = counts.clone();
                    for place in 0..p.places.len() {
                        let mut final_value = Q::from_integer(p.initial[place].into());
                        for (edge, count) in graph.edges().iter().zip(&counts) {
                            final_value += count * effect(&p, edge.transition, place);
                        }
                        values.push(final_value);
                    }
                    let shared = scaled(&values, deadline()).unwrap();
                    for finite in [vec![], vec![None, None, Some(2.into()), Some(2.into())]] {
                        for place in 0..p.places.len() {
                            let answer = shared.separate_place(
                                &p,
                                &graph,
                                terminal,
                                place,
                                &finite,
                                deadline(),
                            );
                            assert_eq!(
                                answer,
                                separate_bounded_place(
                                    &p,
                                    &graph,
                                    terminal,
                                    place,
                                    &values,
                                    &finite,
                                    deadline()
                                )
                            );
                            match answer {
                                Separation::Feasible => feasible += 1,
                                Separation::Cut(cut) => {
                                    cuts += 1;
                                    let row = bounded_cut_row(&p, &graph, terminal, &cut, &finite)
                                        .unwrap();
                                    let lhs: Q =
                                        row.coefficients.iter().map(|(i, a)| &values[*i] * a).sum();
                                    assert!(lhs < Q::from_integer(row.bound));
                                }
                                Separation::Unknown => panic!("valid rational candidate rejected"),
                            }
                        }
                    }
                }
            }
        }
        assert!(feasible > 0 && cuts > 0);
    }

    #[test]
    fn shared_scaling_preserves_invalid_input_and_deadline_results() {
        let (p, graph) = fixture();
        let values: Vec<Q> = [0, 0, 1, 0, 2, 0]
            .into_iter()
            .map(|n| Q::from_integer(n.into()))
            .collect();
        let shared = scaled(&values, deadline()).unwrap();
        for (terminal, place, limit) in [
            (2, 0, deadline()),
            (0, 4, deadline()),
            (0, 0, Instant::now()),
        ] {
            assert_eq!(
                shared.separate_place(&p, &graph, terminal, place, &[], limit),
                Separation::Unknown
            );
            assert_eq!(
                separate_bounded_place(&p, &graph, terminal, place, &values, &[], limit),
                Separation::Unknown
            );
        }
        let short = &values[..1];
        assert_eq!(
            scaled(short, deadline())
                .unwrap()
                .separate_place(&p, &graph, 0, 0, &[], deadline()),
            Separation::Unknown
        );
        assert_eq!(
            separate_bounded_place(&p, &graph, 0, 0, short, &[], deadline()),
            Separation::Unknown
        );
        let mut wrong_marking = values.clone();
        wrong_marking[4] += Q::one();
        assert_eq!(
            scaled(&wrong_marking, deadline()).unwrap().separate_place(
                &p,
                &graph,
                0,
                2,
                &[],
                deadline()
            ),
            Separation::Unknown
        );
        assert_eq!(
            separate_bounded_place(&p, &graph, 0, 2, &wrong_marking, &[], deadline()),
            Separation::Unknown
        );
        let mut negative = values;
        negative[0] = Q::new((-1).into(), 2.into());
        assert!(scaled(&negative, deadline()).is_none());
        assert_eq!(
            separate_bounded_place(&p, &graph, 0, 0, &negative, &[], deadline()),
            Separation::Unknown
        );
        assert!(scaled(&[], Instant::now()).is_none());
    }

    #[test]
    fn scaling_checks_lcm_size_without_limiting_numerators() {
        let denominator = BigInt::one() << 4095_u32;
        let values = [
            Q::new(BigInt::one(), denominator.clone()),
            Q::new(1.into(), 2.into()),
        ];
        let candidate = scaled(&values, deadline()).unwrap();
        assert_eq!(candidate.scale, denominator);
        assert_eq!(candidate.values[0], BigInt::one());
        assert!(
            scaled(
                &[Q::new(BigInt::one(), BigInt::one() << 4096_u32)],
                deadline()
            )
            .is_none()
        );
        let half = BigInt::one() << 2048_u32;
        assert!(
            scaled(
                &[Q::new(1.into(), half.clone()), Q::new(1.into(), half + 1)],
                deadline()
            )
            .is_none()
        );
        let huge = BigInt::one() << 10_000_u32;
        assert_eq!(
            scaled(&[Q::from_integer(huge.clone())], deadline())
                .unwrap()
                .values,
            vec![huge]
        );
    }
}
