//! Witness search guided by a delete-relaxed enabling graph.
//!
//! A fact is a weighted input guard `m[p] >= w`. Positive incidence effects
//! achieve facts without consuming tokens; their costs include the cheapest
//! prerequisites and repetitions. Signed linear goals choose an improving
//! transition and regress through its guards. These costs and helpful actions
//! are ordering hints only, including for equality and mixed-sign goals.
//! Every reported answer is an independently replayed original-net witness.
use crate::{model::Problem, search::Outcome};
use num_bigint::BigInt;
use std::{
    cmp::{Ordering, Reverse},
    collections::{BinaryHeap, HashMap, HashSet},
    sync::Arc,
    time::{Duration, Instant},
};

const INF: u64 = u64::MAX / 4;
const FULL_EXPANSION_PERIOD: u64 = 8;
const CLOSURE_WORK_LIMIT: usize = 100_000;
const BATCHED_TRACE_LIMIT: u64 = 1_000_000;
type Marking = Arc<[(usize, u64)]>;
type Queue = BinaryHeap<Reverse<(u64, u64, usize)>>;

fn tokens(marking: &[(usize, u64)], place: usize) -> u64 {
    marking
        .binary_search_by_key(&place, |&(p, _)| p)
        .map_or(0, |i| marking[i].1)
}

struct Action {
    original: usize,
    guards: Vec<usize>,
    delta: Vec<(usize, i128)>,
    produces: Vec<(usize, u64)>,
    effects: Vec<i128>,
}
struct Graph {
    retained_places: Vec<bool>,
    facts: Vec<(usize, u64)>,
    users: Vec<Vec<usize>>,
    actions: Vec<Action>,
    sources: Vec<usize>,
    goal_actions: Vec<[Vec<usize>; 2]>,
}
struct Plan {
    score: u64,
    helpful: Vec<usize>,
    enabled: Vec<usize>,
}

/// Incidence lists avoid materializing the quadratic transition dependency graph.
struct Stubborn<'a> {
    graph: &'a Graph,
    readers: Vec<Vec<usize>>,
    consumers: Vec<Vec<usize>>,
    producers: Vec<Vec<usize>>,
    visible: Vec<bool>,
    work_limit: usize,
    full_period: u64,
}

#[derive(Debug, PartialEq, Eq)]
enum FullExpansion {
    Periodic,
    Visible,
    Seen,
    ClosureLimit,
    AllEnabled,
}

enum Selection {
    Full(FullExpansion),
    Reduced(Vec<(usize, Marking)>),
    TargetReduced(Vec<usize>),
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum Reduction {
    Off,
    Invisible,
    TargetDirected,
}

struct ClosureWork {
    used: usize,
    limit: usize,
    deadline: Instant,
}

impl ClosureWork {
    fn spend(&mut self) -> bool {
        self.used += 1;
        self.used <= self.limit && Instant::now() < self.deadline
    }
}

#[derive(Default)]
struct ExactSum {
    small: i128,
    large: Option<BigInt>,
}

impl ExactSum {
    fn add(&mut self, coefficient: i64, value: i128) {
        if let Some(sum) = &mut self.large {
            *sum += BigInt::from(coefficient) * BigInt::from(value);
        } else if let Some(sum) = i128::from(coefficient)
            .checked_mul(value)
            .and_then(|product| self.small.checked_add(product))
        {
            self.small = sum;
        } else {
            self.large =
                Some(BigInt::from(self.small) + BigInt::from(coefficient) * BigInt::from(value));
        }
    }

    fn compare(&self, bound: i64) -> Ordering {
        self.large.as_ref().map_or_else(
            || self.small.cmp(&i128::from(bound)),
            |sum| sum.cmp(&BigInt::from(bound)),
        )
    }
}

fn exact_compare(
    terms: impl IntoIterator<Item = (i64, i128)>,
    bound: i64,
    work: &mut ClosureWork,
) -> Option<Ordering> {
    let mut sum = ExactSum::default();
    for (coefficient, value) in terms {
        if !work.spend() {
            return None;
        }
        sum.add(coefficient, value);
    }
    Some(sum.compare(bound))
}

#[derive(Default)]
struct TargetDirections {
    increasing: Vec<usize>,
    decreasing: Vec<usize>,
}

#[derive(Default)]
struct DirectionBuilder {
    directions: TargetDirections,
    action: usize,
    term: usize,
    sum: ExactSum,
}

enum DirectionCache {
    Building(DirectionBuilder),
    Complete(TargetDirections),
}

impl DirectionCache {
    fn complete(
        &mut self,
        graph: &Graph,
        coefficients: &[i64],
        work: &mut ClosureWork,
    ) -> Option<&TargetDirections> {
        if let Self::Building(builder) = self {
            while builder.action < graph.actions.len() {
                if !work.spend() {
                    return None;
                }
                let delta = &graph.actions[builder.action].delta;
                while builder.term < delta.len() {
                    if !work.spend() {
                        return None;
                    }
                    let (place, effect) = delta[builder.term];
                    builder.sum.add(coefficients[place], effect);
                    builder.term += 1;
                }
                match builder.sum.compare(0) {
                    Ordering::Greater => builder.directions.increasing.push(builder.action),
                    Ordering::Less => builder.directions.decreasing.push(builder.action),
                    Ordering::Equal => {}
                }
                builder.action += 1;
                builder.term = 0;
                builder.sum = ExactSum::default();
            }
            *self = Self::Complete(std::mem::take(&mut builder.directions));
        }
        match self {
            Self::Complete(directions) => Some(directions),
            Self::Building(_) => None,
        }
    }
}

#[derive(Clone, Default, serde::Serialize)]
struct TargetDiagnostics {
    target_limit_evaluation: u64,
    target_limit_directions: u64,
    target_limit_seeds: u64,
    target_limit_closure: u64,
    target_early_all_enabled: u64,
    target_repeated_lists_avoided: u64,
}

#[derive(Clone, Copy)]
enum DependencyRole {
    Producers = 1,
    Consumers = 2,
    Readers = 4,
}

struct TargetClosure<'a> {
    remaining: usize,
    enabled: Vec<bool>,
    scanned: Vec<u8>,
    stats: &'a mut TargetDiagnostics,
}

