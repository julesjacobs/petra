//! Finite token-flow cuts with implicit self-loop columns. Restricted
//! infeasibility becomes a proof only after pricing every original self-loop.
use crate::{
    control::Edge,
    counts_master::CountsMaster,
    finite_control::{self, FiniteControl, Graph},
    linear::System,
    model::Problem,
    place_bounds,
    search::Outcome,
    token_cut::{self, BoundedCertificate, Cut, Separation, Terminal},
};
use anyhow::{Context, Result, ensure};
use num_bigint::BigInt;
use num_rational::BigRational as Q;
use num_traits::{Signed, Zero};
use std::{
    collections::HashSet,
    time::{Duration, Instant},
};

const KIND: &str = "lazy-finite-token-cut-v1";
const METHOD: &str = "lazy-finite-token-cut";
const PRICE_BATCH: usize = 64;
const MAX_ACTIVE_STUTTERS: usize = 8192;

fn check_time(deadline: Option<Instant>) -> Result<()> {
    ensure!(
        deadline.is_none_or(|d| Instant::now() < d),
        "lazy token-cut deadline exhausted"
    );
    Ok(())
}

struct Stutter {
    transition: usize,
    pre: Vec<(usize, u64)>,
}

struct Stutters {
    transitions: Vec<Stutter>,
    count: usize,
}

impl Stutters {
    fn new(p: &Problem, graph: &FiniteControl, deadline: Option<Instant>) -> Result<Self> {
        ensure!(
            graph
                .modes
                .len()
                .checked_mul(p.transitions.len())
                .is_some_and(|n| n <= finite_control::MAX_IMPLICIT_VISITS),
            "finite control visit limit exhausted"
        );
        let mut coordinate = vec![None; p.places.len()];
        for (i, &place) in graph.places.iter().enumerate() {
            coordinate[place] = Some(i);
        }
        let mut transitions = vec![];
        for (transition, tr) in p.transitions.iter().enumerate() {
            check_time(deadline)?;
            let project = |arcs: &[(usize, u64)]| -> Vec<(usize, u64)> {
                let mut result: Vec<_> = arcs
                    .iter()
                    .filter_map(|&(p, w)| coordinate[p].map(|i| (i, w)))
                    .collect();
                result.sort_unstable();
                result
            };
            let pre = project(&tr.pre);
            if pre == project(&tr.post) {
                transitions.push(Stutter { transition, pre });
            }
        }
        let mut count = 0;
        for mode in &graph.modes {
            for stutter in &transitions {
                check_time(deadline)?;
                count += usize::from(stutter.enabled(mode));
            }
        }
        Ok(Self { transitions, count })
    }

    /// Returns a bounded batch of strictly positive omitted columns. An empty
    /// batch certifies that the entire implicit family satisfies Farkas' sign.
    fn price(
        &self,
        p: &Problem,
        graph: &FiniteControl,
        cuts: &[Cut],
        weights: &[Q],
        active: &HashSet<(usize, usize)>,
        deadline: Option<Instant>,
    ) -> Result<Vec<Edge>> {
        let cut_start = weights
            .len()
            .checked_sub(cuts.len())
            .context("missing cut rows")?;
        let mut base = vec![Q::zero(); p.places.len()];
        for (i, weight) in base.iter_mut().enumerate() {
            check_time(deadline)?;
            *weight = &weights[2 * i] - &weights[2 * i + 1];
        }
        let mut added = vec![];
        for (q, mode) in graph.modes.iter().enumerate() {
            check_time(deadline)?;
            let mut local = base.clone();
            for (j, cut) in cuts.iter().enumerate() {
                check_time(deadline)?;
                if cut.modes.binary_search(&q).is_ok() {
                    local[cut.place] -= &weights[cut_start + j];
                }
            }
            for stutter in &self.transitions {
                check_time(deadline)?;
                if active.contains(&(q, stutter.transition)) || !stutter.enabled(mode) {
                    continue;
                }
                let tr = &p.transitions[stutter.transition];
                let mut score = Q::zero();
                for &(i, w) in &tr.post {
                    check_time(deadline)?;
                    score += &local[i] * BigInt::from(w);
                }
                for &(i, w) in &tr.pre {
                    check_time(deadline)?;
                    score -= &local[i] * BigInt::from(w);
                }
                if score.is_positive() {
                    added.push(Edge {
                        source: q,
                        target: q,
                        transition: stutter.transition,
                    });
                    if added.len() == PRICE_BATCH {
                        return Ok(added);
                    }
                }
            }
        }
        check_time(deadline)?;
        Ok(added)
    }
}

