//! Positive-only random walks with incremental weighted enabledness.
//!
//! `max_steps` counts firings across restarts, not distinct markings. Witness
//! replay uses the original checker; a late replay returns Unknown, but the
//! checker itself is not interruptible, so hard wall limits require a caller.
use crate::{model::Problem, search::Outcome};
use std::time::{Duration, Instant};

#[path = "walk_guidance.rs"]
mod guidance;
use guidance::Guidance;

pub const DEFAULT_SEED: u64 = 0;
pub const DEFAULT_RESTART_STEPS: usize = 10_000;
pub const MAX_TRACE_STEPS: usize = 100_000;

#[derive(Clone, Copy)]
pub struct Options {
    pub seed: u64,
    pub restart_steps: usize,
}

impl Default for Options {
    fn default() -> Self {
        Self {
            seed: DEFAULT_SEED,
            restart_steps: DEFAULT_RESTART_STEPS,
        }
    }
}

struct Random(u64);

impl Random {
    fn next(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9e3779b97f4a7c15);
        let mut value = self.0;
        value = (value ^ (value >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
        value = (value ^ (value >> 27)).wrapping_mul(0x94d049bb133111eb);
        value ^ (value >> 31)
    }

    fn index(&mut self, count: usize) -> usize {
        let bound = count as u64;
        let threshold = bound.wrapping_neg() % bound;
        loop {
            let value = self.next();
            if value >= threshold {
                return (value % bound) as usize;
            }
        }
    }
}

struct Target {
    terms: Vec<(usize, i64)>,
    bound: i64,
    equality: bool,
}

struct Index {
    users: Vec<Vec<(usize, u64)>>,
    guard_ranges: Vec<(u64, u64)>,
    effects: Vec<Vec<(usize, i128)>>,
    targets: Vec<Target>,
}

fn within(deadline: Instant) -> Result<(), &'static str> {
    if Instant::now() >= deadline {
        Err("time limit")
    } else {
        Ok(())
    }
}

impl Index {
    fn new(p: &Problem, deadline: Instant) -> Result<Self, &'static str> {
        let mut users = vec![Vec::new(); p.places.len()];
        let mut guard_ranges = vec![(u64::MAX, 0); p.places.len()];
        let mut effects = Vec::with_capacity(p.transitions.len());
        for (t, transition) in p.transitions.iter().enumerate() {
            within(deadline)?;
            let mut entries = Vec::with_capacity(transition.pre.len() + transition.post.len());
            for &(place, weight) in &transition.pre {
                within(deadline)?;
                users[place].push((t, weight));
                let (minimum, maximum) = &mut guard_ranges[place];
                *minimum = (*minimum).min(weight);
                *maximum = (*maximum).max(weight);
                entries.push((place, -i128::from(weight)));
            }
            for &(place, weight) in &transition.post {
                within(deadline)?;
                entries.push((place, i128::from(weight)));
            }
            entries.sort_unstable_by_key(|&(place, _)| place);
            let mut delta: Vec<(usize, i128)> = Vec::with_capacity(entries.len());
            for (place, effect) in entries {
                within(deadline)?;
                if let Some(last) = delta.last_mut().filter(|last| last.0 == place) {
                    last.1 += effect;
                } else {
                    delta.push((place, effect));
                }
            }
            delta.retain(|&(_, effect)| effect != 0);
            effects.push(delta);
        }
        let mut targets = Vec::with_capacity(p.target.len());
        for target in &p.target {
            let mut terms = Vec::new();
            for (place, &coefficient) in target.coefficients.iter().enumerate() {
                within(deadline)?;
                if coefficient != 0 {
                    terms.push((place, coefficient));
                }
            }
            targets.push(Target {
                terms,
                bound: target.bound,
                equality: target.equality,
            });
        }
        Ok(Self {
            users,
            guard_ranges,
            effects,
            targets,
        })
    }

    fn accepts(&self, marking: &[u64], deadline: Instant) -> Result<bool, &'static str> {
        for target in &self.targets {
            within(deadline)?;
            let mut value = 0i128;
            for &(place, coefficient) in &target.terms {
                within(deadline)?;
                value = value
                    .checked_add(i128::from(coefficient) * i128::from(marking[place]))
                    .ok_or("target arithmetic overflow")?;
            }
            if (target.equality && value != i128::from(target.bound))
                || (!target.equality && value < i128::from(target.bound))
            {
                return Ok(false);
            }
        }
        Ok(true)
    }
}