impl<'a> TargetClosure<'a> {
    fn new(index: &Stubborn<'_>, enabled: &[usize], stats: &'a mut TargetDiagnostics) -> Self {
        let mut mask = vec![false; index.graph.actions.len()];
        for &t in enabled {
            mask[t] = true;
        }
        Self {
            remaining: enabled.len(),
            enabled: mask,
            scanned: vec![0; index.producers.len()],
            stats,
        }
    }

    fn select(&mut self, t: usize) -> bool {
        if std::mem::replace(&mut self.enabled[t], false) {
            self.remaining -= 1;
        }
        self.remaining == 0
    }

    fn scan(&mut self, place: usize, role: DependencyRole) -> bool {
        let role = role as u8;
        if self.scanned[place] & role != 0 {
            self.stats.target_repeated_lists_avoided += 1;
            false
        } else {
            self.scanned[place] |= role;
            true
        }
    }
}

struct TargetStubborn<'a> {
    index: Stubborn<'a>,
    directions: Vec<DirectionCache>,
    stats: TargetDiagnostics,
}

impl<'a> TargetStubborn<'a> {
    fn new(graph: &'a Graph, p: &Problem, deadline: Instant) -> Option<Self> {
        Some(Self {
            index: Stubborn::new(graph, p, deadline)?,
            stats: TargetDiagnostics::default(),
            directions: (0..p.target.len())
                .map(|_| DirectionCache::Building(DirectionBuilder::default()))
                .collect(),
        })
    }

    fn select(
        &mut self,
        p: &Problem,
        marking: &[(usize, u64)],
        enabled_order: &[usize],
        deadline: Instant,
    ) -> Selection {
        let mut work = ClosureWork {
            used: 0,
            limit: self.index.work_limit,
            deadline,
        };
        let mut violated = None;
        for (id, constraint) in p.target.iter().enumerate() {
            if !work.spend() {
                self.stats.target_limit_evaluation += 1;
                return Selection::Full(FullExpansion::ClosureLimit);
            }
            let Some(comparison) = exact_compare(
                marking
                    .iter()
                    .map(|&(place, count)| (constraint.coefficients[place], i128::from(count))),
                constraint.bound,
                &mut work,
            ) else {
                self.stats.target_limit_evaluation += 1;
                return Selection::Full(FullExpansion::ClosureLimit);
            };
            if comparison == Ordering::Less
                || (constraint.equality && comparison == Ordering::Greater)
            {
                violated = Some((id, comparison == Ordering::Less));
                break;
            }
        }
        let Some((id, increase)) = violated else {
            return Selection::Full(FullExpansion::AllEnabled);
        };
        let Some(directions) =
            self.directions[id].complete(self.index.graph, &p.target[id].coefficients, &mut work)
        else {
            self.stats.target_limit_directions += 1;
            return Selection::Full(FullExpansion::ClosureLimit);
        };
        let seeds = if increase {
            &directions.increasing
        } else {
            &directions.decreasing
        };
        let mut closure = TargetClosure::new(&self.index, enabled_order, &mut self.stats);
        if closure.remaining == 0 {
            closure.stats.target_early_all_enabled += 1;
            return Selection::Full(FullExpansion::AllEnabled);
        }
        let mut selected = vec![false; self.index.graph.actions.len()];
        let mut pending = Vec::new();
        for &t in seeds {
            if !work.spend() {
                closure.stats.target_limit_seeds += 1;
                return Selection::Full(FullExpansion::ClosureLimit);
            }
            selected[t] = true;
            pending.push(t);
            if closure.select(t) {
                closure.stats.target_early_all_enabled += 1;
                return Selection::Full(FullExpansion::AllEnabled);
            }
        }
        if let Err(reason) = self.index.close(
            marking,
            &mut selected,
            &mut pending,
            false,
            &mut work,
            Some(&mut closure),
        ) {
            match reason {
                FullExpansion::AllEnabled => closure.stats.target_early_all_enabled += 1,
                FullExpansion::ClosureLimit => closure.stats.target_limit_closure += 1,
                _ => unreachable!(),
            }
            return Selection::Full(reason);
        }
        Selection::TargetReduced(
            enabled_order
                .iter()
                .copied()
                .filter(|&t| selected[t])
                .collect(),
        )
    }
}