impl Stutter {
    fn enabled(&self, mode: &[u64]) -> bool {
        self.pre.iter().all(|&(i, w)| mode[i] >= w)
    }
}

fn master(
    p: &Problem,
    graph: &FiniteControl,
    terminal: usize,
    cuts: &[Cut],
    finite: &[Option<BigInt>],
    deadline: Option<Instant>,
) -> Result<System> {
    let mut system = token_cut::master_with_deadline(p, graph, terminal, deadline)?;
    for cut in cuts {
        check_time(deadline)?;
        system.rows.push(token_cut::bounded_cut_row_with_deadline(
            p, graph, terminal, cut, finite, deadline,
        )?);
    }
    check_time(deadline)?;
    Ok(system)
}

/// Checks explicit and marking columns and the RHS before pricing implicit
/// columns. Row positions are independent of the active column set.
fn checked_weights(
    system: &System,
    multipliers: &[(usize, String)],
    deadline: Option<Instant>,
) -> Result<Vec<Q>> {
    let mut weights = vec![Q::zero(); system.rows.len()];
    let mut lhs = vec![Q::zero(); system.variables];
    let mut rhs = Q::zero();
    let mut previous = None;
    for (index, weight) in multipliers {
        check_time(deadline)?;
        ensure!(
            previous.is_none_or(|p| p < *index),
            "unordered or duplicate multiplier"
        );
        previous = Some(*index);
        let row = system.rows.get(*index).context("invalid Farkas row")?;
        let weight: Q = weight.parse()?;
        ensure!(weight.is_positive(), "nonpositive Farkas multiplier");
        for (variable, coefficient) in &row.coefficients {
            check_time(deadline)?;
            *lhs.get_mut(*variable).context("invalid variable")? += &weight * coefficient;
        }
        rhs += &weight * &row.bound;
        weights[*index] = weight;
    }
    ensure!(
        lhs.iter().all(|x| !x.is_positive()) && rhs.is_positive(),
        "invalid sparse Farkas contradiction"
    );
    check_time(deadline)?;
    Ok(weights)
}

pub fn verify_certificate(p: &Problem, value: &serde_json::Value) -> Result<()> {
    verify_with_deadline(p, value, None)
}

fn verify_with_deadline(
    p: &Problem,
    value: &serde_json::Value,
    deadline: Option<Instant>,
) -> Result<()> {
    check_time(deadline)?;
    let proof: BoundedCertificate = serde_json::from_value(value.clone())?;
    ensure!(proof.kind == KIND, "wrong proof kind");
    let finite = place_bounds::check(p, &proof.bounds)?;
    let graph = finite_control::build_without_stutters(p, &proof.controls, &finite, deadline)?;
    let stutters = Stutters::new(p, &graph, deadline)?;
    ensure!(
        proof.terminals.len() == graph.mode_count(),
        "terminal coverage mismatch"
    );
    for (q, terminal) in proof.terminals.iter().enumerate() {
        let system = master(p, &graph, q, &terminal.cuts, &finite, deadline)?;
        let weights = checked_weights(&system, &terminal.multipliers, deadline)?;
        ensure!(
            stutters
                .price(
                    p,
                    &graph,
                    &terminal.cuts,
                    &weights,
                    &HashSet::new(),
                    deadline
                )?
                .is_empty(),
            "implicit stutter invalidates Farkas contradiction"
        );
    }
    check_time(deadline)
}

