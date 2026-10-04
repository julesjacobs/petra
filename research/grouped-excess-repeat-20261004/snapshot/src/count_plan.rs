//! Integer firing-count candidates coupled to support and exact execution.
use crate::{
    complete_arithmetic::{self, Answer, Limits, System},
    model::Problem,
    search::Outcome,
};
use num_bigint::BigInt;
use num_traits::{One, ToPrimitive, Zero};
use std::{
    collections::{HashSet, VecDeque},
    time::{Duration, Instant},
};

// Bound coefficient slots before allocation; max_rows alone does not bound width.
const MAX_DENSE_ENTRIES: usize = 1 << 20;

fn characteristic_entries(
    places: usize,
    transitions: usize,
    targets: usize,
    inequalities: usize,
) -> Option<usize> {
    let rows = places.checked_add(targets)?.checked_add(1)?;
    let columns = transitions
        .checked_add(places)?
        .checked_add(inequalities)?
        .checked_add(1)?;
    places
        .checked_mul(transitions)?
        .checked_add(rows.checked_mul(columns.checked_add(1)?)?)
}

fn refinement_fits(
    system: &System,
    pending: &[System],
    extra_rows: usize,
    extra_columns: usize,
    copies: usize,
) -> bool {
    let entries = |s: &System| s.a.len().checked_mul(s.variables.checked_add(1)?);
    let estimate = || -> Option<usize> {
        let current = pending
            .iter()
            .try_fold(entries(system)?, |sum, s| sum.checked_add(entries(s)?))?;
        let rows = system.a.len().checked_add(extra_rows)?;
        let columns = system
            .variables
            .checked_add(extra_columns)?
            .checked_add(1)?;
        current.checked_add(rows.checked_mul(columns)?.checked_mul(copies)?)
    };
    estimate().is_some_and(|n| n <= MAX_DENSE_ENTRIES)
}

fn equation(s: &mut System, mut row: Vec<BigInt>, rhs: BigInt, slack: i32) {
    row.resize(s.variables, BigInt::zero());
    if slack != 0 {
        for a in &mut s.a {
            a.push(BigInt::zero());
        }
        row.push(slack.into());
        s.variables += 1;
    }
    s.a.push(row);
    s.b.push(rhs);
}

fn characteristic(p: &Problem, cap: u64) -> System {
    let n = p.transitions.len();
    let mut effect = vec![vec![BigInt::zero(); n]; p.places.len()];
    for (t, tr) in p.transitions.iter().enumerate() {
        for &(q, w) in &tr.pre {
            effect[q][t] -= BigInt::from(w);
        }
        for &(q, w) in &tr.post {
            effect[q][t] += BigInt::from(w);
        }
    }
    let mut s = System {
        variables: n,
        a: vec![],
        b: vec![],
    };
    for (q, row) in effect.iter().enumerate() {
        equation(&mut s, row.clone(), -BigInt::from(p.initial[q]), -1);
    }
    for c in &p.target {
        let row = (0..n)
            .map(|t| {
                c.coefficients
                    .iter()
                    .zip(&effect)
                    .map(|(&a, e)| BigInt::from(a) * &e[t])
                    .sum()
            })
            .collect();
        let rhs = BigInt::from(c.bound)
            - c.coefficients
                .iter()
                .zip(&p.initial)
                .map(|(&a, &x)| BigInt::from(a) * BigInt::from(x))
                .sum::<BigInt>();
        equation(&mut s, row, rhs, if c.equality { 0 } else { -1 });
    }
    equation(&mut s, vec![BigInt::one(); n], cap.into(), 1);
    s
}

fn support_failure(p: &Problem, marking: &[u64], counts: &[u64], reverse: bool) -> Option<usize> {
    let mut marked: Vec<_> = marking.iter().map(|&x| x != 0).collect();
    let mut fired = vec![false; counts.len()];
    loop {
        let mut changed = false;
        for (t, tr) in p.transitions.iter().enumerate() {
            if counts[t] == 0 || fired[t] {
                continue;
            }
            let (pre, post) = if reverse {
                (&tr.post, &tr.pre)
            } else {
                (&tr.pre, &tr.post)
            };
            if pre.iter().all(|&(q, _)| marked[q]) {
                fired[t] = true;
                for &(q, _) in post {
                    marked[q] = true;
                }
                changed = true;
            }
        }
        if !changed {
            break;
        }
    }
    counts
        .iter()
        .enumerate()
        .find_map(|(t, &x)| (x != 0 && !fired[t]).then_some(t))
}