enum ReductionIndex<'a> {
    Invisible(Stubborn<'a>),
    TargetDirected(TargetStubborn<'a>),
}

impl<'a> Stubborn<'a> {
    fn new(graph: &'a Graph, p: &Problem, deadline: Instant) -> Option<Self> {
        let mut index = Self {
            graph,
            readers: vec![vec![]; p.places.len()],
            consumers: vec![vec![]; p.places.len()],
            producers: vec![vec![]; p.places.len()],
            visible: vec![false; graph.actions.len()],
            work_limit: CLOSURE_WORK_LIMIT,
            full_period: FULL_EXPANSION_PERIOD,
        };
        let target_support: Vec<_> = (0..p.places.len())
            .map(|place| p.target.iter().any(|c| c.coefficients[place] != 0))
            .collect();
        for (t, action) in graph.actions.iter().enumerate() {
            if Instant::now() >= deadline {
                return None;
            }
            for &guard in &action.guards {
                index.readers[graph.facts[guard].0].push(t);
            }
            for &(place, delta) in &action.delta {
                if delta < 0 {
                    index.consumers[place].push(t);
                } else {
                    index.producers[place].push(t);
                }
                index.visible[t] |= target_support[place];
            }
        }
        Some(index)
    }

    fn close(
        &self,
        marking: &[(usize, u64)],
        selected: &mut [bool],
        pending: &mut Vec<usize>,
        invisible: bool,
        work: &mut ClosureWork,
        mut target: Option<&mut TargetClosure<'_>>,
    ) -> Result<(), FullExpansion> {
        while let Some(t) = pending.pop() {
            if !work.spend() {
                return Err(FullExpansion::ClosureLimit);
            }
            let action = &self.graph.actions[t];
            let mut deficient = None;
            for &guard in &action.guards {
                if !work.spend() {
                    return Err(FullExpansion::ClosureLimit);
                }
                let (place, weight) = self.graph.facts[guard];
                if tokens(marking, place) < weight {
                    deficient = Some(place);
                    break;
                }
            }
            if deficient.is_none() && invisible && self.visible[t] {
                return Err(FullExpansion::Visible);
            }
            let (guards, delta): (&[usize], &[(usize, i128)]) = if deficient.is_some() {
                (&[], &[])
            } else {
                (&action.guards, &action.delta)
            };
            let dependencies = deficient
                .map(|place| {
                    (
                        place,
                        DependencyRole::Producers,
                        self.producers[place].as_slice(),
                    )
                })
                .into_iter()
                .chain(guards.iter().map(|&guard| {
                    let place = self.graph.facts[guard].0;
                    (
                        place,
                        DependencyRole::Consumers,
                        self.consumers[place].as_slice(),
                    )
                }))
                .chain(delta.iter().filter(|&&(_, d)| d < 0).map(|&(place, _)| {
                    (
                        place,
                        DependencyRole::Readers,
                        self.readers[place].as_slice(),
                    )
                }));
            for (place, role, list) in dependencies {
                if let Some(target) = target.as_deref_mut() {
                    if !work.spend() {
                        return Err(FullExpansion::ClosureLimit);
                    }
                    if !target.scan(place, role) {
                        continue;
                    }
                }
                for &u in list {
                    if !work.spend() {
                        return Err(FullExpansion::ClosureLimit);
                    }
                    if !std::mem::replace(&mut selected[u], true) {
                        pending.push(u);
                        if target.as_deref_mut().is_some_and(|target| target.select(u)) {
                            return Err(FullExpansion::AllEnabled);
                        }
                    }
                }
            }
        }
        Ok(())
    }

    fn select(
        &self,
        marking: &[(usize, u64)],
        enabled_order: &[usize],
        depth: u64,
        seen: &HashSet<Marking>,
        deadline: Instant,
    ) -> Result<Selection, &'static str> {
        depth.checked_add(1).ok_or("discovery depth overflow")?;
        if depth.is_multiple_of(self.full_period) {
            return Ok(Selection::Full(FullExpansion::Periodic));
        }
        let Some(&seed) = enabled_order.first().filter(|&&t| !self.visible[t]) else {
            return Ok(Selection::Full(FullExpansion::Visible));
        };
        let mut selected = vec![false; self.graph.actions.len()];
        let mut pending = vec![seed];
        selected[seed] = true;
        let mut work = ClosureWork {
            used: 0,
            limit: self.work_limit,
            deadline,
        };
        if let Err(reason) = self.close(marking, &mut selected, &mut pending, true, &mut work, None)
        {
            return Ok(Selection::Full(reason));
        }
        if enabled_order.iter().all(|&t| selected[t]) {
            return Ok(Selection::Full(FullExpansion::AllEnabled));
        }
        let mut successors = Vec::new();
        for &t in enabled_order.iter().filter(|&&t| selected[t]) {
            if Instant::now() >= deadline {
                return Ok(Selection::Full(FullExpansion::ClosureLimit));
            }
            let next = self
                .graph
                .fire(marking, t)?
                .ok_or("stubborn enabledness mismatch")?;
            // Freshness uses the pre-expansion set; inserting here would invalidate depth progress.
            if seen.contains(&next) {
                return Ok(Selection::Full(FullExpansion::Seen));
            }
            successors.push((t, next));
        }
        Ok(Selection::Reduced(successors))
    }
}