#[derive(Default)]
struct Diagnostics {
    cuts: usize,
    models: usize,
    pricing_rounds: usize,
    model_attempts: usize,
    dimensions: (usize, usize, usize, usize),
    build: Duration,
    dual: Duration,
    pricing: Duration,
    primal: Duration,
    checking: Duration,
    separation: Duration,
    realization: Duration,
}

fn timed<T>(total: &mut Duration, run: impl FnOnce() -> T) -> T {
    let start = Instant::now();
    let result = run();
    *total += start.elapsed();
    result
}

fn solve_graph(
    p: &Problem,
    mut graph: FiniteControl,
    finite: &[Option<BigInt>],
    deadline: Instant,
    mut out: Outcome,
) -> (Outcome, Option<Vec<Terminal>>) {
    let stutters = match Stutters::new(p, &graph, Some(deadline)) {
        Ok(stutters) => stutters,
        Err(error) => {
            out.reason = error.to_string();
            return (out, None);
        }
    };
    let fixed = graph.edges.len();
    let mut active = HashSet::new();
    let mut terminals = vec![];
    let mut cached_cuts = vec![];
    let mut stats = Diagnostics::default();
    let mut reason = "relaxation did not yield a replayable witness".to_string();
    for q in 0..graph.mode_count() {
        if Instant::now() >= deadline {
            reason = "deadline exhausted".into();
            break;
        }
        let now = Instant::now();
        let terminal_deadline =
            now + deadline.saturating_duration_since(now) / (graph.mode_count() - q) as u32;
        let mut cuts = cached_cuts.clone();
        let attempt = (|| -> Result<Option<Terminal>> {
            for _ in 0..128 {
                check_time(Some(terminal_deadline))?;
                let (system, reduced) = timed(&mut stats.build, || -> Result<_> {
                    let system = master(p, &graph, q, &cuts, finite, Some(terminal_deadline))?;
                    let reduced = CountsMaster::new(&system, p.places.len(), terminal_deadline)?;
                    Ok((system, reduced))
                })?;
                stats.dimensions = (
                    system.variables,
                    system.rows.len(),
                    reduced.system.variables,
                    reduced.system.rows.len(),
                );
                let remaining = terminal_deadline.saturating_duration_since(Instant::now());
                let proposal = timed(&mut stats.dual, || {
                    reduced.system.refute(Instant::now() + remaining / 2)
                });
                if let Some(proposal) = proposal {
                    let (multipliers, weights) = timed(&mut stats.checking, || -> Result<_> {
                        let multipliers = reduced.lift(&proposal, terminal_deadline)?;
                        let weights =
                            checked_weights(&system, &multipliers, Some(terminal_deadline))?;
                        Ok((multipliers, weights))
                    })?;
                    stats.pricing_rounds += 1;
                    let added = timed(&mut stats.pricing, || {
                        stutters.price(p, &graph, &cuts, &weights, &active, Some(terminal_deadline))
                    })?;
                    if added.is_empty() {
                        return Ok(Some(Terminal { cuts, multipliers }));
                    }
                    ensure!(
                        active.len() + added.len() <= MAX_ACTIVE_STUTTERS,
                        "active stutter limit exhausted"
                    );
                    for edge in added {
                        active.insert((edge.source, edge.transition));
                        graph.edges.push(edge);
                    }
                    continue;
                }
                stats.model_attempts += 1;
                let counts = timed(&mut stats.primal, || {
                    reduced
                        .system
                        .rational_model_with_objective(&reduced.objective, terminal_deadline)
                })?;
                let values = timed(&mut stats.checking, || {
                    reduced.reconstruct(&system, &counts, terminal_deadline)
                })?;
                stats.models += 1;
                let candidate = token_cut::scaled(&values, terminal_deadline)
                    .context("candidate scaling exhausted")?;
                let mut added = false;
                for i in 0..p.places.len() {
                    check_time(Some(terminal_deadline))?;
                    if let Separation::Cut(cut) = timed(&mut stats.separation, || {
                        candidate.separate_place(p, &graph, q, i, finite, terminal_deadline)
                    }) && !cuts.contains(&cut)
                    {
                        cached_cuts.push(cut.clone());
                        cuts.push(cut);
                        stats.cuts += 1;
                        added = true;
                    }
                }
                if !added {
                    if let Some(trace) = timed(&mut stats.realization, || {
                        token_cut::witness(p, &graph, &values, terminal_deadline, &mut out.states)
                    }) {
                        check_time(Some(terminal_deadline))?;
                        out.verdict = "reachable";
                        out.marking = p.check_witness(&trace).ok();
                        out.trace = trace;
                        reason = "flow-guided counts realized and replayed".into();
                    }
                    return Ok(None);
                }
            }
            anyhow::bail!("column/cut round limit exhausted")
        })();
        match attempt {
            Ok(terminal) => terminals.push(terminal),
            Err(error) => {
                reason = format!("{error:#}");
                terminals.push(None);
            }
        }
        if out.verdict == "reachable" {
            break;
        }
    }
    let complete = terminals.len() == graph.mode_count() && terminals.iter().all(Option::is_some);
    if complete {
        reason = "all terminal modes refuted".into();
    }
    out.reason = format!(
        "{} of {} terminal modes refuted; {} fixed edges, {} active of {} implicit stutters; {} pricing rounds, {} cuts, {} exact models from {} primal attempts; last master {} vars/{} rows -> {} vars/{} rows; phase ms build={} dual={} pricing={} primal={} checking={} separation={} realization={}; {reason}",
        terminals.iter().filter(|t| t.is_some()).count(),
        graph.mode_count(),
        fixed,
        active.len(),
        stutters.count,
        stats.pricing_rounds,
        stats.cuts,
        stats.models,
        stats.model_attempts,
        stats.dimensions.0,
        stats.dimensions.1,
        stats.dimensions.2,
        stats.dimensions.3,
        stats.build.as_millis(),
        stats.dual.as_millis(),
        stats.pricing.as_millis(),
        stats.primal.as_millis(),
        stats.checking.as_millis(),
        stats.separation.as_millis(),
        stats.realization.as_millis(),
    );
    (
        out,
        complete.then(|| terminals.into_iter().flatten().collect()),
    )
}

