//! Backward antichain search for a necessary upward-closed target.
use crate::{model::Problem, search::Outcome};
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::{
    cmp::Reverse,
    collections::{BTreeMap, BinaryHeap},
    time::{Duration, Instant},
};

type Marking = Vec<(usize, u64)>;
const MAX_BASIS: usize = 20_000;

#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Requirement {
    pub target_row: usize,
    pub sign: i8,
    pub place: usize,
    pub required: u64,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Certificate {
    pub kind: String,
    pub requirements: Vec<Requirement>,
    pub basis: Vec<Marking>,
}

struct Work {
    deadline: Instant,
    remaining: usize,
}

impl Work {
    fn take(&mut self, amount: usize) -> Result<()> {
        ensure!(Instant::now() < self.deadline, "backward cover deadline");
        self.remaining = self
            .remaining
            .checked_sub(amount)
            .context("backward cover work limit")?;
        Ok(())
    }
}

fn goal(problem: &Problem, requirements: &[Requirement], work: &mut Work) -> Result<Marking> {
    ensure!(!requirements.is_empty(), "missing target requirements");
    let mut result = BTreeMap::<usize, u64>::new();
    for r in requirements {
        let row = problem
            .target
            .get(r.target_row)
            .context("invalid target row")?;
        ensure!(
            r.sign == 1 || (r.sign == -1 && row.equality),
            "invalid target sign"
        );
        ensure!(r.place < problem.places.len(), "invalid required place");
        let sign = i128::from(r.sign);
        let coefficient = sign * i128::from(row.coefficients[r.place]);
        let bound = sign * i128::from(row.bound);
        ensure!(
            coefficient > 0 && bound > 0,
            "target has no positive requirement"
        );
        for (place, &value) in row.coefficients.iter().enumerate() {
            work.take(1)?;
            ensure!(
                place == r.place || sign * i128::from(value) <= 0,
                "target has another positive coefficient"
            );
        }
        let required = u64::try_from((bound + coefficient - 1) / coefficient)?;
        ensure!(r.required == required, "incorrect target requirement");
        result
            .entry(r.place)
            .and_modify(|n| *n = (*n).max(required))
            .or_insert(required);
    }
    Ok(result.into_iter().collect())
}

fn requirements(problem: &Problem, work: &mut Work) -> Result<Vec<Requirement>> {
    let mut result = Vec::new();
    for (target_row, row) in problem.target.iter().enumerate() {
        for &sign in if row.equality {
            &[1i8, -1][..]
        } else {
            &[1i8][..]
        } {
            let bound = i128::from(sign) * i128::from(row.bound);
            if bound <= 0 {
                continue;
            }
            let mut positive = None;
            let mut multiple = false;
            for (place, &value) in row.coefficients.iter().enumerate() {
                work.take(1)?;
                let value = i128::from(sign) * i128::from(value);
                if value > 0 && positive.replace((place, value)).is_some() {
                    multiple = true;
                    break;
                }
            }
            if !multiple && let Some((place, coefficient)) = positive {
                result.push(Requirement {
                    target_row,
                    sign,
                    place,
                    required: u64::try_from((bound + coefficient - 1) / coefficient)?,
                });
            }
        }
    }
    Ok(result)
}

struct Transition {
    arcs: Vec<(usize, u64, u64)>,
}

struct Index {
    transitions: Vec<Transition>,
    producers: Vec<Vec<usize>>,
    token_bound: Option<u128>,
}

impl Index {
    fn new(problem: &Problem, work: &mut Work) -> Result<Self> {
        let mut producers = vec![Vec::new(); problem.places.len()];
        let mut transitions = Vec::new();
        let mut conservative = true;
        for (t, transition) in problem.transitions.iter().enumerate() {
            work.take(1)?;
            let mut arcs = BTreeMap::<usize, (u64, u64)>::new();
            let mut input = 0u128;
            let mut output = 0u128;
            for &(place, weight) in &transition.pre {
                work.take(1)?;
                arcs.entry(place).or_default().0 = weight;
                input = input
                    .checked_add(u128::from(weight))
                    .context("input mass overflow")?;
            }
            for &(place, weight) in &transition.post {
                work.take(1)?;
                arcs.entry(place).or_default().1 = weight;
                output = output
                    .checked_add(u128::from(weight))
                    .context("output mass overflow")?;
            }
            conservative &= output <= input;
            let arcs = arcs
                .into_iter()
                .map(|(place, (pre, post))| {
                    if post > pre {
                        producers[place].push(t);
                    }
                    (place, pre, post)
                })
                .collect();
            transitions.push(Transition { arcs });
        }
        let mut initial_mass = 0u128;
        for &value in &problem.initial {
            work.take(1)?;
            initial_mass = initial_mass
                .checked_add(u128::from(value))
                .context("initial mass overflow")?;
        }
        Ok(Self {
            transitions,
            producers,
            token_bound: conservative.then_some(initial_mass),
        })
    }