#[cfg(test)]
#[path = "relaxed_stubborn_tests.rs"]
mod stubborn_tests;

#[cfg(test)]
#[path = "relaxed_plan_tests.rs"]
mod plan_tests;

#[derive(serde::Serialize)]
struct Diagnostics {
    focused: bool,
    stubborn: bool,
    target_directed: bool,
    expanded: u64,
    generated: u64,
    enabled_considered: u64,
    chosen: u64,
    reductions: u64,
    full_periodic: u64,
    full_visible: u64,
    full_seen: u64,
    full_closure_limit: u64,
    full_all_enabled: u64,
    #[serde(flatten)]
    target_selection: TargetDiagnostics,
}

impl Diagnostics {
    fn new(focused: bool, reduction: Reduction) -> Self {
        Self {
            focused,
            stubborn: reduction != Reduction::Off,
            target_directed: reduction == Reduction::TargetDirected,
            expanded: 0,
            generated: 0,
            enabled_considered: 0,
            chosen: 0,
            reductions: 0,
            full_periodic: 0,
            full_visible: 0,
            full_seen: 0,
            full_closure_limit: 0,
            full_all_enabled: 0,
            target_selection: TargetDiagnostics::default(),
        }
    }

    fn full(&mut self, reason: FullExpansion) {
        match reason {
            FullExpansion::Periodic => self.full_periodic += 1,
            FullExpansion::Visible => self.full_visible += 1,
            FullExpansion::Seen => self.full_seen += 1,
            FullExpansion::ClosureLimit => self.full_closure_limit += 1,
            FullExpansion::AllEnabled => self.full_all_enabled += 1,
        }
    }
}

impl Drop for Diagnostics {
    fn drop(&mut self) {
        if std::env::var_os("VASS_RELAXED_PROFILE").is_some()
            || std::env::var_os("VASS_PORTFOLIO_PROFILE").is_some()
        {
            eprintln!(
                "{}",
                serde_json::json!({"event": "relaxed-search", "stats": self})
            );
        }
    }
}

impl Graph {
    fn new(p: &Problem, start: Instant, timeout: Duration) -> Option<Self> {
        let mut facts: Vec<_> = p
            .transitions
            .iter()
            .flat_map(|t| t.pre.iter().copied())
            .collect();
        facts.sort_unstable();
        facts.dedup();
        let mut facts_by_place = vec![vec![]; p.places.len()];
        for (id, &(place, _)) in facts.iter().enumerate() {
            facts_by_place[place].push(id);
        }
        let mut actions = Vec::with_capacity(p.transitions.len());
        for (id, t) in p.transitions.iter().enumerate() {
            if start.elapsed() >= timeout {
                return None;
            }
            let guards: Vec<_> = t
                .pre
                .iter()
                .map(|arc| facts.binary_search(arc).unwrap())
                .collect();
            let mut delta = HashMap::<usize, i128>::new();
            for &(place, weight) in &t.pre {
                *delta.entry(place).or_default() -= i128::from(weight);
            }
            for &(place, weight) in &t.post {
                *delta.entry(place).or_default() += i128::from(weight);
            }
            let mut delta: Vec<_> = delta.into_iter().filter(|&(_, d)| d != 0).collect();
            delta.sort_unstable_by_key(|&(place, _)| place);
            let produces = delta
                .iter()
                .filter(|&&(_, d)| d > 0)
                .flat_map(|&(place, d)| {
                    facts_by_place[place]
                        .iter()
                        .map(move |&fact| (fact, d as u64))
                })
                .collect();
            let effects = p
                .target
                .iter()
                .map(|c| {
                    delta.iter().fold(0i128, |sum, &(place, d)| {
                        sum.saturating_add(i128::from(c.coefficients[place]).saturating_mul(d))
                    })
                })
                .collect();
            actions.push(Action {
                original: id,
                guards,
                delta,
                produces,
                effects,
            });
        }
        let mut producers = vec![Vec::new(); facts.len()];
        for (t, action) in actions.iter().enumerate() {
            for &(fact, _) in &action.produces {
                producers[fact].push(t);
            }
        }
        let mut retained_places: Vec<_> = (0..p.places.len())
            .map(|place| p.target.iter().any(|c| c.coefficients[place] != 0))
            .collect();
        let mut pending = Vec::new();
        let mut retained_actions = vec![false; actions.len()];
        let mut retained_facts = vec![false; facts.len()];
        for (t, action) in actions.iter().enumerate() {
            if action
                .delta
                .iter()
                .any(|&(place, _)| retained_places[place])
            {
                retained_actions[t] = true;
                pending.push(t);
            }
        }
        while let Some(t) = pending.pop() {
            if start.elapsed() >= timeout {
                return None;
            }
            for &fact in &actions[t].guards {
                retained_places[facts[fact].0] = true;
                if !std::mem::replace(&mut retained_facts[fact], true) {
                    for &producer in &producers[fact] {
                        if !std::mem::replace(&mut retained_actions[producer], true) {
                            pending.push(producer);
                        }
                    }
                }
            }
        }
        let mut fact_map = vec![usize::MAX; facts.len()];
        let mut next_fact = 0;
        let facts: Vec<_> = facts
            .into_iter()
            .enumerate()
            .filter_map(|(old, fact)| {
                if retained_facts[old] {
                    fact_map[old] = next_fact;
                    next_fact += 1;
                    Some(fact)
                } else {
                    None
                }
            })
            .collect();
        let actions: Vec<_> = actions
            .into_iter()
            .enumerate()
            .filter_map(|(id, mut action)| {
                if !retained_actions[id] {
                    return None;
                }
                action.delta.retain(|&(place, _)| retained_places[place]);
                for fact in &mut action.guards {
                    *fact = fact_map[*fact];
                }
                action.produces.retain_mut(|(fact, _)| {
                    let mapped = fact_map[*fact];
                    *fact = mapped;
                    mapped != usize::MAX
                });
                Some(action)
            })
            .collect();
        let mut users = vec![Vec::new(); facts.len()];
        let mut sources = Vec::new();
        let mut goal_actions = vec![[Vec::new(), Vec::new()]; p.target.len()];
        for (t, action) in actions.iter().enumerate() {
            if start.elapsed() >= timeout {
                return None;
            }
            for &fact in &action.guards {
                users[fact].push(t);
            }
            if action.guards.is_empty() {
                sources.push(t);
            }
            for (goal, &effect) in action.effects.iter().enumerate() {
                if effect != 0 {
                    goal_actions[goal][usize::from(effect < 0)].push(t);
                }
            }
        }
        Some(Self {
            retained_places,
            facts,
            users,
            actions,
            sources,
            goal_actions,
        })
    }

