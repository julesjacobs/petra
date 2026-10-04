//! Causal splits over firing counts, with exact arithmetic proof leaves.
use crate::{
    count_plan::{Realization, realize},
    linear::{Row, System, state_equation},
    model::Problem,
    search::Outcome,
};
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use std::time::{Duration, Instant};

const MAX_DEPTH: usize = 96;

#[derive(Debug, Serialize, Deserialize)]
#[serde(tag = "rule", rename_all = "snake_case", deny_unknown_fields)]
pub enum Node {
    Farkas {
        multipliers: Vec<(usize, String)>,
    },
    Support {
        places: Vec<usize>,
        blocked: usize,
        omit: Box<Node>,
        enter: Box<Node>,
    },
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Certificate {
    pub kind: String,
    pub root: Node,
}

fn split(p: &Problem, places: &[usize], blocked: usize) -> Result<(Row, Row)> {
    let mut inside = vec![false; p.places.len()];
    let mut previous = None;
    for &place in places {
        ensure!(previous.is_none_or(|i| i < place), "unordered support set");
        *inside.get_mut(place).context("invalid support place")? = true;
        previous = Some(place);
    }
    ensure!(
        p.initial.iter().zip(&inside).all(|(&m, &s)| m == 0 || s),
        "support omits initially marked place"
    );
    let transition = p
        .transitions
        .get(blocked)
        .context("invalid blocked transition")?;
    ensure!(
        transition.pre.iter().any(|&(i, _)| !inside[i]),
        "transition is not blocked"
    );
    let frontier = p
        .transitions
        .iter()
        .enumerate()
        .filter(|(_, t)| {
            t.pre.iter().all(|&(i, _)| inside[i]) && t.post.iter().any(|&(i, _)| !inside[i])
        })
        .map(|(i, _)| (i, 1.into()))
        .collect();
    Ok((
        Row {
            coefficients: vec![(blocked, (-1).into())],
            bound: 0.into(),
        },
        Row {
            coefficients: frontier,
            bound: 1.into(),
        },
    ))
}

fn check_node(p: &Problem, system: &mut System, node: &Node, depth: usize) -> Result<()> {
    ensure!(depth <= MAX_DEPTH, "causal proof depth limit");
    match node {
        Node::Farkas { multipliers } => system.check(multipliers),
        Node::Support {
            places,
            blocked,
            omit,
            enter,
        } => {
            let (omit_row, enter_row) = split(p, places, *blocked)?;
            for (row, child) in [(omit_row, omit), (enter_row, enter)] {
                system.rows.push(row);
                let result = check_node(p, system, child, depth + 1);
                system.rows.pop();
                result?;
            }
            Ok(())
        }
    }
}

pub fn verify_certificate(p: &Problem, value: &serde_json::Value) -> Result<()> {
    p.validate()?;
    let certificate: Certificate = serde_json::from_value(value.clone())?;
    ensure!(
        certificate.kind == "causal-state-equation-v1",
        "wrong proof kind"
    );
    check_node(p, &mut state_equation(p), &certificate.root, 0)
}

fn blocked_support(p: &Problem, counts: &[u64]) -> Option<(Vec<usize>, usize)> {
    let mut inside: Vec<_> = p.initial.iter().map(|&m| m > 0).collect();
    loop {
        let mut changed = false;
        for (t, &count) in p.transitions.iter().zip(counts) {
            if count > 0 && t.pre.iter().all(|&(i, _)| inside[i]) {
                for &(i, _) in &t.post {
                    changed |= !inside[i];
                    inside[i] = true;
                }
            }
        }
        if !changed {
            break;
        }
    }
    let blocked = p
        .transitions
        .iter()
        .zip(counts)
        .position(|(t, &n)| n > 0 && t.pre.iter().any(|&(i, _)| !inside[i]))?;
    Some((
        inside
            .iter()
            .enumerate()
            .filter_map(|(i, &s)| s.then_some(i))
            .collect(),
        blocked,
    ))
}

enum Answer {
    Refuted(Node),
    Witness(Vec<usize>),
    Unknown,
}

struct Search<'a> {
    problem: &'a Problem,
    deadline: Instant,
    max_states: usize,
    states: usize,
    nodes: usize,
    models: usize,
    cuts: usize,
}

