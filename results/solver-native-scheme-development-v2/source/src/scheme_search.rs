//! Bounded native search over exactly accelerated word sequences.
use crate::{
    accelerated_bmc::{self, Segment},
    complete_arithmetic::{Answer, Limits as ArithmeticLimits},
    model::Problem,
    path_scheme, word_discovery,
};
use anyhow::Result;
use serde::Serialize;
use std::{
    collections::VecDeque,
    time::{Duration, Instant},
};

#[derive(Clone, Copy)]
pub struct Limits {
    pub depth: usize,
    pub schemes: usize,
    pub entries: usize,
    pub arithmetic_rows: usize,
    pub arithmetic_nodes: usize,
    pub arithmetic_quantum: Duration,
    pub discovery: word_discovery::Limits,
}

#[derive(Default, Serialize)]
pub struct Statistics {
    pub words: usize,
    pub discovery_truncated: bool,
    pub schemes: usize,
    pub prefix_refutations: usize,
    pub arithmetic_unknown: usize,
    pub discovery_seconds: f64,
    pub target_seconds: f64,
    pub prefix_seconds: f64,
}

#[derive(Serialize)]
pub struct Outcome {
    pub verdict: &'static str,
    pub reason: &'static str,
    pub segments: Vec<Segment>,
    pub statistics: Statistics,
}

fn arithmetic(deadline: Instant, limits: Limits) -> ArithmeticLimits {
    ArithmeticLimits {
        deadline: Some(
            Instant::now()
                .checked_add(limits.arithmetic_quantum)
                .map_or(deadline, |t| deadline.min(t)),
        ),
        max_rows: Some(limits.arithmetic_rows),
        max_nodes: Some(limits.arithmetic_nodes),
    }
}