    fn plan(
        &self,
        p: &Problem,
        marking: &[(usize, u64)],
        start: Instant,
        timeout: Duration,
    ) -> Option<Plan> {
        let mut costs = vec![INF; self.facts.len()];
        let mut achiever = vec![None; self.facts.len()];
        let mut settled = vec![false; self.facts.len()];
        let mut remaining: Vec<_> = self.actions.iter().map(|t| t.guards.len()).collect();
        let mut activation = vec![INF; self.actions.len()];
        let mut guard_max = vec![0; self.actions.len()];
        let mut enabled = self.sources.clone();
        let mut queue = BinaryHeap::new();
        let mut deficits = Vec::with_capacity(self.facts.len());
        for (fact, &(place, weight)) in self.facts.iter().enumerate() {
            let deficit = weight.saturating_sub(tokens(marking, place));
            deficits.push(deficit);
            if deficit == 0 {
                costs[fact] = 0;
                queue.push(Reverse((0, fact)));
            }
        }
        let offer = |action: usize,
                     base: u64,
                     costs: &mut [u64],
                     achiever: &mut [Option<usize>],
                     queue: &mut BinaryHeap<Reverse<(u64, usize)>>| {
            for &(fact, gain) in &self.actions[action].produces {
                if base >= costs[fact] {
                    continue;
                }
                let deficit = deficits[fact];
                let cost = base.saturating_add(deficit.div_ceil(gain).max(1)).min(INF);
                if cost < costs[fact] {
                    costs[fact] = cost;
                    achiever[fact] = Some(action);
                    queue.push(Reverse((cost, fact)));
                }
            }
        };
        for &t in &self.sources {
            activation[t] = 0;
            offer(t, 0, &mut costs, &mut achiever, &mut queue);
        }
        let mut iteration = 0usize;
        while let Some(Reverse((cost, fact))) = queue.pop() {
            iteration += 1;
            if iteration.is_multiple_of(128) && start.elapsed() >= timeout {
                return None;
            }
            if settled[fact] || cost != costs[fact] {
                continue;
            }
            settled[fact] = true;
            for &t in &self.users[fact] {
                remaining[t] -= 1;
                guard_max[t] = guard_max[t].max(cost);
                if remaining[t] == 0 {
                    activation[t] = guard_max[t];
                    // Only guards true in this marking have zero relaxed cost.
                    if guard_max[t] == 0 {
                        enabled.push(t);
                    }
                    offer(t, guard_max[t], &mut costs, &mut achiever, &mut queue);
                }
            }
        }
        let mut score = 0u64;
        let mut selected = Vec::new();
        for (goal, constraint) in p.target.iter().enumerate() {
            if start.elapsed() >= timeout {
                return None;
            }
            let value = marking.iter().fold(0i128, |sum, &(place, count)| {
                sum.saturating_add(i128::from(constraint.coefficients[place]) * i128::from(count))
            });
            let gap = i128::from(constraint.bound).saturating_sub(value);
            if gap == 0 || (!constraint.equality && gap < 0) {
                continue;
            }
            let mut best = (INF, usize::MAX);
            for (i, &t) in self.goal_actions[goal][usize::from(gap < 0)]
                .iter()
                .enumerate()
            {
                if i.is_multiple_of(256) && start.elapsed() >= timeout {
                    return None;
                }
                let effect = self.actions[t].effects[goal];
                if activation[t] == INF {
                    continue;
                }
                let repeats = gap
                    .unsigned_abs()
                    .div_ceil(effect.unsigned_abs())
                    .min(u128::from(INF)) as u64;
                let cost = activation[t].saturating_add(repeats).min(INF);
                best = best.min((cost, t));
            }
            score = score.saturating_add(best.0).min(INF);
            if best.1 != usize::MAX {
                selected.push(best.1);
            }
        }
        let mut visited = vec![false; self.actions.len()];
        let mut helpful = Vec::new();
        while let Some(t) = selected.pop() {
            if visited[t] {
                continue;
            }
            visited[t] = true;
            if activation[t] == 0 {
                helpful.push(t);
            } else {
                for &g in &self.actions[t].guards {
                    if costs[g] > 0
                        && let Some(producer) = achiever[g]
                    {
                        selected.push(producer);
                    }
                }
            }
        }
        helpful.sort_unstable();
        enabled.sort_unstable();
        Some(Plan {
            score,
            helpful,
            enabled,
        })
    }