fn support(p: &Problem, marking: &[u64], counts: &[u64], reverse: bool) -> bool {
    support_failure(p, marking, counts, reverse).is_none()
}

fn refine_support(s: &System, counts: &[u64], blocked: usize, stack: &mut Vec<System>) {
    let mut omit = s.clone();
    let mut row = vec![BigInt::zero(); counts.len()];
    row[blocked] = BigInt::one();
    equation(&mut omit, row, BigInt::zero(), 0);
    stack.push(omit);
    let mut expand = s.clone();
    let row = counts
        .iter()
        .map(|&x| {
            if x == 0 {
                BigInt::one()
            } else {
                BigInt::zero()
            }
        })
        .collect();
    equation(&mut expand, row, BigInt::one(), -1);
    stack.push(expand);
}

fn endpoint(p: &Problem, counts: &[u64]) -> Option<Vec<u64>> {
    let mut m: Vec<BigInt> = p.initial.iter().copied().map(BigInt::from).collect();
    for (tr, &count) in p.transitions.iter().zip(counts) {
        for &(q, w) in &tr.pre {
            m[q] -= BigInt::from(w) * BigInt::from(count);
        }
        for &(q, w) in &tr.post {
            m[q] += BigInt::from(w) * BigInt::from(count);
        }
    }
    m.iter().map(ToPrimitive::to_u64).collect()
}

pub(crate) enum Realization {
    Witness(Vec<usize>),
    Impossible,
    Limited,
}
struct Frame {
    marking: Vec<u64>,
    remaining: Vec<u64>,
    next: usize,
}
pub(crate) fn realize(
    p: &Problem,
    counts: &[u64],
    deadline: Instant,
    max_states: usize,
    states: &mut usize,
) -> Realization {
    let mut stack = vec![Frame {
        marking: p.initial.clone(),
        remaining: counts.to_vec(),
        next: 0,
    }];
    let mut trace = vec![];
    // A remaining-count vector fixes the marking through the state equation.
    let mut dead = HashSet::new();
    while let Some(frame) = stack.last_mut() {
        if Instant::now() >= deadline || *states >= max_states {
            return Realization::Limited;
        }
        if frame.remaining.iter().all(|&x| x == 0) {
            return Realization::Witness(trace);
        }
        if frame.next == counts.len() {
            dead.insert(frame.remaining.clone());
            stack.pop();
            trace.pop();
            continue;
        }
        let t = frame.next;
        frame.next += 1;
        if frame.remaining[t] == 0 {
            continue;
        }
        let mut remaining = frame.remaining.clone();
        remaining[t] -= 1;
        if dead.contains(&remaining) {
            continue;
        }
        let marking = match p.fire(&frame.marking, t) {
            Ok(Some(m)) => m,
            Ok(None) => continue,
            Err(_) => return Realization::Limited,
        };
        *states += 1;
        trace.push(t);
        stack.push(Frame {
            marking,
            remaining,
            next: 0,
        });
    }
    Realization::Impossible
}

struct AcyclicOrder(Vec<usize>);