/// Adjacent equal words are merged: w^a w^b = w^(a+b), with a,b positive.
/// A prefix is pruned only after proving that no positive counts can execute it.
/// Exhaustion, truncation and even complete bounded failure all return unknown.
pub fn solve(problem: &Problem, deadline: Instant, limits: Limits) -> Result<Outcome> {
    problem.validate()?;
    let mut result = Outcome {
        verdict: "unknown",
        reason: "bounded schemes exhausted",
        segments: Vec::new(),
        statistics: Statistics::default(),
    };
    if Instant::now() >= deadline || limits.entries == 0 || limits.schemes == 0 {
        result.reason = "search resource limit";
        return Ok(result);
    }
    if accelerated_bmc::check(problem, &[]).is_ok() {
        result.verdict = "reachable";
        result.reason = "checked initial marking";
        return Ok(result);
    }
    if limits.depth == 0 {
        return Ok(result);
    }
    let phase = Instant::now();
    let discovery = match word_discovery::discover(problem, limits.discovery, deadline) {
        Ok(discovery) => discovery,
        Err(_) => {
            result.reason = "discovery resource limit";
            return Ok(result);
        }
    };
    result.statistics.discovery_seconds = phase.elapsed().as_secs_f64();
    result.statistics.words = discovery.words.len();
    result.statistics.discovery_truncated = discovery.truncated;
    let vocabulary = discovery.words;
    let mut prefix_problem = problem.clone();
    prefix_problem.target.clear();
    // Queue entries enumerate children lazily, avoiding vocabulary^depth allocation.
    let mut queue = VecDeque::from([(Vec::<usize>::new(), 0usize)]);
    let mut pending_entries = 1usize;
    while let Some((prefix, mut next)) = queue.pop_front() {
        pending_entries -= prefix.len() + 1;
        while next < vocabulary.len() {
            if Instant::now() >= deadline || result.statistics.schemes >= limits.schemes {
                result.reason = "search resource limit";
                return Ok(result);
            }
            let choice = next;
            next += 1;
            if prefix.last() == Some(&choice) {
                continue;
            }
            let mut indices = prefix.clone();
            indices.push(choice);
            let words: Vec<_> = indices.iter().map(|&i| vocabulary[i].clone()).collect();
            result.statistics.schemes += 1;
            let phase = Instant::now();
            let answer = path_scheme::solve(
                problem,
                &words,
                &arithmetic(deadline, limits),
                limits.entries,
            )?;
            result.statistics.target_seconds += phase.elapsed().as_secs_f64();
            match answer {
                Answer::Feasible(segments) => {
                    result.verdict = "reachable";
                    result.reason = "checked native scheme witness";
                    result.segments = segments;
                    return Ok(result);
                }
                Answer::Unknown(_) => result.statistics.arithmetic_unknown += 1,
                Answer::Infeasible => {}
            }
            if indices.len() == limits.depth {
                continue;
            }
            let phase = Instant::now();
            let prefix_answer = path_scheme::solve(
                &prefix_problem,
                &words,
                &arithmetic(deadline, limits),
                limits.entries,
            )?;
            result.statistics.prefix_seconds += phase.elapsed().as_secs_f64();
            match prefix_answer {
                Answer::Infeasible => result.statistics.prefix_refutations += 1,
                answer => {
                    if matches!(answer, Answer::Unknown(_)) {
                        result.statistics.arithmetic_unknown += 1;
                    }
                    pending_entries = pending_entries.saturating_add(indices.len() + 1);
                    if pending_entries > limits.entries {
                        result.reason = "agenda entry limit";
                        return Ok(result);
                    }
                    queue.push_back((indices, 0));
                }
            }
        }
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Constraint, Transition};
    fn control_loop() -> Problem {
        Problem {
            places: vec!["a".into(), "b".into(), "count".into()],
            initial: vec![1, 0, 0],
            transitions: vec![
                Transition {
                    name: "ab".into(),
                    pre: vec![(0, 1)],
                    post: vec![(1, 1), (2, 1)],
                },
                Transition {
                    name: "ba".into(),
                    pre: vec![(1, 1)],
                    post: vec![(0, 1)],
                },
            ],
            target: vec![
                Constraint {
                    coefficients: vec![0, 0, 1],
                    bound: 1_000_000_000_000,
                    equality: true,
                },
                Constraint {
                    coefficients: vec![1, 0, 0],
                    bound: 1,
                    equality: true,
                },
            ],
        }
    }
    fn limits() -> Limits {
        Limits {
            depth: 2,
            schemes: 64,
            entries: 10000,
            arithmetic_rows: 1000,
            arithmetic_nodes: 1000,
            arithmetic_quantum: Duration::from_millis(500),
            discovery: word_discovery::Limits {
                max_work: 10000,
                max_length: 8,
                extra_words: 16,
            },
        }
    }
    #[test]
    fn automatically_accelerates_control_loop() {
        let p = control_loop();
        let result = solve(&p, Instant::now() + Duration::from_secs(3), limits()).unwrap();
        assert_eq!(result.verdict, "reachable");
        accelerated_bmc::check(&p, &result.segments).unwrap();
        assert!(result.segments.iter().any(|s| s.word.len() == 2));
        let mut singleton = limits();
        singleton.discovery.extra_words = 0;
        let result = solve(&p, Instant::now() + Duration::from_secs(3), singleton).unwrap();
        assert_eq!(result.verdict, "unknown");
    }
    #[test]
    fn prefix_refutations_prune_but_resource_failures_do_not() {
        let mut p = control_loop();
        p.initial = vec![0, 0, 0];
        let mut bounded = limits();
        bounded.discovery.extra_words = 0;
        let result = solve(&p, Instant::now() + Duration::from_secs(3), bounded).unwrap();
        assert_eq!(result.verdict, "unknown");
        assert_eq!(result.statistics.prefix_refutations, 2);
        assert_eq!(result.statistics.schemes, 2);
        bounded.arithmetic_rows = 0;
        let result = solve(&p, Instant::now() + Duration::from_secs(3), bounded).unwrap();
        assert_eq!(result.verdict, "unknown");
        assert_eq!(result.statistics.prefix_refutations, 0);
        assert_eq!(result.statistics.schemes, 4);
        assert!(result.statistics.arithmetic_unknown > 0);
    }
    #[test]
    fn empty_execution_and_budget_limits() {
        let mut p = control_loop();
        p.target.clear();
        let result = solve(&p, Instant::now() + Duration::from_secs(3), limits()).unwrap();
        assert_eq!(result.verdict, "reachable");
        assert!(result.segments.is_empty());
        assert_eq!(
            solve(&p, Instant::now(), limits()).unwrap().verdict,
            "unknown"
        );
        p = control_loop();
        let mut bounded = limits();
        bounded.depth = 0;
        assert_eq!(
            solve(&p, Instant::now() + Duration::from_secs(3), bounded)
                .unwrap()
                .verdict,
            "unknown"
        );
        bounded = limits();
        bounded.schemes = 1;
        let result = solve(&p, Instant::now() + Duration::from_secs(3), bounded).unwrap();
        assert_eq!(result.verdict, "unknown");
        assert_eq!(result.statistics.schemes, 1);
    }
}
