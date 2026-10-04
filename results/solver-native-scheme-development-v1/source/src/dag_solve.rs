//! Exact SAT search when a certified one-token controller is acyclic.
use crate::{control, dag, model::Problem, sat, search::Outcome};
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::time::{Duration, Instant};

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Certificate {
    kind: String,
    control_places: Vec<usize>,
    additions: Vec<Vec<i32>>,
}

pub fn verify_certificate(problem: &Problem, proof: &Value) -> Result<()> {
    let proof: Certificate = serde_json::from_value(proof.clone())?;
    ensure!(
        matches!(proof.kind.as_str(), "dag-cnf-rup-v1" | "dag-cnf-rup-v2"),
        "wrong DAG proof kind"
    );
    let deadline = Instant::now() + Duration::from_secs(30);
    let work = 20_000_000;
    let encoding = if proof.kind == "dag-cnf-rup-v1" {
        dag::encode_legacy(problem, &proof.control_places, deadline, work)?
    } else {
        dag::encode(problem, &proof.control_places, deadline, work)?
    };
    sat::check_rup(
        encoding.variables,
        &encoding.clauses,
        &proof.additions,
        deadline,
        work,
    )
}

pub fn solve(problem: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    let deadline = Instant::now() + timeout;
    let mut out = Outcome::unknown("dag-sat", "no certified acyclic controller", 0);
    let result = || -> Result<Outcome> {
        problem.validate()?;
        ensure!(
            max_states > 0 && Instant::now() < deadline,
            "DAG resource limit"
        );
        let work = max_states.saturating_mul(100);
        let discovery_deadline =
            (Instant::now() + (timeout / 5).min(Duration::from_millis(250))).min(deadline);
        let control = control::discover(
            problem,
            discovery_deadline,
            problem.transitions.len().min(work),
        )
        .context("no certified one-token controller within discovery budget")?;
        let encoding = dag::encode(problem, &control.places, deadline, work)?;
        let mut answer = Outcome::unknown("dag-sat", "SAT search inconclusive", encoding.variables);
        match sat::solve(encoding.variables, &encoding.clauses, deadline, work)? {
            sat::SatResult::Sat(model) => {
                let trace: Vec<_> = encoding
                    .choices
                    .iter()
                    .filter_map(|&(transition, choice)| {
                        model
                            .get(choice.unsigned_abs() as usize - 1)
                            .filter(|&&value| value == (choice > 0))
                            .map(|_| transition)
                    })
                    .collect();
                let marking = problem.check_witness(&trace)?;
                ensure!(Instant::now() < deadline, "DAG replay deadline");
                answer.verdict = "reachable";
                answer.reason = "exact acyclic-control model; original-net witness replayed".into();
                answer.trace = trace;
                answer.marking = Some(marking);
            }
            sat::SatResult::Unsat(additions) => {
                answer.proof = Some(serde_json::to_value(Certificate {
                    kind: "dag-cnf-rup-v2".into(),
                    control_places: control.places,
                    additions,
                })?);
                ensure!(Instant::now() < deadline, "DAG certificate deadline");
                answer.verdict = "unreachable";
                answer.reason = "exact acyclic-control encoding; checked RUP refutation".into();
            }
            sat::SatResult::Unknown(reason) => answer.reason = reason,
        }
        Ok(answer)
    };
    match result() {
        Ok(answer) => answer,
        Err(error) => {
            out.reason = error.to_string();
            out
        }
    }
}