    fn candidates(&self, marking: &Marking, work: &mut Work) -> Result<Vec<usize>> {
        let mut result = Vec::new();
        for &(place, _) in marking {
            work.take(self.producers[place].len().saturating_add(1))?;
            result.extend_from_slice(&self.producers[place]);
        }
        work.take(
            result
                .len()
                .saturating_mul(result.len().checked_ilog2().unwrap_or(0) as usize + 1),
        )?;
        result.sort_unstable();
        result.dedup();
        Ok(result)
    }

    fn outside(&self, marking: &Marking, work: &mut Work) -> Result<bool> {
        let Some(bound) = self.token_bound else {
            return Ok(false);
        };
        let mut mass = 0u128;
        for &(_, value) in marking {
            work.take(1)?;
            mass = mass
                .checked_add(u128::from(value))
                .context("required mass overflow")?;
            if mass > bound {
                return Ok(true);
            }
        }
        Ok(false)
    }

    fn predecessor(&self, marking: &Marking, t: usize, work: &mut Work) -> Result<Option<Marking>> {
        let mut marking = marking.iter().peekable();
        let mut arcs = self.transitions[t].arcs.iter().peekable();
        let mut result = Vec::new();
        let mut mass = 0u128;
        while marking.peek().is_some() || arcs.peek().is_some() {
            work.take(1)?;
            let place = match (marking.peek(), arcs.peek()) {
                (Some(a), Some(b)) => a.0.min(b.0),
                (Some(a), None) => a.0,
                (None, Some(b)) => b.0,
                _ => unreachable!(),
            };
            let required = if marking.peek().is_some_and(|entry| entry.0 == place) {
                marking.next().unwrap().1
            } else {
                0
            };
            let (pre, post) = if arcs.peek().is_some_and(|entry| entry.0 == place) {
                let &(_, pre, post) = arcs.next().unwrap();
                (pre, post)
            } else {
                (0, 0)
            };
            let value = u128::from(pre) + u128::from(required.saturating_sub(post));
            mass = mass
                .checked_add(value)
                .context("predecessor mass overflow")?;
            if self.token_bound.is_some_and(|bound| mass > bound) {
                return Ok(None);
            }
            if value > 0 {
                result.push((
                    place,
                    u64::try_from(value).context("predecessor coordinate overflow")?,
                ));
            }
        }
        Ok(Some(result))
    }
}

fn dominates(marking: &Marking, lower: &Marking, work: &mut Work) -> Result<bool> {
    let mut i = 0;
    for &(place, required) in lower {
        work.take(1)?;
        while i < marking.len() && marking[i].0 < place {
            work.take(1)?;
            i += 1;
        }
        if i == marking.len() || marking[i].0 != place || marking[i].1 < required {
            return Ok(false);
        }
    }
    Ok(true)
}

fn covered(marking: &Marking, basis: &[Marking], work: &mut Work) -> Result<bool> {
    for lower in basis {
        work.take(1)?;
        if dominates(marking, lower, work)? {
            return Ok(true);
        }
    }
    Ok(false)
}

fn initial(problem: &Problem) -> Marking {
    problem
        .initial
        .iter()
        .enumerate()
        .filter_map(|(p, &n)| (n != 0).then_some((p, n)))
        .collect()
}

fn verify_inner(
    problem: &Problem,
    certificate: &Certificate,
    index: &Index,
    work: &mut Work,
) -> Result<()> {
    ensure!(
        certificate.kind == "backward-cover-v1",
        "invalid backward cover kind"
    );
    ensure!(
        certificate.basis.len() <= MAX_BASIS,
        "backward cover basis size limit"
    );
    let goal = goal(problem, &certificate.requirements, work)?;
    for marking in &certificate.basis {
        let mut previous = None;
        for &(place, value) in marking {
            work.take(1)?;
            ensure!(
                place < problem.places.len() && value > 0 && previous.is_none_or(|p| p < place),
                "invalid sparse marking"
            );
            previous = Some(place);
        }
    }
    ensure!(
        !covered(&initial(problem), &certificate.basis, work)?,
        "initial marking reaches backward cover"
    );
    ensure!(
        index.outside(&goal, work)? || covered(&goal, &certificate.basis, work)?,
        "backward cover omits goal"
    );
    for marking in &certificate.basis {
        for t in index.candidates(marking, work)? {
            if let Some(predecessor) = index.predecessor(marking, t, work)? {
                ensure!(
                    covered(&predecessor, &certificate.basis, work)?,
                    "backward cover is not closed"
                );
            }
        }
    }
    work.take(0)
}