struct State {
    marking: Vec<u64>,
    missing: Vec<usize>,
    enabled: Vec<usize>,
    position: Vec<usize>,
    changes: Vec<(usize, u64)>,
}

impl State {
    fn new(p: &Problem, index: &Index, deadline: Instant) -> Result<Self, &'static str> {
        let mut state = Self {
            marking: p.initial.clone(),
            missing: vec![0; p.transitions.len()],
            enabled: Vec::with_capacity(p.transitions.len()),
            position: vec![usize::MAX; p.transitions.len()],
            changes: Vec::new(),
        };
        state.reset(p, index, deadline)?;
        Ok(state)
    }

    fn reset(&mut self, p: &Problem, index: &Index, deadline: Instant) -> Result<(), &'static str> {
        self.marking.clone_from(&p.initial);
        self.missing.fill(0);
        self.enabled.clear();
        self.position.fill(usize::MAX);
        self.changes.clear();
        for (place, users) in index.users.iter().enumerate() {
            within(deadline)?;
            for &(t, weight) in users {
                within(deadline)?;
                self.missing[t] += usize::from(self.marking[place] < weight);
            }
        }
        for t in 0..self.missing.len() {
            within(deadline)?;
            if self.missing[t] == 0 {
                self.enable(t);
            }
        }
        Ok(())
    }

    fn enable(&mut self, t: usize) {
        debug_assert_eq!(self.position[t], usize::MAX);
        self.position[t] = self.enabled.len();
        self.enabled.push(t);
    }

    fn disable(&mut self, t: usize) {
        let position = self.position[t];
        debug_assert_ne!(position, usize::MAX);
        self.enabled.swap_remove(position);
        if position < self.enabled.len() {
            self.position[self.enabled[position]] = position;
        }
        self.position[t] = usize::MAX;
    }

    fn fire(&mut self, index: &Index, t: usize, deadline: Instant) -> Result<(), &'static str> {
        if self.missing[t] != 0 {
            return Err("internal enabledness mismatch");
        }
        self.changes.clear();
        // Check all outputs before mutation so overflow cannot corrupt a restart.
        for &(place, effect) in &index.effects[t] {
            within(deadline)?;
            let next = u64::try_from(i128::from(self.marking[place]) + effect)
                .map_err(|_| "counter overflow")?;
            self.changes.push((place, next));
        }
        for i in 0..self.changes.len() {
            let (place, next) = self.changes[i];
            let previous = self.marking[place];
            self.marking[place] = next;
            let (minimum, maximum) = index.guard_ranges[place];
            if previous.min(next) >= maximum || previous.max(next) < minimum {
                continue;
            }
            for &(user, weight) in &index.users[place] {
                within(deadline)?;
                let before = previous < weight;
                let after = next < weight;
                if before == after {
                    continue;
                }
                if after {
                    if self.missing[user] == 0 {
                        self.disable(user);
                    }
                    self.missing[user] += 1;
                } else {
                    self.missing[user] -= 1;
                    if self.missing[user] == 0 {
                        self.enable(user);
                    }
                }
            }
        }
        within(deadline)
    }
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum Policy {
    Uniform,
    Incremental,
    Guided,
}

impl Policy {
    fn method(self) -> &'static str {
        match self {
            Self::Uniform => "walk",
            Self::Incremental => "walk-incremental",
            Self::Guided => "walk-guided",
        }
    }
}

struct Run {
    policy: Policy,
    options: Options,
    steps: usize,
    restarts: usize,
}

impl Run {
    fn reason(&self, reason: &str) -> String {
        let policy = match self.policy {
            Policy::Uniform => "",
            Policy::Incremental => "; incremental_targets=true",
            Policy::Guided => "; incremental_targets=true; candidates=8; uniform_probability=1/5",
        };
        format!(
            "{reason}; seed={}; restart_steps={}; trace_limit={MAX_TRACE_STEPS}; steps={}; restarts={}{policy}",
            self.options.seed, self.options.restart_steps, self.steps, self.restarts
        )
    }

    fn unknown(&self, reason: &str) -> Outcome {
        Outcome::unknown(self.policy.method(), &self.reason(reason), self.steps)
    }

    fn witness(&self, p: &Problem, trace: Vec<usize>, deadline: Instant) -> Outcome {
        if within(deadline).is_err() {
            return self.unknown("time limit before witness replay");
        }
        let checked = p.check_witness(&trace);
        if within(deadline).is_err() {
            return self.unknown("time limit during witness replay");
        }
        match checked {
            Ok(marking) => Outcome {
                verdict: "reachable",
                method: self.policy.method().into(),
                reason: self.reason("original-net witness replayed"),
                states: self.steps,
                trace,
                marking: Some(marking),
                certificate: None,
                proof: None,
            },
            Err(error) => self.unknown(&format!("witness check failed: {error}")),
        }
    }
}