fn acyclic_order(p: &Problem, deadline: Instant) -> Option<AcyclicOrder> {
    let transitions = p.transitions.len();
    let vertices = transitions.checked_add(p.places.len())?;
    let mut entries = vertices.checked_mul(3)?;
    if Instant::now() >= deadline || entries > MAX_DENSE_ENTRIES {
        return None;
    }
    for transition in &p.transitions {
        if Instant::now() >= deadline {
            return None;
        }
        entries = entries
            .checked_add(transition.pre.len())?
            .checked_add(transition.post.len())?;
        if entries > MAX_DENSE_ENTRIES {
            return None;
        }
    }
    // Place vertices avoid materializing every producer/consumer pair.
    let mut successors = vec![Vec::new(); vertices];
    let mut incoming = vec![0usize; vertices];
    for (t, transition) in p.transitions.iter().enumerate() {
        if Instant::now() >= deadline {
            return None;
        }
        for &(place, _) in &transition.pre {
            successors[transitions + place].push(t);
            incoming[t] += 1;
        }
        for &(place, _) in &transition.post {
            successors[t].push(transitions + place);
            incoming[transitions + place] += 1;
        }
    }
    let mut pending: VecDeque<_> = incoming
        .iter()
        .enumerate()
        .filter_map(|(i, &count)| (count == 0).then_some(i))
        .collect();
    let mut visited = 0;
    let mut order = Vec::with_capacity(transitions);
    while let Some(vertex) = pending.pop_front() {
        if Instant::now() >= deadline {
            return None;
        }
        visited += 1;
        if vertex < transitions {
            order.push(vertex);
        }
        for &successor in &successors[vertex] {
            incoming[successor] -= 1;
            if incoming[successor] == 0 {
                pending.push_back(successor);
            }
        }
    }
    (visited == vertices).then_some(AcyclicOrder(order))
}

fn realize_acyclic(
    p: &Problem,
    counts: &[u64],
    order: &AcyclicOrder,
    deadline: Instant,
    max_states: usize,
    states: &mut usize,
) -> Option<Realization> {
    if Instant::now() >= deadline || *states >= max_states {
        return Some(Realization::Limited);
    }
    let total = counts.iter().try_fold(0usize, |sum, &count| {
        sum.checked_add(count.try_into().ok()?)
    })?;
    // The existing realizer checks its budget before accepting the final frame.
    if total >= max_states - *states {
        return None;
    }
    let mut marking = p.initial.clone();
    for &t in &order.0 {
        if Instant::now() >= deadline {
            return Some(Realization::Limited);
        }
        let count = u128::from(counts[t]);
        if count == 0 {
            continue;
        }
        let transition = &p.transitions[t];
        for &(place, weight) in &transition.pre {
            let consumed = u128::from(weight) * count;
            if consumed > u128::from(marking[place]) {
                return None;
            }
            marking[place] -= u64::try_from(consumed).ok()?;
        }
        for &(place, weight) in &transition.post {
            let produced = u128::from(weight) * count;
            marking[place] = u64::try_from(u128::from(marking[place]) + produced).ok()?;
        }
    }
    let mut trace = Vec::new();
    if trace.try_reserve_exact(total).is_err() {
        return Some(Realization::Limited);
    }
    for &t in &order.0 {
        let mut left = usize::try_from(counts[t]).ok()?;
        while left != 0 {
            if Instant::now() >= deadline {
                return Some(Realization::Limited);
            }
            let block = left.min(2048);
            trace.resize(trace.len() + block, t);
            *states += block;
            left -= block;
        }
    }
    Some(Realization::Witness(trace))
}

fn exclude(s: &System, counts: &[u64], stack: &mut Vec<System>, cap: usize) {
    let mut prefix = s.clone();
    for (j, &value) in counts.iter().enumerate() {
        if stack.len() >= cap {
            return;
        }
        let mut unit = vec![BigInt::zero(); counts.len()];
        unit[j] = BigInt::one();
        if value != 0 {
            let mut lower = prefix.clone();
            equation(&mut lower, unit.clone(), BigInt::from(value - 1), 1);
            stack.push(lower);
        }
        let mut upper = prefix.clone();
        equation(&mut upper, unit.clone(), BigInt::from(value) + 1, -1);
        stack.push(upper);
        equation(&mut prefix, unit, value.into(), 0);
    }
}

