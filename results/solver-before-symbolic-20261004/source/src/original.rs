//! Whole-property scheduling for original PNML/XML input.
use crate::{
    model::Problem,
    pnml::{ParsedQuery, PropertyKind},
    search::Outcome,
};
use anyhow::{Result, ensure};
use serde::Serialize;
use std::time::Duration;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Schedule {
    SinglePass,
    Geometric,
}

#[derive(Debug, Serialize)]
pub struct Attempt {
    pub branch: usize,
    pub outcome: Outcome,
}

#[derive(Debug, Serialize)]
pub struct PropertyOutcome {
    pub kind: &'static str,
    pub property_id: String,
    pub property_kind: PropertyKind,
    pub branch_count: usize,
    pub verdict: &'static str,
    pub property_truth: Option<bool>,
    pub reason: &'static str,
    pub deadline_exceeded: bool,
    pub parse_seconds: f64,
    pub solve_seconds: f64,
    pub attempts: Vec<Attempt>,
}

/// `elapsed` measures from before input reads/parsing, against one property limit.
/// Branch shares are advisory; an external process deadline must enforce limits
/// for engines that do not return promptly. No result after the property limit
/// is accepted. The injected clock also permits deterministic scheduler tests.
pub fn solve(
    query: ParsedQuery,
    limit: Duration,
    elapsed: impl FnMut() -> Duration,
    solve_branch: impl FnMut(&Problem, Duration) -> Outcome,
) -> Result<PropertyOutcome> {
    solve_with_schedule(query, limit, Schedule::SinglePass, elapsed, solve_branch)
}

/// Geometric passes revisit unresolved branches with doubling time shares.
/// Refutations are retained, and the final attempts remain a contiguous prefix.
pub fn solve_with_schedule(
    query: ParsedQuery,
    limit: Duration,
    schedule: Schedule,
    mut elapsed: impl FnMut() -> Duration,
    mut solve_branch: impl FnMut(&Problem, Duration) -> Outcome,
) -> Result<PropertyOutcome> {
    let ParsedQuery {
        mut net,
        property_id,
        kind,
        mut targets,
    } = query;
    let branch_count = targets.len();
    let schedule = if branch_count <= 1 {
        Schedule::SinglePass
    } else {
        schedule
    };
    let parsed_at = elapsed();
    let mut attempts: Vec<Attempt> = Vec::new();
    let mut deadline_exceeded = parsed_at >= limit;
    if !deadline_exceeded && branch_count > 0 {
        let initial_remaining = limit.saturating_sub(parsed_at);
        let mut slice = match schedule {
            Schedule::SinglePass => Duration::ZERO,
            Schedule::Geometric => (initial_remaining / u32::try_from(branch_count)? / 2)
                .max(Duration::from_nanos(1))
                .min(initial_remaining),
        };
        let mut stop = false;
        loop {
            for (branch, target) in targets.iter_mut().enumerate() {
                if attempts
                    .get(branch)
                    .is_some_and(|attempt| attempt.outcome.verdict == "unreachable")
                {
                    continue;
                }
                let remaining = limit.saturating_sub(elapsed());
                if remaining.is_zero() {
                    deadline_exceeded = true;
                    break;
                }
                let share = match schedule {
                    Schedule::SinglePass => remaining / u32::try_from(branch_count - branch)?,
                    Schedule::Geometric => slice.min(remaining),
                };
                if share.is_zero() {
                    deadline_exceeded = true;
                    break;
                }
                std::mem::swap(&mut net.target, target);
                let mut outcome = solve_branch(&net, share);
                std::mem::swap(&mut net.target, target);
                ensure!(
                    matches!(outcome.verdict, "reachable" | "unreachable" | "unknown"),
                    "invalid solver verdict: {}",
                    outcome.verdict
                );
                if elapsed() >= limit {
                    deadline_exceeded = true;
                    outcome = Outcome::unknown(
                        &outcome.method,
                        "whole-property time limit",
                        outcome.states,
                    );
                }
                let reached = outcome.verdict == "reachable";
                let attempt = Attempt { branch, outcome };
                if branch < attempts.len() {
                    attempts[branch] = attempt;
                } else {
                    attempts.push(attempt);
                }
                if reached {
                    attempts.truncate(branch + 1);
                    stop = true;
                }
                if stop || deadline_exceeded {
                    break;
                }
            }
            if stop
                || deadline_exceeded
                || schedule == Schedule::SinglePass
                || slice == initial_remaining
                || attempts
                    .iter()
                    .all(|attempt| attempt.outcome.verdict == "unreachable")
            {
                break;
            }
            slice = slice.saturating_mul(2).min(initial_remaining);
        }
    }
    let finished_at = elapsed();
    deadline_exceeded |= finished_at >= limit;
    let (verdict, reason) = if deadline_exceeded {
        ("unknown", "whole-property time limit")
    } else if attempts
        .iter()
        .any(|attempt| attempt.outcome.verdict == "reachable")
    {
        ("reachable", "branch witness")
    } else if attempts.len() == branch_count
        && attempts
            .iter()
            .all(|attempt| attempt.outcome.verdict == "unreachable")
    {
        ("unreachable", "every branch refuted")
    } else {
        ("unknown", "one or more branches unresolved")
    };
    let property_truth = match verdict {
        "reachable" => Some(kind == PropertyKind::EF),
        "unreachable" => Some(kind == PropertyKind::AG),
        _ => None,
    };
    Ok(PropertyOutcome {
        kind: "original-property-v1",
        property_id,
        property_kind: kind,
        branch_count,
        verdict,
        property_truth,
        reason,
        deadline_exceeded,
        parse_seconds: parsed_at.as_secs_f64(),
        solve_seconds: finished_at.saturating_sub(parsed_at).as_secs_f64(),
        attempts,
    })
}