    fn repetitions(
        &self,
        p: &Problem,
        marking: &[(usize, u64)],
        t: usize,
        cap: u64,
        deadline: Instant,
    ) -> Vec<u64> {
        let action = &self.actions[t];
        let maximum = crate::repeat_fire::maximum_sparse(
            action.guards.iter().map(|&g| self.facts[g]),
            &action.delta,
            |place| tokens(marking, place),
        )
        .unwrap_or(0)
        .min(cap);
        let mut counts = Vec::new();
        if maximum <= 1 {
            return counts;
        }
        counts.push(maximum);
        for (constraint, &effect) in p.target.iter().zip(&action.effects) {
            if Instant::now() >= deadline {
                break;
            }
            let value = marking.iter().try_fold(0i128, |sum, &(place, count)| {
                sum.checked_add(i128::from(constraint.coefficients[place]) * i128::from(count))
            });
            let Some(gap) = value.and_then(|value| i128::from(constraint.bound).checked_sub(value))
            else {
                continue;
            };
            if gap == 0 || effect == 0 || gap.signum() != effect.signum() {
                continue;
            }
            let numerator = gap.unsigned_abs();
            let denominator = effect.unsigned_abs();
            let count = numerator / denominator + u128::from(numerator % denominator != 0);
            if let Ok(count) = u64::try_from(count)
                && count > 1
                && count <= maximum
            {
                counts.push(count);
            }
        }
        counts.sort_unstable();
        counts.dedup();
        counts
    }

    fn fire(&self, marking: &[(usize, u64)], t: usize) -> Result<Option<Marking>, &'static str> {
        self.fire_many(marking, t, 1)
    }

    fn fire_many(
        &self,
        marking: &[(usize, u64)],
        t: usize,
        repeats: u64,
    ) -> Result<Option<Marking>, &'static str> {
        let action = &self.actions[t];
        if repeats > 1
            && crate::repeat_fire::maximum_sparse(
                action.guards.iter().map(|&g| self.facts[g]),
                &action.delta,
                |place| tokens(marking, place),
            )
            .is_none_or(|bound| repeats > bound)
        {
            return Ok(None);
        }
        if action.guards.iter().any(|&g| {
            let (place, weight) = self.facts[g];
            tokens(marking, place) < weight
        }) {
            return Ok(None);
        }
        let mut next = marking.to_vec();
        for &(place, delta) in &action.delta {
            let delta = delta
                .checked_mul(i128::from(repeats))
                .ok_or("counter overflow")?;
            match next.binary_search_by_key(&place, |&(p, _)| p) {
                Ok(i) => {
                    let count = u64::try_from(i128::from(next[i].1) + delta)
                        .map_err(|_| "counter overflow")?;
                    if count == 0 {
                        next.remove(i);
                    } else {
                        next[i].1 = count;
                    }
                }
                Err(i) => {
                    let count = u64::try_from(delta).map_err(|_| "counter overflow")?;
                    if count > 0 {
                        next.insert(i, (place, count));
                    }
                }
            }
        }
        Ok(Some(next.into()))
    }
}

struct Node {
    marking: Marking,
    parent: Option<(usize, usize, u64)>,
    depth: u64,
    preferred: bool,
    plan: Option<Plan>,
    expanded: bool,
}

fn accepts(p: &Problem, marking: &[(usize, u64)]) -> Result<bool, &'static str> {
    for c in &p.target {
        let value = marking
            .iter()
            .try_fold(0i128, |sum, &(place, count)| {
                sum.checked_add(i128::from(c.coefficients[place]) * i128::from(count))
            })
            .ok_or("target arithmetic overflow")?;
        if (c.equality && value != i128::from(c.bound))
            || (!c.equality && value < i128::from(c.bound))
        {
            return Ok(false);
        }
    }
    Ok(true)
}