pub fn solve(p: &Problem, timeout: Duration, max_states: usize, max_rows: usize) -> Outcome {
    let method = "count-plan";
    let deadline = Instant::now() + timeout;
    let mut states = 0;
    let mut candidates = 0;
    let mut last_reason = "candidate budget exhausted";
    if p.validate().is_err() {
        return Outcome::unknown(method, "invalid problem", 0);
    }
    if timeout.is_zero() || max_states == 0 {
        return Outcome::unknown(method, "resource limit", 0);
    }
    if p.accepts(&p.initial).unwrap_or(false) {
        let mut out = Outcome::unknown(method, "replayed empty witness", 1);
        out.verdict = "reachable";
        out.marking = Some(p.initial.clone());
        return out;
    }
    let entries = characteristic_entries(
        p.places.len(),
        p.transitions.len(),
        p.target.len(),
        p.target.iter().filter(|c| !c.equality).count(),
    );
    if entries.is_none_or(|n| n > MAX_DENSE_ENTRIES)
        || p.places
            .len()
            .saturating_add(p.target.len())
            .saturating_add(1)
            > max_rows
    {
        return solve_sparse_until(p, deadline, max_states, states, 8192);
    }
    for cap in [8, 16, 32, 64, 128, 256, 512, 1024] {
        if Instant::now() >= deadline || states >= max_states {
            break;
        }
        let mut pending = vec![characteristic(p, cap)];
        for _ in 0..32 {
            let Some(system) = pending.pop() else {
                break;
            };
            let limits = Limits {
                deadline: Some(deadline),
                max_rows: Some(max_rows),
                max_nodes: Some(max_states.saturating_sub(states)),
            };
            let values = match complete_arithmetic::solve_integer(&system, &limits) {
                Answer::Feasible(v) => v,
                Answer::Infeasible => continue,
                Answer::Unknown(reason) => {
                    last_reason = reason;
                    break;
                }
            };
            candidates += 1;
            let Some(counts): Option<Vec<u64>> = values[..p.transitions.len()]
                .iter()
                .map(ToPrimitive::to_u64)
                .collect()
            else {
                last_reason = "candidate exceeds machine counters";
                break;
            };
            let Some(final_marking) = endpoint(p, &counts) else {
                last_reason = "candidate endpoint exceeds machine counters";
                break;
            };
            if let Some(blocked) = support_failure(p, &p.initial, &counts, false) {
                // Every execution using blocked must add a transition outside this
                // support: its input place cannot otherwise become marked.
                if pending.len() < 256 {
                    if !refinement_fits(&system, &pending, 1, 1, 2) {
                        drop(pending);
                        drop(system);
                        return solve_sparse_until(p, deadline, max_states, states, 8192);
                    }
                    refine_support(&system, &counts, blocked, &mut pending);
                }
                continue;
            }
            let possible = support(p, &final_marking, &counts, true);
            if possible {
                match realize(p, &counts, deadline, max_states, &mut states) {
                    Realization::Witness(trace) => {
                        if let Ok(marking) = p.check_witness(&trace) {
                            let mut out = Outcome::unknown(
                                method,
                                &format!("replayed witness after {candidates} integer candidates"),
                                states,
                            );
                            out.verdict = "reachable";
                            out.trace = trace;
                            out.marking = Some(marking);
                            return out;
                        }
                        return Outcome::unknown(method, "candidate replay failed", states);
                    }
                    Realization::Limited => {
                        return Outcome::unknown(method, "realization resource limit", states);
                    }
                    Realization::Impossible => {}
                }
            }
            // Exclusion keeps a growing prefix and up to two children per count.
            let children = counts.len().saturating_mul(2).min(257 - pending.len());
            if !refinement_fits(
                &system,
                &pending,
                counts.len().saturating_add(1),
                1,
                children + 2,
            ) {
                drop(pending);
                drop(system);
                return solve_sparse_until(p, deadline, max_states, states, 8192);
            }
            exclude(&system, &counts, &mut pending, 256);
        }
    }
    Outcome::unknown(
        method,
        &format!("{last_reason}; examined {candidates} integer candidates"),
        states,
    )
}