pub fn solve(p: &Problem, timeout: Duration) -> Outcome {
    let start = Instant::now();
    let deadline = start + timeout;
    let mut out = Outcome::unknown(METHOD, "finite projection budget exhausted", 0);
    if timeout.is_zero() || p.validate().is_err() {
        return out;
    }
    if p.accepts(&p.initial).unwrap_or(false) {
        out.verdict = "reachable";
        out.marking = Some(p.initial.clone());
        out.reason = "initial marking satisfies target".into();
        return out;
    }
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
        .extend(place_bounds::discover(p, start + timeout / 5).potentials);
    let finite = match place_bounds::check(p, &proof) {
        Ok(finite) => finite,
        Err(error) => {
            out.reason = error.to_string();
            return out;
        }
    };
    let selections = token_cut::selections(p, &finite, deadline);
    let rounds = selections.len();
    let mut attempts = 0;
    for (round, controls) in selections.into_iter().enumerate() {
        let now = Instant::now();
        if now >= deadline {
            break;
        }
        let round_deadline =
            now + deadline.saturating_duration_since(now) / (rounds - round) as u32;
        let graph = match finite_control::build_without_stutters(
            p,
            &controls,
            &finite,
            Some(round_deadline),
        ) {
            Ok(graph) => graph,
            Err(error) => {
                out.reason = error.to_string();
                continue;
            }
        };
        attempts += 1;
        let (next, terminals) = solve_graph(p, graph, &finite, round_deadline, out);
        out = next;
        if out.verdict == "reachable" {
            return out;
        }
        if let Some(terminals) = terminals {
            let certificate = serde_json::to_value(BoundedCertificate {
                kind: KIND.into(),
                controls,
                bounds: proof,
                terminals,
            })
            .unwrap();
            match verify_with_deadline(p, &certificate, Some(deadline)) {
                Ok(()) => {
                    out.verdict = "unreachable";
                    out.proof = Some(certificate);
                }
                Err(error) => {
                    out.reason = format!("{}; final check: {error}", out.reason);
                }
            }
            return out;
        }
    }
    out.reason = format!("{attempts} finite projections; {}", out.reason);
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Constraint, Transition};
    use std::collections::BTreeSet;

    fn deadline() -> Instant {
        Instant::now() + Duration::from_secs(5)
    }

    fn cycle() -> Problem {
        serde_json::from_value(serde_json::json!({
            "places":["c","d","x","y"], "initial":[2,0,2,0],
            "transitions":[
                {"name":"convert-at-c","pre":[[0,2],[2,2]],"post":[[0,2],[3,2]]},
                {"name":"advance","pre":[[0,2],[3,2]],"post":[[0,1],[1,1],[3,2]]},
                {"name":"advance-again","pre":[[0,1],[1,1],[3,2]],"post":[[1,2],[3,2]]},
                {"name":"convert-at-d","pre":[[1,2],[3,2]],"post":[[1,2],[2,2]]},
                {"name":"return","pre":[[1,2],[2,2]],"post":[[0,2],[2,2]]}],
            "target":[{"coefficients":[1,0,0,0],"bound":1,"equality":false},
                {"coefficients":[0,1,0,0],"bound":1,"equality":false},
                {"coefficients":[0,0,1,0],"bound":2,"equality":false}]
        }))
        .unwrap()
    }

    fn bounds() -> place_bounds::Certificate {
        place_bounds::Certificate {
            potentials: vec![
                place_bounds::Potential {
                    weights: vec![(0, "1".into()), (1, "1".into())],
                },
                place_bounds::Potential {
                    weights: vec![(2, "1".into()), (3, "1".into())],
                },
            ],
            ..Default::default()
        }
    }

    #[test]
    fn pricing_matches_explicit_columns_for_every_row_and_cut() {
        let p = cycle();
        let finite = place_bounds::check(&p, &bounds()).unwrap();
        for controls in [vec![], vec![0], vec![0, 1], vec![2], vec![0, 2]] {
            let full = finite_control::build(&p, &controls, &finite, None).unwrap();
            let graph =
                finite_control::build_without_stutters(&p, &controls, &finite, None).unwrap();
            assert_eq!(full.modes, graph.modes);
            let stutters = Stutters::new(&p, &graph, None).unwrap();
            assert_eq!(stutters.count + graph.edges.len(), full.edges.len());
            let modes = graph.mode_count();
            let cuts: Vec<_> = (0..p.places.len())
                .flat_map(|place| {
                    (0..1usize << modes).map(move |mask| Cut {
                        place,
                        modes: (0..modes).filter(|q| mask & (1 << q) != 0).collect(),
                    })
                })
                .collect();
            for q in 0..graph.mode_count() {
                let explicit = master(&p, &full, q, &cuts, &finite, None).unwrap();
                let restricted = master(&p, &graph, q, &cuts, &finite, None).unwrap();
                assert_eq!(explicit.rows.len(), restricted.rows.len());
                for (row, base) in explicit.rows.iter().zip(&restricted.rows) {
                    assert_eq!(row.bound, base.bound);
                }
                for r in 0..explicit.rows.len() + 1 {
                    let weights: Vec<_> = (0..explicit.rows.len())
                        .map(|i| {
                            if r == explicit.rows.len() {
                                Q::from_integer((i % 7).into()) / BigInt::from(3)
                            } else {
                                Q::from_integer(u64::from(i == r).into())
                            }
                        })
                        .collect();
                    let expected: BTreeSet<_> = full
                        .edges
                        .iter()
                        .enumerate()
                        .filter(|(_, e)| e.source == e.target)
                        .filter(|(e, _)| {
                            explicit
                                .rows
                                .iter()
                                .zip(&weights)
                                .map(|(row, weight)| {
                                    row.coefficients
                                        .iter()
                                        .filter(|(i, _)| i == e)
                                        .map(|(_, a)| weight * a)
                                        .sum::<Q>()
                                })
                                .sum::<Q>()
                                .is_positive()
                        })
                        .map(|(_, e)| (e.source, e.transition))
                        .collect();
                    let actual: BTreeSet<_> = stutters
                        .price(&p, &graph, &cuts, &weights, &HashSet::new(), None)
                        .unwrap()
                        .into_iter()
                        .map(|e| (e.source, e.transition))
                        .collect();
                    assert_eq!(
                        actual, expected,
                        "controls={controls:?}, terminal={q}, row={r}"
                    );
                }
            }
        }
    }

    #[test]
    fn missing_stutter_invalidates_restricted_negative_and_is_priced_for_witness() {
        let p = Problem {
            places: vec!["x".into()],
            initial: vec![0],
            transitions: vec![Transition {
                name: "produce".into(),
                pre: vec![],
                post: vec![(0, 1)],
            }],
            target: vec![Constraint {
                coefficients: vec![1],
                bound: 1,
                equality: false,
            }],
        };
        let graph = finite_control::build_without_stutters(&p, &[], &[], None).unwrap();
        let system = master(&p, &graph, 0, &[], &[], None).unwrap();
        let multipliers = system.refute(deadline()).unwrap();
        system.check(&multipliers).unwrap();
        let bad = serde_json::to_value(BoundedCertificate {
            kind: KIND.into(),
            controls: vec![],
            bounds: Default::default(),
            terminals: vec![Terminal {
                cuts: vec![],
                multipliers,
            }],
        })
        .unwrap();
        assert!(
            verify_certificate(&p, &bad)
                .unwrap_err()
                .to_string()
                .contains("implicit stutter")
        );
        let out = solve(&p, Duration::from_secs(5));
        assert_eq!(out.verdict, "reachable", "{}", out.reason);
        assert_eq!(out.trace, vec![0]);
        p.check_witness(&out.trace).unwrap();
    }

    #[test]
    fn lazy_and_explicit_proofs_are_interchangeable_on_bounded_cycle() {
        let p = cycle();
        let finite = place_bounds::check(&p, &bounds()).unwrap();
        let graph = finite_control::build_without_stutters(&p, &[0, 1], &finite, None).unwrap();
        let (out, terminals) = solve_graph(
            &p,
            graph,
            &finite,
            deadline(),
            Outcome::unknown(METHOD, "", 0),
        );
        let terminals = terminals.unwrap_or_else(|| panic!("{}", out.reason));
        assert!(terminals.iter().any(|t| !t.cuts.is_empty()));
        let mut proof = serde_json::to_value(BoundedCertificate {
            kind: KIND.into(),
            controls: vec![0, 1],
            bounds: bounds(),
            terminals,
        })
        .unwrap();
        verify_certificate(&p, &proof).unwrap();
        proof["kind"] = serde_json::json!("finite-token-cut-v1");
        token_cut::verify_finite_certificate(&p, &proof).unwrap();
        let old = token_cut::solve_finite(&p, Duration::from_secs(5));
        assert_eq!(old.verdict, "unreachable", "{}", old.reason);
        let mut old_proof = old.proof.unwrap();
        old_proof["kind"] = serde_json::json!(KIND);
        verify_certificate(&p, &old_proof).unwrap();
    }

    #[test]
    fn zero_count_unbounded_mode_changing_edge_stays_in_separator() {
        let p: Problem = serde_json::from_value(serde_json::json!({
            "places":["before","after","x","y"],"initial":[1,0,0,0],
            "transitions":[
                {"name":"consume","pre":[[0,1],[2,1]],"post":[[0,1],[3,1]]},
                {"name":"switch","pre":[[0,1]],"post":[[1,1]]},
                {"name":"produce","pre":[[1,1]],"post":[[1,1],[2,1]]},
                {"name":"return","pre":[[1,1]],"post":[[0,1]]}], "target":[]
        }))
        .unwrap();
        let finite = vec![Some(1.into()), Some(1.into()), None, None];
        let mut graph = finite_control::build_without_stutters(&p, &[0, 1], &finite, None).unwrap();
        assert_eq!(graph.edges.len(), 2);
        assert!(graph.edges.iter().any(|e| e.transition == 3));
        graph.edges.extend([
            Edge {
                source: 0,
                target: 0,
                transition: 0,
            },
            Edge {
                source: 1,
                target: 1,
                transition: 2,
            },
        ]);
        let values: Vec<_> = graph
            .edges
            .iter()
            .map(|e| Q::from_integer(u64::from(e.transition != 3).into()))
            .chain([0, 1, 0, 1].map(|n| Q::from_integer(n.into())))
            .collect();
        assert_eq!(
            token_cut::separate_bounded_place(&p, &graph, 1, 2, &values, &finite, deadline()),
            Separation::Feasible
        );
        let removed = graph.edges.iter().position(|e| e.transition == 3).unwrap();
        graph.edges.remove(removed);
        let mut pruned = values;
        assert!(pruned.remove(removed).is_zero());
        assert!(matches!(
            token_cut::separate_bounded_place(&p, &graph, 1, 2, &pruned, &finite, deadline()),
            Separation::Cut(_)
        ));
    }

    #[test]
    fn disabled_stutters_and_selected_guards_are_reconstructed() {
        let p: Problem = serde_json::from_value(serde_json::json!({
            "places":["c","x"],"initial":[0,0],
            "transitions":[{"name":"disabled","pre":[[0,1]],"post":[[1,1],[0,1]]}],
            "target":[{"coefficients":[0,1],"bound":1,"equality":false}]
        }))
        .unwrap();
        let proof = place_bounds::Certificate {
            potentials: vec![place_bounds::Potential {
                weights: vec![(0, "1".into())],
            }],
            ..Default::default()
        };
        let finite = place_bounds::check(&p, &proof).unwrap();
        let graph = finite_control::build_without_stutters(&p, &[0], &finite, None).unwrap();
        assert_eq!(Stutters::new(&p, &graph, None).unwrap().count, 0);
        let (out, terminals) = solve_graph(
            &p,
            graph,
            &finite,
            deadline(),
            Outcome::unknown(METHOD, "", 0),
        );
        let terminals = terminals.unwrap_or_else(|| panic!("{}", out.reason));
        let proof = serde_json::to_value(BoundedCertificate {
            kind: KIND.into(),
            controls: vec![0],
            bounds: proof,
            terminals,
        })
        .unwrap();
        verify_certificate(&p, &proof).unwrap();
        let mut changed = p;
        changed.transitions[0].pre.clear();
        changed.transitions[0].post = vec![(1, 1)];
        assert!(verify_certificate(&changed, &proof).is_err());
    }

    #[test]
    fn graph_cap_counts_mode_changing_edges_and_deadline_never_accepts_a_prefix() {
        let mut p = cycle();
        p.transitions = (0..finite_control::MAX_EDGES + 1)
            .map(|i| Transition {
                name: i.to_string(),
                pre: vec![(0, 2)],
                post: vec![(0, 2)],
            })
            .collect();
        let finite = place_bounds::check(&p, &bounds()).unwrap();
        assert!(finite_control::build(&p, &[0], &finite, None).is_err());
        let graph = finite_control::build_without_stutters(&p, &[0], &finite, None).unwrap();
        assert_eq!(graph.mode_count(), 1);
        assert!(graph.edges.is_empty());
        assert_eq!(
            Stutters::new(&p, &graph, None).unwrap().count,
            finite_control::MAX_EDGES + 1
        );
        assert!(
            finite_control::build_without_stutters(&p, &[0], &finite, Some(Instant::now()))
                .is_err()
        );
        assert!(Stutters::new(&p, &graph, Some(Instant::now())).is_err());
        assert_eq!(solve(&p, Duration::ZERO).verdict, "unknown");
    }
}