fn witness(p: &Problem, nodes: &[Node], id: usize) -> Outcome {
    let mut trace = vec![];
    let mut back = id;
    while let Some((parent, t, repeats)) = nodes[back].parent {
        trace.extend(std::iter::repeat_n(t, repeats as usize));
        back = parent;
    }
    trace.reverse();
    match p.check_witness(&trace) {
        Ok(marking) => Outcome {
            verdict: "reachable",
            method: "relaxed".into(),
            reason: "independently replayed witness".into(),
            states: nodes.len(),
            trace,
            marking: Some(marking),
            certificate: None,
            proof: None,
        },
        Err(e) => Outcome::unknown(
            "relaxed",
            &format!("witness check failed: {e}"),
            nodes.len(),
        ),
    }
}

fn pop(queue: &mut Queue, nodes: &[Node]) -> Option<usize> {
    while let Some(Reverse((score, _, id))) = queue.pop() {
        if !nodes[id].expanded
            && nodes[id]
                .plan
                .as_ref()
                .is_none_or(|plan| plan.score == score)
        {
            return Some(id);
        }
    }
    None
}
fn enqueue(all: &mut Queue, preferred: &mut Queue, node: &Node, id: usize, score: u64) {
    let entry = Reverse((score, u64::MAX - node.depth, id));
    all.push(entry);
    if node.preferred {
        preferred.push(entry);
    }
}

/// Exact sparse-state witness search over a static backward relevance slice.
/// Keep target-changing transitions and recursively their guard producers.
/// Exhaustion, limits, overflow, and heuristic dead ends never prove unreachability.
pub fn solve(p: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    run(p, timeout, max_states, false, Reduction::Off, false)
}

/// Helpful-action restriction is a positive search heuristic, never a refutation.
/// If it fails, retain the full search within the same deadline.
pub fn solve_focused(p: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    focused_with_fallback(p, timeout, max_states, Reduction::Off, false)
}

/// Same helpful-action attempt and budget as `solve_focused`, followed by
/// unrestricted search with reachability-preserving stubborn-set reduction.
pub fn solve_stubborn(p: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    focused_with_fallback(p, timeout, max_states, Reduction::Invisible, false)
}

/// Target-directed closure seeds every improving alternative, including disabled actions.
pub fn solve_target_stubborn(p: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    focused_with_fallback(p, timeout, max_states, Reduction::TargetDirected, false)
}

/// Adds finite repeated-transition successors; every answer is replayed normally.
pub fn solve_batched(p: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    let mut result = focused_with_fallback(p, timeout, max_states, Reduction::Off, true);
    result.method = "relaxed-batched".into();
    result
}

fn focused_with_fallback(
    p: &Problem,
    timeout: Duration,
    max_states: usize,
    reduction: Reduction,
    batched: bool,
) -> Outcome {
    let start = Instant::now();
    let mut result = run(p, timeout / 3, max_states, true, Reduction::Off, batched);
    if result.verdict == "unknown" {
        result = run(
            p,
            timeout.saturating_sub(start.elapsed()),
            max_states,
            false,
            reduction,
            batched,
        );
    }
    result.method = match reduction {
        Reduction::Off => "relaxed-focused",
        Reduction::Invisible => "relaxed-stubborn",
        Reduction::TargetDirected => "relaxed-target-stubborn",
    }
    .into();
    result
}

