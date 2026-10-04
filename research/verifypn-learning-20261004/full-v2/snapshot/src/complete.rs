//! Kosaraju generalized-VASS decomposition, with exact terminating subprocedures.
use crate::{
    complete_arithmetic as arithmetic,
    complete_cover::{self, Arc},
    model::Problem,
    search::Outcome,
};
use arithmetic::{Answer, System};
use num_bigint::BigInt;
use num_traits::{One, Signed, ToPrimitive, Zero};
use std::{
    collections::{HashMap, HashSet, VecDeque},
    time::{Duration, Instant},
};

#[derive(Clone, Debug)]
pub struct Component {
    pub states: usize,
    pub arcs: Vec<Arc>,
    pub entry: usize,
    pub exit: usize,
    pub initial: Vec<Option<BigInt>>,
    pub final_marking: Vec<Option<BigInt>>,
    pub rigid: Vec<Option<BigInt>>,
}
#[derive(Clone, Debug)]
pub struct Sequence {
    pub components: Vec<Component>,
    pub bridges: Vec<Vec<BigInt>>,
}
#[derive(Clone, Debug, Default)]
pub struct Limits {
    pub deadline: Option<Instant>,
    pub max_nodes: Option<usize>,
    pub max_rows: Option<usize>,
}
#[derive(Clone, Debug, Default)]
pub struct Statistics {
    pub decompositions: usize,
    pub scc_refinements: usize,
    pub transition_refinements: usize,
    pub endpoint_refinements: usize,
    pub counter_refinements: usize,
    pub perfect_sequences: usize,
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Decision {
    Reachable,
    Unreachable,
    Unknown(String),
}
struct Context {
    limits: Limits,
    stats: Statistics,
    work: usize,
}
type Checked<T> = Result<T, String>;
impl Context {
    fn tick(&mut self) -> Checked<()> {
        if self.limits.deadline.is_some_and(|d| Instant::now() >= d) {
            return Err("decomposition time limit".into());
        }
        self.work = self.work.saturating_add(1);
        if self.limits.max_nodes.is_some_and(|n| self.work > n) {
            return Err("decomposition work limit".into());
        }
        Ok(())
    }
    fn arithmetic(&self) -> arithmetic::Limits {
        arithmetic::Limits {
            deadline: self.limits.deadline,
            max_nodes: self.limits.max_nodes,
            max_rows: self.limits.max_rows,
        }
    }
}
fn rank(c: &Component) -> (usize, usize, usize) {
    (
        c.rigid.iter().filter(|x| x.is_none()).count(),
        c.arcs.len(),
        c.initial
            .iter()
            .chain(&c.final_marking)
            .filter(|x| x.is_none())
            .count(),
    )
}
fn replacement(
    g: &Sequence,
    index: usize,
    parts: Vec<Component>,
    links: Vec<Vec<BigInt>>,
) -> Checked<Sequence> {
    if parts.is_empty() || links.len() + 1 != parts.len() {
        return Err("invalid replacement arity".into());
    }
    if parts.iter().any(|c| rank(c) >= rank(&g.components[index])) {
        return Err("non-decreasing refinement rank".into());
    }
    let mut components = g.components[..index].to_vec();
    components.extend(parts);
    components.extend_from_slice(&g.components[index + 1..]);
    let mut bridges = g.bridges[..index.min(g.bridges.len())].to_vec();
    bridges.extend(links);
    bridges.extend_from_slice(&g.bridges[index.min(g.bridges.len())..]);
    Ok(Sequence {
        components,
        bridges,
    })
}
fn validate(g: &Sequence) -> Checked<()> {
    if g.components.is_empty() || g.bridges.len() + 1 != g.components.len() {
        return Err("invalid GVASS sequence".into());
    }
    let d = g.components[0].initial.len();
    for c in &g.components {
        if c.initial.len() != d
            || c.final_marking.len() != d
            || c.rigid.len() != d
            || c.entry >= c.states
            || c.exit >= c.states
        {
            return Err("invalid component dimensions".into());
        }
        for value in c
            .initial
            .iter()
            .chain(&c.final_marking)
            .chain(&c.rigid)
            .flatten()
        {
            if value.is_negative() {
                return Err("negative endpoint".into());
            }
        }
        for (j, r) in c.rigid.iter().enumerate() {
            if let Some(r) = r
                && (c.initial[j].as_ref() != Some(r) || c.final_marking[j].as_ref() != Some(r))
            {
                return Err("inconsistent rigid endpoint".into());
            }
        }
        for arc in &c.arcs {
            if arc.source >= c.states
                || arc.target >= c.states
                || arc.effect.len() != d
                || c.rigid
                    .iter()
                    .enumerate()
                    .any(|(j, r)| r.is_some() && !arc.effect[j].is_zero())
            {
                return Err("invalid component arc".into());
            }
        }
    }
    if g.bridges.iter().any(|b| b.len() != d) {
        return Err("invalid bridge".into());
    }
    Ok(())
}
fn reachable_states(c: &Component, reverse: bool) -> HashSet<usize> {
    let mut seen = HashSet::new();
    let mut stack = vec![if reverse { c.exit } else { c.entry }];
    while let Some(q) = stack.pop() {
        if !seen.insert(q) {
            continue;
        }
        for e in &c.arcs {
            let (a, b) = if reverse {
                (e.target, e.source)
            } else {
                (e.source, e.target)
            };
            if a == q {
                stack.push(b);
            }
        }
    }
    seen
}
// Graph pruning and rigid normalization are equivalences, not refinement branches.
fn normalize(c: &mut Component) -> bool {
    let forward = reachable_states(c, false);
    if !forward.contains(&c.exit) {
        return false;
    }
    let backward = reachable_states(c, true);
    let mut keep: Vec<_> = forward.intersection(&backward).copied().collect();
    keep.sort_unstable();
    let map: HashMap<_, _> = keep.iter().enumerate().map(|(i, &q)| (q, i)).collect();
    c.arcs
        .retain(|e| map.contains_key(&e.source) && map.contains_key(&e.target));
    for e in &mut c.arcs {
        e.source = map[&e.source];
        e.target = map[&e.target];
    }
    c.entry = map[&c.entry];
    c.exit = map[&c.exit];
    c.states = keep.len();
    for j in 0..c.initial.len() {
        if c.arcs.iter().all(|e| e.effect[j].is_zero()) {
            if let (Some(a), Some(b)) = (&c.initial[j], &c.final_marking[j])
                && a != b
            {
                return false;
            }
            if let Some(value) = c.initial[j]
                .as_ref()
                .or(c.final_marking[j].as_ref())
                .cloned()
            {
                c.initial[j] = Some(value.clone());
                c.final_marking[j] = Some(value.clone());
                c.rigid[j] = Some(value);
            }
        }
    }
    true
}
fn sccs(c: &Component) -> Vec<usize> {
    // Iterative Kosaraju graph decomposition avoids a call stack proportional to states.
    let mut adj = vec![vec![]; c.states];
    let mut rev = vec![vec![]; c.states];
    for e in &c.arcs {
        adj[e.source].push(e.target);
        rev[e.target].push(e.source);
    }
    let mut seen = vec![false; c.states];
    let mut order = vec![];
    for q in 0..c.states {
        if seen[q] {
            continue;
        }
        let mut stack = vec![(q, false)];
        while let Some((q, done)) = stack.pop() {
            if done {
                order.push(q);
                continue;
            }
            if seen[q] {
                continue;
            }
            seen[q] = true;
            stack.push((q, true));
            for &r in &adj[q] {
                if !seen[r] {
                    stack.push((r, false));
                }
            }
        }
    }
    let mut ids = vec![usize::MAX; c.states];
    let mut next = 0;
    for &q in order.iter().rev() {
        if ids[q] != usize::MAX {
            continue;
        }
        let mut stack = vec![q];
        while let Some(q) = stack.pop() {
            if ids[q] != usize::MAX {
                continue;
            }
            ids[q] = next;
            stack.extend(&rev[q]);
        }
        next += 1;
    }
    ids
}
fn restricted(c: &Component, ids: &[usize], id: usize, entry: usize, exit: usize) -> Component {
    let states: Vec<_> = (0..c.states).filter(|&q| ids[q] == id).collect();
    let map: HashMap<_, _> = states.iter().enumerate().map(|(i, &q)| (q, i)).collect();
    let arcs = c
        .arcs
        .iter()
        .filter(|e| ids[e.source] == id && ids[e.target] == id)
        .map(|e| Arc {
            source: map[&e.source],
            target: map[&e.target],
            effect: e.effect.clone(),
        })
        .collect();
    Component {
        states: states.len(),
        arcs,
        entry: map[&entry],
        exit: map[&exit],
        initial: c.rigid.clone(),
        final_marking: c.rigid.clone(),
        rigid: c.rigid.clone(),
    }
}
fn split_scc(
    g: &Sequence,
    index: usize,
    ids: &[usize],
    ctx: &mut Context,
) -> Checked<Vec<Sequence>> {
    let c = &g.components[index];
    let destination = ids[c.exit];
    let mut paths = vec![(ids[c.entry], Vec::<usize>::new())];
    let mut out = vec![];
    while let Some((id, path)) = paths.pop() {
        ctx.tick()?;
        if id == destination {
            let mut parts = vec![];
            let mut links = vec![];
            let mut entry = c.entry;
            for &e in &path {
                let edge = &c.arcs[e];
                parts.push(restricted(c, ids, ids[entry], entry, edge.source));
                links.push(edge.effect.clone());
                entry = edge.target;
            }
            parts.push(restricted(c, ids, ids[entry], entry, c.exit));
            parts[0].initial = c.initial.clone();
            parts.last_mut().unwrap().final_marking = c.final_marking.clone();
            out.push(replacement(g, index, parts, links)?);
        } else {
            for (e, edge) in c.arcs.iter().enumerate() {
                if ids[edge.source] == id && ids[edge.target] != id {
                    let mut path = path.clone();
                    path.push(e);
                    paths.push((ids[edge.target], path));
                }
            }
        }
    }
    Ok(out)
}
#[derive(Clone, Debug)]
enum Variable {
    Initial(usize, usize),
    Final(usize, usize),
    Transition(usize, usize),
}
struct Characteristic {
    system: System,
    marked: Vec<(usize, Variable)>,
}
fn characteristic(g: &Sequence) -> Characteristic {
    let d = g.components[0].initial.len();
    let mut n = 0;
    let mut marked = vec![];
    let mut initial_vars = vec![];
    let mut final_vars = vec![];
    let mut arc_offsets = vec![];
    for (i, c) in g.components.iter().enumerate() {
        let mut initial = vec![None; d];
        let mut final_marking = vec![None; d];
        for j in 0..d {
            if c.initial[j].is_none() {
                initial[j] = Some(n);
                marked.push((n, Variable::Initial(i, j)));
                n += 1;
            }
            if c.final_marking[j].is_none() {
                final_marking[j] = Some(n);
                marked.push((n, Variable::Final(i, j)));
                n += 1;
            }
        }
        initial_vars.push(initial);
        final_vars.push(final_marking);
        arc_offsets.push(n);
        for e in 0..c.arcs.len() {
            marked.push((n, Variable::Transition(i, e)));
            n += 1;
        }
    }
    let mut system = System {
        variables: n,
        a: vec![],
        b: vec![],
    };
    let mut add = |terms: Vec<(usize, BigInt)>, b: BigInt| {
        let mut row = vec![BigInt::zero(); n];
        for (i, v) in terms {
            row[i] += v;
        }
        if !b.is_zero() || row.iter().any(|x| !x.is_zero()) {
            system.a.push(row);
            system.b.push(b);
        }
    };
    for (i, c) in g.components.iter().enumerate() {
        for j in 0..d {
            let mut terms = vec![];
            let mut rhs = BigInt::zero();
            if let Some(v) = final_vars[i][j] {
                terms.push((v, BigInt::one()));
            } else {
                rhs -= c.final_marking[j].as_ref().unwrap();
            }
            if let Some(v) = initial_vars[i][j] {
                terms.push((v, -BigInt::one()));
            } else {
                rhs += c.initial[j].as_ref().unwrap();
            }
            for (e, arc) in c.arcs.iter().enumerate() {
                if !arc.effect[j].is_zero() {
                    terms.push((arc_offsets[i] + e, -&arc.effect[j]));
                }
            }
            add(terms, rhs);
        }
        for q in 0..c.states {
            let mut terms = vec![];
            for (e, arc) in c.arcs.iter().enumerate() {
                if arc.source == q {
                    terms.push((arc_offsets[i] + e, BigInt::one()));
                }
                if arc.target == q {
                    terms.push((arc_offsets[i] + e, -BigInt::one()));
                }
            }
            add(
                terms,
                BigInt::from(i32::from(q == c.entry) - i32::from(q == c.exit)),
            );
        }
        if i + 1 < g.components.len() {
            for j in 0..d {
                let mut terms = vec![];
                let mut rhs = g.bridges[i][j].clone();
                if let Some(v) = initial_vars[i + 1][j] {
                    terms.push((v, BigInt::one()));
                } else {
                    rhs -= g.components[i + 1].initial[j].as_ref().unwrap();
                }
                if let Some(v) = final_vars[i][j] {
                    terms.push((v, -BigInt::one()));
                } else {
                    rhs += c.final_marking[j].as_ref().unwrap();
                }
                add(terms, rhs);
            }
        }
    }
    Characteristic { system, marked }
}
fn bounded_maximum(system: &System, variable: usize, ctx: &mut Context) -> Checked<BigInt> {
    let mut lower = vec![BigInt::zero(); system.variables];
    let upper = vec![None; system.variables];
    let mut low = BigInt::zero();
    let mut high = BigInt::one();
    loop {
        ctx.tick()?;
        lower[variable] = high.clone();
        match arithmetic::solve_rational(system, &lower, &upper, &ctx.arithmetic()) {
            Answer::Infeasible => break,
            Answer::Feasible(_) => {
                low = high.clone();
                high *= 2;
            }
            Answer::Unknown(s) => return Err(s.into()),
        }
    }
    while &high - &low > BigInt::one() {
        ctx.tick()?;
        let mid: BigInt = (&low + &high) / 2;
        lower[variable] = mid.clone();
        match arithmetic::solve_rational(system, &lower, &upper, &ctx.arithmetic()) {
            Answer::Infeasible => high = mid,
            Answer::Feasible(_) => low = mid,
            Answer::Unknown(s) => return Err(s.into()),
        }
    }
    Ok(low)
}
fn bounded_transition(
    g: &Sequence,
    index: usize,
    edge: usize,
    bound: &BigInt,
    ctx: &mut Context,
) -> Checked<Vec<Sequence>> {
    let c = &g.components[index];
    let removed = &c.arcs[edge];
    let mut base = c.clone();
    base.arcs.remove(edge);
    base.initial = c.rigid.clone();
    base.final_marking = c.rigid.clone();
    let mut out = vec![];
    let mut count = BigInt::zero();
    while &count <= bound {
        ctx.tick()?;
        let m = count
            .to_usize()
            .ok_or("transition unfolding exceeds address space")?;
        let mut parts = Vec::new();
        let mut links = Vec::new();
        for segment in 0..=m {
            ctx.tick()?;
            let mut part = base.clone();
            part.entry = if segment == 0 {
                c.entry
            } else {
                removed.target
            };
            part.exit = if segment == m { c.exit } else { removed.source };
            if segment == 0 {
                part.initial = c.initial.clone();
            }
            if segment == m {
                part.final_marking = c.final_marking.clone();
            }
            parts.push(part);
            if segment < m {
                links.push(removed.effect.clone());
            }
        }
        out.push(replacement(g, index, parts, links)?);
        count += 1;
    }
    Ok(out)
}
fn constrain_endpoint(
    g: &Sequence,
    index: usize,
    j: usize,
    initial: bool,
    bound: &BigInt,
    ctx: &mut Context,
) -> Checked<Vec<Sequence>> {
    let mut out = vec![];
    let mut value = BigInt::zero();
    while &value <= bound {
        ctx.tick()?;
        let mut part = g.components[index].clone();
        if initial {
            part.initial[j] = Some(value.clone());
        } else {
            part.final_marking[j] = Some(value.clone());
        }
        out.push(replacement(g, index, vec![part], vec![])?);
        value += 1;
    }
    Ok(out)
}
fn bound_counter(
    g: &Sequence,
    index: usize,
    j: usize,
    bound: &BigInt,
    ctx: &mut Context,
) -> Checked<Option<Sequence>> {
    let c = &g.components[index];
    let a = c.initial[j].as_ref().ok_or("missing bounded entry")?;
    let b = c.final_marking[j].as_ref().ok_or("missing bounded exit")?;
    if a > bound || b > bound {
        return Ok(None);
    }
    let size = (bound + BigInt::one())
        .to_usize()
        .ok_or("counter unfolding exceeds address space")?;
    let states = c
        .states
        .checked_mul(size)
        .ok_or("counter unfolding state capacity")?;
    if ctx.limits.max_nodes.is_some_and(|n| states > n) {
        return Err("counter unfolding state limit".into());
    }
    let mut part = c.clone();
    part.states = states;
    part.entry = c.entry * size + a.to_usize().ok_or("entry capacity")?;
    part.exit = c.exit * size + b.to_usize().ok_or("exit capacity")?;
    part.arcs.clear();
    for e in &c.arcs {
        for value in 0..size {
            ctx.tick()?;
            let next = BigInt::from(value) + &e.effect[j];
            if next.is_negative() || &next > bound {
                continue;
            }
            let mut effect = e.effect.clone();
            effect[j] = BigInt::zero();
            part.arcs.push(Arc {
                source: e.source * size + value,
                target: e.target * size + next.to_usize().ok_or("counter capacity")?,
                effect,
            });
        }
    }
    part.rigid[j] = Some(a.clone());
    part.initial[j] = Some(a.clone());
    part.final_marking[j] = Some(a.clone());
    let mut tail = Component {
        states: 1,
        arcs: vec![],
        entry: 0,
        exit: 0,
        initial: c.final_marking.clone(),
        final_marking: c.final_marking.clone(),
        rigid: c.rigid.clone(),
    };
    tail.rigid[j] = Some(b.clone());
    let mut bridge = vec![BigInt::zero(); c.initial.len()];
    bridge[j] = b - a;
    Ok(Some(replacement(g, index, vec![part, tail], vec![bridge])?))
}
fn theta_two(g: &Sequence, ctx: &mut Context) -> Checked<Option<Vec<Sequence>>> {
    for (i, c) in g.components.iter().enumerate() {
        for reverse in [false, true] {
            ctx.tick()?;
            let endpoints = if reverse {
                &c.final_marking
            } else {
                &c.initial
            };
            let selected: Vec<_> = (0..endpoints.len())
                .filter(|&j| c.rigid[j].is_none() && endpoints[j].is_some())
                .collect();
            if selected.is_empty() {
                continue;
            }
            let arcs: Vec<_> = c
                .arcs
                .iter()
                .map(|e| Arc {
                    source: if reverse { e.target } else { e.source },
                    target: if reverse { e.source } else { e.target },
                    effect: selected
                        .iter()
                        .map(|&j| {
                            if reverse {
                                -&e.effect[j]
                            } else {
                                e.effect[j].clone()
                            }
                        })
                        .collect(),
                })
                .collect();
            let initial: Vec<_> = selected
                .iter()
                .map(|&j| endpoints[j].clone().unwrap())
                .collect();
            let analysis = complete_cover::analyze(
                c.states,
                &arcs,
                if reverse { c.exit } else { c.entry },
                &initial,
                ctx.limits.deadline,
                ctx.limits.max_nodes,
            )
            .map_err(|e| format!("coverability: {e:?}"))?;
            if analysis.pumpable {
                continue;
            }
            let bound = analysis
                .path_bound
                .ok_or("missing pathwise counter bound")?;
            let mut refinements = vec![];
            for j in selected {
                let other = if reverse {
                    &c.initial[j]
                } else {
                    &c.final_marking[j]
                };
                if other.is_none() {
                    ctx.stats.endpoint_refinements += 1;
                    refinements.extend(constrain_endpoint(g, i, j, reverse, &bound, ctx)?);
                } else {
                    ctx.stats.counter_refinements += 1;
                    if let Some(next) = bound_counter(g, i, j, &bound, ctx)? {
                        refinements.push(next);
                    }
                }
            }
            return Ok(Some(refinements));
        }
    }
    Ok(None)
}
fn decide_inner(initial: Sequence, ctx: &mut Context) -> Checked<bool> {
    validate(&initial)?;
    let mut pending = vec![initial];
    while let Some(mut g) = pending.pop() {
        ctx.tick()?;
        ctx.stats.decompositions += 1;
        if !g.components.iter_mut().all(normalize) {
            continue;
        }
        let mut split = false;
        for i in 0..g.components.len() {
            let ids = sccs(&g.components[i]);
            if ids.iter().any(|&id| id != ids[0]) {
                ctx.stats.scc_refinements += 1;
                pending.extend(split_scc(&g, i, &ids, ctx)?);
                split = true;
                break;
            }
        }
        if split {
            continue;
        }
        let ch = characteristic(&g);
        match arithmetic::solve_integer(&ch.system, &ctx.arithmetic()) {
            Answer::Infeasible => continue,
            Answer::Unknown(s) => return Err(s.into()),
            Answer::Feasible(_) => {}
        }
        let positive: Vec<_> = ch.marked.iter().map(|(i, _)| *i).collect();
        match arithmetic::homogeneous_direction(&ch.system, &positive, &ctx.arithmetic()) {
            Answer::Unknown(s) => return Err(s.into()),
            Answer::Feasible(_) => {}
            Answer::Infeasible => {
                let mut refined = false;
                for (v, kind) in &ch.marked {
                    ctx.tick()?;
                    match arithmetic::homogeneous_direction(&ch.system, &[*v], &ctx.arithmetic()) {
                        Answer::Unknown(s) => return Err(s.into()),
                        Answer::Feasible(_) => continue,
                        Answer::Infeasible => {
                            let bound = bounded_maximum(&ch.system, *v, ctx)?;
                            let branches = match *kind {
                                Variable::Initial(i, j) => {
                                    ctx.stats.endpoint_refinements += 1;
                                    constrain_endpoint(&g, i, j, true, &bound, ctx)?
                                }
                                Variable::Final(i, j) => {
                                    ctx.stats.endpoint_refinements += 1;
                                    constrain_endpoint(&g, i, j, false, &bound, ctx)?
                                }
                                Variable::Transition(i, e) => {
                                    ctx.stats.transition_refinements += 1;
                                    bounded_transition(&g, i, e, &bound, ctx)?
                                }
                            };
                            pending.extend(branches);
                            refined = true;
                            break;
                        }
                    }
                }
                if !refined {
                    return Err("ray decomposition inconsistency".into());
                }
                continue;
            }
        }
        if let Some(branches) = theta_two(&g, ctx)? {
            pending.extend(branches);
            continue;
        }
        ctx.stats.perfect_sequences += 1;
        return Ok(true);
    }
    Ok(false)
}
pub fn decide(sequence: Sequence, limits: Limits) -> (Decision, Statistics) {
    let mut ctx = Context {
        limits,
        stats: Statistics::default(),
        work: 0,
    };
    let verdict = match decide_inner(sequence, &mut ctx) {
        Ok(true) => Decision::Reachable,
        Ok(false) => Decision::Unreachable,
        Err(s) => Decision::Unknown(s),
    };
    (verdict, ctx.stats)
}

pub fn from_problem(p: &Problem) -> Sequence {
    let point = crate::complete_target::reduce(p);
    let d = point.initial.len();
    Sequence {
        components: vec![Component {
            states: point.states,
            arcs: point.arcs,
            entry: point.initial_state,
            exit: point.final_state,
            initial: point.initial.into_iter().map(Some).collect(),
            final_marking: point.final_marking.into_iter().map(Some).collect(),
            rigid: vec![None; d],
        }],
        bridges: vec![],
    }
}
fn accepts(p: &Problem, m: &[BigInt]) -> bool {
    p.target.iter().all(|c| {
        let value: BigInt = c
            .coefficients
            .iter()
            .zip(m)
            .map(|(&a, x)| BigInt::from(a) * x)
            .sum();
        if c.equality {
            value == BigInt::from(c.bound)
        } else {
            value >= BigInt::from(c.bound)
        }
    })
}
pub fn check_witness(p: &Problem, trace: &[usize]) -> Checked<Vec<BigInt>> {
    let mut m: Vec<_> = p.initial.iter().copied().map(BigInt::from).collect();
    for &i in trace {
        let t = p.transitions.get(i).ok_or("invalid witness index")?;
        for &(j, w) in &t.pre {
            if m[j] < BigInt::from(w) {
                return Err("disabled witness transition".into());
            }
        }
        for &(j, w) in &t.pre {
            m[j] -= w;
        }
        for &(j, w) in &t.post {
            m[j] += w;
        }
    }
    if !accepts(p, &m) {
        return Err("witness target not reached".into());
    }
    Ok(m)
}
fn extract_witness(p: &Problem, limits: &Limits) -> Checked<Outcome> {
    let initial: Vec<_> = p.initial.iter().copied().map(BigInt::from).collect();
    let mut nodes = vec![(initial.clone(), None::<(usize, usize)>)];
    let mut seen = HashMap::from([(initial, 0)]);
    let mut queue = VecDeque::from([0]);
    while let Some(id) = queue.pop_front() {
        if limits.deadline.is_some_and(|d| Instant::now() >= d) {
            return Err("reachability proved; witness extraction time limit".into());
        }
        let m = &nodes[id].0;
        if accepts(p, m) {
            let mut trace = vec![];
            let mut current = id;
            while let Some((prev, t)) = nodes[current].1 {
                trace.push(t);
                current = prev;
            }
            trace.reverse();
            let marking = check_witness(p, &trace)?;
            let small: Option<Vec<_>> = marking.iter().map(ToPrimitive::to_u64).collect();
            let mut out = Outcome::unknown(
                "kosaraju",
                "Kosaraju reachability and replayed witness",
                nodes.len(),
            );
            out.verdict = "reachable";
            out.trace = trace;
            out.marking = small;
            if out.marking.is_none() {
                out.proof = Some(
                    serde_json::json!({"kind":"big-witness","marking":marking.iter().map(ToString::to_string).collect::<Vec<_>>()}),
                );
            }
            return Ok(out);
        }
        for (t, tr) in p.transitions.iter().enumerate() {
            if tr
                .pre
                .iter()
                .any(|&(j, w)| nodes[id].0[j] < BigInt::from(w))
            {
                continue;
            }
            let mut next = nodes[id].0.clone();
            for &(j, w) in &tr.pre {
                next[j] -= w;
            }
            for &(j, w) in &tr.post {
                next[j] += w;
            }
            if seen.contains_key(&next) {
                continue;
            }
            if limits.max_nodes.is_some_and(|n| nodes.len() >= n) {
                return Err("reachability proved; witness extraction state limit".into());
            }
            let child = nodes.len();
            seen.insert(next.clone(), child);
            nodes.push((next, Some((id, t))));
            queue.push_back(child);
        }
    }
    Err("internal inconsistency: proved reachable but finite search exhausted".into())
}
pub fn solve(
    p: &Problem,
    timeout: Option<Duration>,
    max_nodes: Option<usize>,
    max_rows: Option<usize>,
) -> Outcome {
    if let Err(e) = p.validate() {
        return Outcome::unknown("kosaraju", &format!("invalid input: {e}"), 0);
    }
    let deadline = match timeout {
        Some(duration) => match Instant::now().checked_add(duration) {
            Some(deadline) => Some(deadline),
            None => return Outcome::unknown("kosaraju", "deadline exceeds clock capacity", 0),
        },
        None => None,
    };
    let limits = Limits {
        deadline,
        max_nodes,
        max_rows,
    };
    let (decision, stats) = decide(from_problem(p), limits.clone());
    let summary = format!(
        "{} decompositions; {} SCC, {} transition, {} endpoint, {} counter refinements",
        stats.decompositions,
        stats.scc_refinements,
        stats.transition_refinements,
        stats.endpoint_refinements,
        stats.counter_refinements
    );
    match decision {
        Decision::Unknown(s) => {
            Outcome::unknown("kosaraju", &format!("{s}; {summary}"), stats.decompositions)
        }
        Decision::Unreachable => {
            let mut out = Outcome::unknown(
                "kosaraju",
                &format!("complete finite decomposition exhausted; {summary}"),
                stats.decompositions,
            );
            out.verdict = "unreachable";
            out
        }
        Decision::Reachable => match extract_witness(p, &limits) {
            Ok(mut out) => {
                out.reason = format!("{}; {summary}", out.reason);
                out
            }
            Err(e) => {
                Outcome::unknown("kosaraju", &format!("{e}; {summary}"), stats.decompositions)
            }
        },
    }
}