impl Search<'_> {
    fn visit(&mut self, system: &mut System, depth: usize) -> Answer {
        if Instant::now() >= self.deadline || self.nodes >= 128 || depth > MAX_DEPTH {
            return Answer::Unknown;
        }
        self.nodes += 1;
        let remaining = self.deadline.saturating_duration_since(Instant::now());
        if depth == 0
            && let Some(multipliers) =
                system.refute(Instant::now() + (remaining / 4).min(Duration::from_millis(500)))
        {
            return Answer::Refuted(Node::Farkas { multipliers });
        }
        let remaining = self.deadline.saturating_duration_since(Instant::now());
        // This bound restricts candidate discovery only; proof leaves use the unbounded system.
        let Some(counts) = system.integer_model(Instant::now() + remaining / 2, 8192) else {
            if depth > 0 {
                let remaining = self.deadline.saturating_duration_since(Instant::now());
                if let Some(multipliers) = system.refute(Instant::now() + remaining / 2) {
                    return Answer::Refuted(Node::Farkas { multipliers });
                }
            }
            return Answer::Unknown;
        };
        // An exactly checked count model already establishes feasibility here.
        self.models += 1;
        if let Some((places, blocked)) = blocked_support(self.problem, &counts) {
            self.cuts += 1;
            let (omit_row, enter_row) = split(self.problem, &places, blocked).unwrap();
            system.rows.push(enter_row);
            let enter = self.visit(system, depth + 1);
            system.rows.pop();
            if matches!(&enter, Answer::Witness(_)) {
                return enter;
            }
            system.rows.push(omit_row);
            let omit = self.visit(system, depth + 1);
            system.rows.pop();
            match (omit, enter) {
                (Answer::Witness(trace), _) => Answer::Witness(trace),
                (Answer::Refuted(omit), Answer::Refuted(enter)) => Answer::Refuted(Node::Support {
                    places,
                    blocked,
                    omit: Box::new(omit),
                    enter: Box::new(enter),
                }),
                _ => Answer::Unknown,
            }
        } else {
            match realize(
                self.problem,
                &counts,
                self.deadline,
                self.max_states,
                &mut self.states,
            ) {
                Realization::Witness(trace) => Answer::Witness(trace),
                _ => Answer::Unknown,
            }
        }
    }
}

pub fn solve(p: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    let mut out = Outcome::unknown(
        "causal-state-equation",
        "invalid net or exhausted budget",
        0,
    );
    let deadline = Instant::now() + timeout;
    if p.validate().is_err() || timeout.is_zero() || max_states == 0 {
        return out;
    }
    if p.accepts(&p.initial).unwrap_or(false) {
        out.verdict = "reachable";
        out.marking = Some(p.initial.clone());
        out.reason = "replayed empty witness".into();
        return out;
    }
    let mut search = Search {
        problem: p,
        deadline,
        max_states,
        states: 0,
        nodes: 0,
        models: 0,
        cuts: 0,
    };
    let mut system = state_equation(p);
    let answer = search.visit(&mut system, 0);
    out.states = search.states;
    out.reason = format!(
        "{} arithmetic nodes, {} integer models, {} causal cuts",
        search.nodes, search.models, search.cuts
    );
    match answer {
        Answer::Refuted(root) => {
            let proof = serde_json::to_value(Certificate {
                kind: "causal-state-equation-v1".into(),
                root,
            })
            .unwrap();
            if verify_certificate(p, &proof).is_ok() {
                out.verdict = "unreachable";
                out.proof = Some(proof);
            }
        }
        Answer::Witness(trace) => {
            if let Ok(marking) = p.check_witness(&trace) {
                out.verdict = "reachable";
                out.trace = trace;
                out.marking = Some(marking);
            }
        }
        Answer::Unknown => {}
    }
    out
}