fn run(
    p: &Problem,
    timeout: Duration,
    max_states: usize,
    focused: bool,
    reduction: Reduction,
    batched: bool,
) -> Outcome {
    let start = Instant::now();
    let deadline = start + timeout;
    let mut stats = Diagnostics::new(focused, reduction);
    if let Err(e) = p.validate() {
        return Outcome::unknown("relaxed", &e.to_string(), 0);
    }
    let marking: Marking = p
        .initial
        .iter()
        .copied()
        .enumerate()
        .filter(|&(_, n)| n != 0)
        .collect::<Vec<_>>()
        .into();
    let mut nodes = vec![Node {
        marking,
        parent: None,
        depth: 0,
        preferred: true,
        plan: None,
        expanded: false,
    }];
    match accepts(p, &nodes[0].marking) {
        Ok(true) => return witness(p, &nodes, 0),
        Ok(false) => {}
        Err(e) => return Outcome::unknown("relaxed", e, 1),
    }
    let Some(graph) = Graph::new(p, start, timeout) else {
        return Outcome::unknown("relaxed", "time limit", 1);
    };
    let mut reduction = match reduction {
        Reduction::Off => None,
        Reduction::Invisible => {
            let Some(index) = Stubborn::new(&graph, p, deadline) else {
                return Outcome::unknown("relaxed", "time limit", 1);
            };
            Some(ReductionIndex::Invisible(index))
        }
        Reduction::TargetDirected => {
            let Some(index) = TargetStubborn::new(&graph, p, deadline) else {
                return Outcome::unknown("relaxed", "time limit", 1);
            };
            Some(ReductionIndex::TargetDirected(index))
        }
    };
    nodes[0].marking = nodes[0]
        .marking
        .iter()
        .copied()
        .filter(|&(place, _)| graph.retained_places[place])
        .collect::<Vec<_>>()
        .into();
    let mut seen = HashSet::from([nodes[0].marking.clone()]);
    let mut all = Queue::new();
    let mut preferred = Queue::new();
    enqueue(&mut all, &mut preferred, &nodes[0], 0, 0);
    let mut fifo = 0;
    let mut iteration = 0usize;
    loop {
        if start.elapsed() >= timeout {
            return Outcome::unknown("relaxed", "time limit", nodes.len());
        }
        while fifo < nodes.len() && nodes[fifo].expanded {
            fifo += 1;
        }
        if fifo == nodes.len() {
            return Outcome::unknown(
                "relaxed",
                "search exhausted; no negative certificate",
                nodes.len(),
            );
        }
        iteration = iteration.wrapping_add(1);
        let id = if iteration.is_multiple_of(32) {
            fifo
        } else if iteration.is_multiple_of(4) {
            pop(&mut all, &nodes).unwrap_or(fifo)
        } else {
            pop(&mut preferred, &nodes)
                .or_else(|| pop(&mut all, &nodes))
                .unwrap_or(fifo)
        };
        if nodes[id].plan.is_none() {
            let Some(plan) = graph.plan(p, &nodes[id].marking, start, timeout) else {
                return Outcome::unknown("relaxed", "time limit", nodes.len());
            };
            let score = plan.score;
            nodes[id].plan = Some(plan);
            enqueue(&mut all, &mut preferred, &nodes[id], id, score);
            continue;
        }
        nodes[id].expanded = true;
        stats.expanded += 1;
        let plan = nodes[id].plan.take().unwrap();
        let marking = nodes[id].marking.clone();
        // Helpful transitions are generated first so the state cap preserves their successors.
        let mut order = plan.helpful.iter().copied().chain(
            plan.enabled
                .iter()
                .copied()
                .filter(|t| !focused && plan.helpful.binary_search(t).is_err()),
        );
        let selected: Vec<_> = if let Some(index) = &mut reduction {
            let mut enabled = Vec::new();
            for t in order.by_ref() {
                if start.elapsed() >= timeout {
                    return Outcome::unknown("relaxed", "time limit", nodes.len());
                }
                if graph.actions[t].guards.iter().all(|&g| {
                    let (place, weight) = graph.facts[g];
                    tokens(&marking, place) >= weight
                }) {
                    stats.enabled_considered += 1;
                    enabled.push(t);
                }
            }
            let selection = match index {
                ReductionIndex::Invisible(index) => {
                    index.select(&marking, &enabled, nodes[id].depth, &seen, deadline)
                }
                ReductionIndex::TargetDirected(index) => {
                    let selection = index.select(p, &marking, &enabled, deadline);
                    stats.target_selection = index.stats.clone();
                    Ok(selection)
                }
            };
            match selection {
                Ok(Selection::TargetReduced(actions)) => {
                    stats.reductions += 1;
                    actions.into_iter().map(|t| (t, None)).collect()
                }
                Ok(Selection::Reduced(successors)) => {
                    stats.reductions += 1;
                    successors
                        .into_iter()
                        .map(|(t, next)| (t, Some(next)))
                        .collect()
                }
                Ok(Selection::Full(reason)) => {
                    stats.full(reason);
                    enabled.into_iter().map(|t| (t, None)).collect()
                }
                Err(e) => return Outcome::unknown("relaxed", e, nodes.len()),
            }
        } else {
            Vec::new()
        };
        for (t, cached) in selected.into_iter().chain(order.map(|t| (t, None))) {
            if start.elapsed() >= timeout {
                return Outcome::unknown("relaxed", "time limit", nodes.len());
            }
            let repetitions = if batched {
                graph.repetitions(
                    p,
                    &marking,
                    t,
                    BATCHED_TRACE_LIMIT.saturating_sub(nodes[id].depth),
                    deadline,
                )
            } else {
                Vec::new()
            };
            for repeats in std::iter::once(1).chain(repetitions) {
                if Instant::now() >= deadline {
                    return Outcome::unknown("relaxed", "time limit", nodes.len());
                }
                let Some(depth) = nodes[id].depth.checked_add(repeats) else {
                    return Outcome::unknown("relaxed", "discovery depth overflow", nodes.len());
                };
                let next = match cached.clone().filter(|_| repeats == 1).map_or_else(
                    || graph.fire_many(&marking, t, repeats),
                    |next| Ok(Some(next)),
                ) {
                    Ok(Some(next)) => next,
                    Ok(None) => continue,
                    Err(e) => return Outcome::unknown("relaxed", e, nodes.len()),
                };
                stats.chosen += 1;
                if reduction.is_none() {
                    stats.enabled_considered += 1;
                }
                if seen.contains(&next) {
                    continue;
                }
                if nodes.len() >= max_states {
                    return Outcome::unknown("relaxed", "state limit", nodes.len());
                }
                let accepted = match accepts(p, &next) {
                    Ok(accepted) => accepted,
                    Err(e) => return Outcome::unknown("relaxed", e, nodes.len()),
                };
                stats.generated += 1;
                seen.insert(next.clone());
                let child = nodes.len();
                nodes.push(Node {
                    marking: next,
                    parent: Some((id, graph.actions[t].original, repeats)),
                    depth,
                    preferred: plan.helpful.binary_search(&t).is_ok(),
                    plan: None,
                    expanded: false,
                });
                if accepted {
                    return witness(p, &nodes, child);
                }
                enqueue(&mut all, &mut preferred, &nodes[child], child, plan.score);
            }
        }
    }
}