fn support_frontier(p: &Problem, counts: &[u64]) -> Vec<(usize, BigInt)> {
    let mut marked: Vec<_> = p.initial.iter().map(|&x| x != 0).collect();
    loop {
        let mut changed = false;
        for (t, transition) in p.transitions.iter().enumerate() {
            if counts[t] > 0 && transition.pre.iter().all(|&(i, _)| marked[i]) {
                for &(i, _) in &transition.post {
                    changed |= !marked[i];
                    marked[i] = true;
                }
            }
        }
        if !changed {
            break;
        }
    }
    p.transitions
        .iter()
        .enumerate()
        .filter(|(_, t)| {
            t.pre.iter().all(|&(i, _)| marked[i]) && t.post.iter().any(|&(i, _)| !marked[i])
        })
        .map(|(i, _)| (i, BigInt::one()))
        .collect()
}

pub fn solve_sparse(p: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    solve_sparse_with_cap(p, timeout, max_states, 8192)
}

pub fn solve_sparse_with_cap(
    p: &Problem,
    timeout: Duration,
    max_states: usize,
    cap: u32,
) -> Outcome {
    let deadline = Instant::now() + timeout;
    if p.validate().is_err()
        || timeout.is_zero()
        || max_states == 0
        || cap == 0
        || cap > i32::MAX as u32
    {
        return Outcome::unknown("sparse-count-plan", "invalid net or exhausted budget", 0);
    }
    solve_sparse_until(p, deadline, max_states, 0, cap)
}

/// Bound firing counts by the remaining budget of the expanded-trace realizer.
/// That realizer checks its state limit before accepting the final marking.
pub fn solve_sparse_with_state_budget(
    p: &Problem,
    timeout: Duration,
    max_states: usize,
) -> Outcome {
    let deadline = Instant::now() + timeout;
    if p.validate().is_err() || timeout.is_zero() || max_states == 0 {
        return Outcome::unknown("sparse-count-plan", "invalid net or exhausted budget", 0);
    }
    solve_sparse_policy(p, deadline, max_states, 0, CountCap::RemainingStates)
}

#[derive(Clone, Copy)]
enum CountCap {
    Fixed(u32),
    RemainingStates,
}

impl CountCap {
    fn limit(self, max_states: usize, states: usize) -> u32 {
        match self {
            Self::Fixed(cap) => cap,
            Self::RemainingStates => max_states
                .saturating_sub(states)
                .saturating_sub(1)
                .min(i32::MAX as usize) as u32,
        }
    }
}

fn solve_sparse_until(
    p: &Problem,
    deadline: Instant,
    max_states: usize,
    states: usize,
    cap: u32,
) -> Outcome {
    solve_sparse_policy(p, deadline, max_states, states, CountCap::Fixed(cap))
}

fn solve_sparse_policy(
    p: &Problem,
    deadline: Instant,
    max_states: usize,
    mut states: usize,
    cap: CountCap,
) -> Outcome {
    let method = "sparse-count-plan";
    if Instant::now() >= deadline || states >= max_states {
        return Outcome::unknown(method, "resource limit", states);
    }
    let mut stack = vec![crate::linear::state_equation(p)];
    let mut attempts = 0;
    let mut models = 0;
    let mut support_refinements = 0;
    let mut order = None;
    while let Some(system) = stack.pop() {
        if Instant::now() >= deadline || attempts >= 128 || states >= max_states {
            break;
        }
        attempts += 1;
        let remaining = deadline.saturating_duration_since(Instant::now());
        let Some(counts) = system.integer_model(
            Instant::now() + remaining / 2,
            cap.limit(max_states, states),
        ) else {
            continue;
        };
        models += 1;
        if let Some(blocked) = support_failure(p, &p.initial, &counts, false) {
            support_refinements += 1;
            let mut omit = system.clone();
            omit.rows.push(crate::linear::Row {
                coefficients: vec![(blocked, (-1).into())],
                bound: 0.into(),
            });
            stack.push(omit);
            let mut expand = system;
            expand.rows.push(crate::linear::Row {
                coefficients: support_frontier(p, &counts),
                bound: 1.into(),
            });
            stack.push(expand);
            continue;
        }
        let realized = order
            .get_or_insert_with(|| acyclic_order(p, deadline))
            .as_ref()
            .and_then(|order| realize_acyclic(p, &counts, order, deadline, max_states, &mut states))
            .unwrap_or_else(|| realize(p, &counts, deadline, max_states, &mut states));
        if let Realization::Witness(trace) = realized
            && let Ok(marking) = p.check_witness(&trace)
            && Instant::now() < deadline
        {
            let mut out = Outcome::unknown(
                method,
                "integer firing counts realized and replayed",
                states,
            );
            out.verdict = "reachable";
            out.marking = Some(marking);
            out.trace = trace;
            return out;
        }
    }
    Outcome::unknown(
        method,
        &format!(
            "{attempts} arithmetic attempts, {models} integer models, {support_refinements} support refinements; no replayed witness"
        ),
        states,
    )
}