pub fn verify(problem: &Problem, value: &Value, deadline: Instant) -> Result<()> {
    problem.validate()?;
    let certificate: Certificate = serde_json::from_value(value.clone())?;
    let mut work = Work {
        deadline,
        remaining: 200_000_000,
    };
    let index = Index::new(problem, &mut work)?;
    verify_inner(problem, &certificate, &index, &mut work)
}

struct Node {
    marking: Marking,
    step: Option<(usize, usize)>,
    active: bool,
}

fn priority(marking: &Marking, problem: &Problem) -> u128 {
    marking
        .iter()
        .map(|&(place, value)| u128::from(value.saturating_sub(problem.initial[place])))
        .sum()
}

fn discover(problem: &Problem, max_states: usize, work: &mut Work) -> Result<Outcome> {
    let requirements = requirements(problem, work)?;
    let goal = goal(problem, &requirements, work)?;
    let index = Index::new(problem, work)?;
    let start = initial(problem);
    let mut nodes = Vec::<Node>::new();
    let mut queue = BinaryHeap::new();
    if !index.outside(&goal, work)? {
        queue.push(Reverse((priority(&goal, problem), 0usize)));
        nodes.push(Node {
            marking: goal,
            step: None,
            active: true,
        });
    }
    while let Some(Reverse((_, id))) = queue.pop() {
        work.take(1)?;
        if !nodes[id].active {
            continue;
        }
        if dominates(&start, &nodes[id].marking, work)? {
            let mut trace = Vec::new();
            let mut back = id;
            while let Some((t, next)) = nodes[back].step {
                work.take(1)?;
                trace.push(t);
                back = next;
            }
            let marking = problem
                .check_witness(&trace)
                .context("necessary target reached but full target is not satisfied")?;
            work.take(0)?;
            let mut out = Outcome::unknown(
                "backward-cover",
                "backward cover witness replayed",
                nodes.len(),
            );
            out.verdict = "reachable";
            out.trace = trace;
            out.marking = Some(marking);
            return Ok(out);
        }
        for t in index.candidates(&nodes[id].marking, work)? {
            let Some(predecessor) = index.predecessor(&nodes[id].marking, t, work)? else {
                continue;
            };
            let mut redundant = false;
            for node in &nodes {
                work.take(1)?;
                if node.active && dominates(&predecessor, &node.marking, work)? {
                    redundant = true;
                    break;
                }
            }
            if redundant {
                continue;
            }
            ensure!(
                nodes.len() < max_states.min(MAX_BASIS),
                "backward cover state limit"
            );
            for node in &mut nodes {
                work.take(1)?;
                if node.active && dominates(&node.marking, &predecessor, work)? {
                    node.active = false;
                }
            }
            let next = nodes.len();
            queue.push(Reverse((priority(&predecessor, problem), next)));
            nodes.push(Node {
                marking: predecessor,
                step: Some((t, id)),
                active: true,
            });
        }
    }
    let states = nodes.len();
    let certificate = Certificate {
        kind: "backward-cover-v1".into(),
        requirements,
        basis: nodes
            .into_iter()
            .filter_map(|node| node.active.then_some(node.marking))
            .collect(),
    };
    verify_inner(problem, &certificate, &index, work)?;
    let mut out = Outcome::unknown(
        "backward-cover",
        "closed backward cover excludes initial marking",
        states,
    );
    out.verdict = "unreachable";
    out.proof = Some(serde_json::to_value(certificate)?);
    work.take(0)?;
    Ok(out)
}

pub fn solve(problem: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    let mut work = Work {
        deadline: Instant::now() + timeout,
        remaining: max_states.saturating_mul(1000).min(200_000_000),
    };
    if problem.validate().is_err() || max_states == 0 {
        return Outcome::unknown("backward-cover", "invalid problem or exhausted budget", 0);
    }
    discover(problem, max_states, &mut work)
        .unwrap_or_else(|e| Outcome::unknown("backward-cover", &e.to_string(), 0))
}