/// Walk the original net. Restarts discard only the current trace; all attempted
/// firings consume `max_steps`, including an overflowing firing. Trace length is
/// capped independently, and hitting that cap restarts rather than refutes.
pub fn solve(p: &Problem, timeout: Duration, max_steps: usize, options: Options) -> Outcome {
    solve_policy(p, timeout, max_steps, options, Policy::Uniform)
}

pub fn solve_incremental(
    p: &Problem,
    timeout: Duration,
    max_steps: usize,
    options: Options,
) -> Outcome {
    solve_policy(p, timeout, max_steps, options, Policy::Incremental)
}

pub fn solve_guided(p: &Problem, timeout: Duration, max_steps: usize, options: Options) -> Outcome {
    solve_policy(p, timeout, max_steps, options, Policy::Guided)
}

fn solve_policy(
    p: &Problem,
    timeout: Duration,
    max_steps: usize,
    options: Options,
    policy: Policy,
) -> Outcome {
    let start = Instant::now();
    let mut run = Run {
        policy,
        options,
        steps: 0,
        restarts: 0,
    };
    let Some(deadline) = start.checked_add(timeout) else {
        return run.unknown("invalid time limit");
    };
    if options.restart_steps == 0 {
        return run.unknown("restart step limit must be positive");
    }
    if within(deadline).is_err() {
        return run.unknown("time limit");
    }
    if let Err(error) = p.validate() {
        return run.unknown(&format!("invalid problem: {error}"));
    }
    if within(deadline).is_err() {
        return run.unknown("time limit during input validation");
    }
    match p.accepts(&p.initial) {
        Ok(true) => return run.witness(p, Vec::new(), deadline),
        Ok(false) => {}
        Err(error) => return run.unknown(&error.to_string()),
    }
    if max_steps == 0 {
        return run.unknown("step limit");
    }
    let index = match Index::new(p, deadline) {
        Ok(index) => index,
        Err(reason) => return run.unknown(reason),
    };
    let mut guidance = if policy == Policy::Uniform {
        None
    } else {
        match Guidance::new(&index, &p.initial, deadline) {
            Ok(guidance) => Some(guidance),
            Err(reason) => return run.unknown(reason),
        }
    };
    let mut state = match State::new(p, &index, deadline) {
        Ok(state) => state,
        Err(reason) => return run.unknown(reason),
    };
    if state.enabled.is_empty() {
        return run.unknown("initial deadlock; no negative certificate");
    }
    let trace_limit = options.restart_steps.min(MAX_TRACE_STEPS);
    let mut trace = Vec::with_capacity(trace_limit.min(max_steps));
    let mut random = Random(options.seed);
    loop {
        if within(deadline).is_err() {
            return run.unknown("time limit");
        }
        if run.steps == max_steps {
            return run.unknown("step limit");
        }
        if state.enabled.is_empty() || trace.len() == trace_limit {
            if let Err(reason) = state.reset(p, &index, deadline) {
                return run.unknown(reason);
            }
            if let Some(guidance) = guidance.as_mut()
                && let Err(reason) = guidance.reset(&index, &p.initial, deadline)
            {
                return run.unknown(reason);
            }
            trace.clear();
            run.restarts += 1;
        }
        let t = if policy == Policy::Guided {
            match guidance
                .as_mut()
                .unwrap()
                .select(&index, &state.enabled, &mut random, deadline)
            {
                Ok(t) => t,
                Err(reason) => return run.unknown(reason),
            }
        } else {
            state.enabled[random.index(state.enabled.len())]
        };
        run.steps += 1;
        if let Err(reason) = state.fire(&index, t, deadline) {
            return run.unknown(reason);
        }
        trace.push(t);
        let accepted = if let Some(guidance) = guidance.as_mut() {
            guidance
                .fired(&index, t, deadline)
                .and_then(|()| guidance.accepts(&index, deadline))
        } else {
            index.accepts(&state.marking, deadline)
        };
        match accepted {
            Ok(true) => return run.witness(p, trace, deadline),
            Ok(false) => {}
            Err(reason) => return run.unknown(reason),
        }
    }
}

#[cfg(test)]
#[path = "walk_tests.rs"]
mod tests;