#[cfg(test)]
#[path = "count_plan_acyclic_tests.rs"]
mod acyclic_tests;

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Constraint, Transition};
    type Arcs<'a> = &'a [(&'a [(usize, u64)], &'a [(usize, u64)])];
    fn sample(initial: Vec<u64>, arcs: Arcs<'_>, target: Vec<i64>, bound: i64) -> Problem {
        Problem {
            places: (0..initial.len()).map(|i| i.to_string()).collect(),
            initial,
            transitions: arcs
                .iter()
                .map(|(pre, post)| Transition {
                    name: "t".into(),
                    pre: pre.to_vec(),
                    post: post.to_vec(),
                })
                .collect(),
            target: vec![Constraint {
                coefficients: target,
                bound,
                equality: true,
            }],
        }
    }
    #[test]
    fn realizes_with_backtracking() {
        let p = sample(
            vec![1, 0],
            &[
                (&[(0, 1)], &[]),
                (&[(0, 1)], &[(1, 1)]),
                (&[(1, 1)], &[(0, 1)]),
            ],
            vec![1, 1],
            0,
        );
        let mut states = 0;
        let Realization::Witness(trace) = realize(
            &p,
            &[1, 1, 1],
            Instant::now() + Duration::from_secs(1),
            100,
            &mut states,
        ) else {
            panic!("missed ordering")
        };
        assert_eq!(trace, vec![1, 2, 0]);
        p.check_witness(&trace).unwrap();
    }
    #[test]
    fn reverse_support_retains_read_arcs() {
        let p = sample(vec![0, 0], &[(&[(0, 1)], &[(0, 1), (1, 1)])], vec![0, 1], 1);
        assert!(!support(&p, &[0, 1], &[1], true));
        assert!(!support(&p, &p.initial, &[1], false));
    }
    #[test]
    fn rejects_support_feasible_but_disabled_counts() {
        let p = sample(vec![1], &[(&[(0, 2)], &[(0, 3)])], vec![1], 2);
        assert!(support(&p, &p.initial, &[1], false));
        let mut states = 0;
        assert!(matches!(
            realize(
                &p,
                &[1],
                Instant::now() + Duration::from_secs(1),
                100,
                &mut states
            ),
            Realization::Impossible
        ));
    }
    #[test]
    fn signed_targets_and_witness() {
        let p = sample(vec![3, 0], &[(&[(0, 1)], &[(1, 1)])], vec![-1, 1], 1);
        let out = solve(&p, Duration::from_secs(2), 10000, 2000);
        assert_eq!(out.method, "count-plan");
        assert_eq!(out.verdict, "reachable", "{}", out.reason);
        p.check_witness(&out.trace).unwrap();
    }
    #[test]
    fn refines_spurious_minimal_counts() {
        let p = sample(
            vec![1, 0],
            &[(&[], &[(0, 1)]), (&[(0, 2)], &[(0, 2), (1, 1)])],
            vec![0, 1],
            1,
        );
        let out = solve(&p, Duration::from_secs(2), 10000, 2000);
        assert_eq!(out.verdict, "reachable", "{}", out.reason);
        p.check_witness(&out.trace).unwrap();
        assert!(out.trace.contains(&0));
    }
    #[test]
    fn support_cut_adds_missing_producer() {
        let p = sample(
            vec![0, 0],
            &[(&[], &[(0, 1)]), (&[(0, 1)], &[(0, 1), (1, 1)])],
            vec![0, 1],
            1,
        );
        assert_eq!(support_failure(&p, &p.initial, &[0, 1], false), Some(1));
        let out = solve(&p, Duration::from_secs(2), 10000, 2000);
        assert_eq!(out.verdict, "reachable", "{}", out.reason);
        p.check_witness(&out.trace).unwrap();
        assert!(out.trace.contains(&0));
    }
    #[test]
    fn resources_return_unknown() {
        let p = sample(vec![1], &[(&[(0, 1)], &[])], vec![1], 0);
        assert_eq!(solve(&p, Duration::ZERO, 100, 100).verdict, "unknown");
        assert_eq!(solve(&p, Duration::from_secs(1), 0, 100).verdict, "unknown");
    }

    fn sparse_large_problem() -> Problem {
        let places = 1100;
        let mut target = vec![0; places];
        target[places - 1] = 1;
        sample(vec![0; places], &[(&[], &[(places - 1, 1)])], target, 1)
    }

    #[test]
    fn dense_budget_routes_to_replayed_sparse_witness() {
        let p = sparse_large_problem();
        let out = solve(&p, Duration::from_secs(2), 100, 10000);
        assert_eq!(out.method, "sparse-count-plan");
        assert_eq!(out.verdict, "reachable", "{}", out.reason);
        assert_eq!(out.trace, vec![0]);
        p.check_witness(&out.trace).unwrap();
    }

    #[test]
    fn row_budget_routes_to_replayed_sparse_witness() {
        let p = sample(vec![0], &[(&[], &[(0, 1)])], vec![1], 1);
        let out = solve(&p, Duration::from_secs(2), 100, 1);
        assert_eq!(out.method, "sparse-count-plan");
        assert_eq!(out.verdict, "reachable", "{}", out.reason);
        p.check_witness(&out.trace).unwrap();
    }

    #[test]
    fn sparse_fallback_has_no_negative_authority() {
        let mut p = sparse_large_problem();
        p.transitions[0].pre = vec![(0, 1)];
        p.transitions[0].post.push((0, 1));
        let out = solve(&p, Duration::from_secs(2), 100, 10000);
        assert_eq!(out.method, "sparse-count-plan");
        assert_eq!(out.verdict, "unknown");
    }

    #[test]
    fn dense_budget_preserves_empty_witness() {
        let mut p = sparse_large_problem();
        p.initial[1099] = 1;
        let out = solve(&p, Duration::from_secs(2), 100, 0);
        assert_eq!(out.method, "count-plan");
        assert_eq!(out.verdict, "reachable");
        assert!(out.trace.is_empty());
        p.check_witness(&out.trace).unwrap();
    }

    #[test]
    fn sparse_fallback_preserves_consumed_resources() {
        let p = sample(vec![0], &[(&[], &[(0, 1)])], vec![1], 1);
        let out = solve_sparse_until(&p, Instant::now(), 100, 17, 8192);
        assert_eq!(out.verdict, "unknown");
        assert_eq!(out.states, 17);
        let out = solve_sparse_until(&p, Instant::now() + Duration::from_secs(1), 17, 17, 8192);
        assert_eq!(out.verdict, "unknown");
        assert_eq!(out.states, 17);
    }

    #[test]
    fn dense_estimate_overflow_requires_sparse_path() {
        assert_eq!(characteristic_entries(usize::MAX, 1, 1, 0), None);
        assert_eq!(characteristic_entries(1, usize::MAX, 1, 0), None);
        assert_eq!(characteristic_entries(1, 1, usize::MAX, 0), None);
        assert_eq!(characteristic_entries(1, 1, 1, usize::MAX), None);
    }

    #[test]
    fn exclusion_partitions_count_vectors() {
        let s = characteristic(
            &sample(vec![0], &[(&[], &[(0, 1)]), (&[], &[])], vec![1], 1),
            4,
        );
        let mut branches = vec![];
        exclude(&s, &[1, 0], &mut branches, 100);
        assert_eq!(branches.len(), 3);
        for branch in branches {
            if let Answer::Feasible(model) =
                complete_arithmetic::solve_integer(&branch, &Limits::default())
            {
                assert_ne!(&model[..2], &[BigInt::from(1), BigInt::from(0)]);
            }
        }
    }
}
