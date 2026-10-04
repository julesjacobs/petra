//! Bounded sequences of exactly accelerated transition words, encoded in QF_LIA.
use crate::{model::Problem, summary::WordSummary};
use anyhow::{Context, Result, ensure};
use num_bigint::{BigInt, BigUint};
use num_traits::{Signed, Zero};
use serde::{Deserialize, Serialize};
use std::fmt::Write;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Segment {
    pub word: Vec<usize>,
    pub repetitions: String,
}

fn summary(problem: &Problem, word: &[usize]) -> Result<WordSummary> {
    ensure!(!word.is_empty(), "empty transition word");
    let mut result = WordSummary::identity(problem.places.len());
    for &index in word {
        let transition = problem
            .transitions
            .get(index)
            .context("invalid transition index")?;
        result = result.then(&WordSummary::transition(problem.places.len(), transition));
    }
    Ok(result)
}

fn integer(value: &BigInt) -> String {
    if value.is_negative() {
        format!("(- {})", -value)
    } else {
        value.to_string()
    }
}

/// Zero repetitions are identity steps, so depth bounds the number of nonempty segments.
pub fn encode(problem: &Problem, words: &[Vec<usize>], depth: usize) -> Result<String> {
    encode_mode(problem, words, depth, true)
}

pub fn encode_mode(
    problem: &Problem,
    words: &[Vec<usize>],
    depth: usize,
    accelerated: bool,
) -> Result<String> {
    problem.validate()?;
    ensure!(
        accelerated || words.iter().all(|w| w.len() == 1),
        "ordinary BMC requires singleton words"
    );
    ensure!(!words.is_empty() || depth == 0, "empty word vocabulary");
    let summaries = if depth == 0 {
        Vec::new()
    } else {
        words
            .iter()
            .map(|w| summary(problem, w))
            .collect::<Result<Vec<_>>>()?
    };
    let mut out = String::from("(set-logic QF_LIA)\n(set-option :produce-models true)\n");
    for step in 0..=depth {
        for place in 0..problem.places.len() {
            writeln!(
                out,
                "(declare-const m{step}_{place} Int)\n(assert (>= m{step}_{place} 0))"
            )?;
        }
    }
    for (place, marking) in problem.initial.iter().enumerate() {
        writeln!(out, "(assert (= m0_{place} {marking}))")?;
    }
    for step in 0..depth {
        writeln!(
            out,
            "(declare-const w{step} Int)\n(declare-const n{step} Int)\n(assert (and (<= 0 w{step}) (< w{step} {}) (>= n{step} 0)))",
            words.len()
        )?;
        if !accelerated {
            writeln!(out, "(assert (<= n{step} 1))")?;
        }
        let next = step + 1;
        for (choice, word) in summaries.iter().enumerate() {
            writeln!(
                out,
                "(assert (=> (and (= w{step} {choice}) (> n{step} 0)) (and true"
            )?;
            for (place, (hurdle, effect)) in word.hurdle.iter().zip(&word.effect).enumerate() {
                let depletion = (-effect).max(BigInt::zero());
                if hurdle.is_zero() && depletion.is_zero() {
                    continue;
                }
                writeln!(
                    out,
                    "(>= m{step}_{place} (+ {} (* (- n{step} 1) {})))",
                    integer(hurdle),
                    integer(&depletion)
                )?;
            }
            writeln!(out, ")))")?;
        }
        for place in 0..problem.places.len() {
            write!(out, "(assert (= m{next}_{place} (+ m{step}_{place} ")?;
            let mut choices = 0;
            for (choice, word) in summaries.iter().enumerate() {
                let effect = &word.effect[place];
                if effect.is_zero() {
                    continue;
                }
                write!(
                    out,
                    "(ite (= w{step} {choice}) (* n{step} {}) ",
                    integer(effect)
                )?;
                choices += 1;
            }
            write!(out, "0")?;
            for _ in 0..choices {
                write!(out, ")")?;
            }
            writeln!(out, ")))")?;
        }
    }
    for constraint in &problem.target {
        let terms = constraint
            .coefficients
            .iter()
            .enumerate()
            .filter(|(_, c)| **c != 0)
            .map(|(p, c)| format!("(* {} m{depth}_{p})", integer(&BigInt::from(*c))))
            .collect::<Vec<_>>()
            .join(" ");
        writeln!(
            out,
            "(assert ({} (+ 0 {terms}) {}))",
            if constraint.equality { "=" } else { ">=" },
            integer(&BigInt::from(constraint.bound))
        )?;
    }
    writeln!(out, "(check-sat)")?;
    if depth > 0 {
        let variables = (0..depth)
            .map(|i| format!("w{i} n{i}"))
            .collect::<Vec<_>>()
            .join(" ");
        writeln!(out, "(get-value ({variables}))")?;
    }
    Ok(out)
}

/// Check words directly against the original net, without expanding repetitions.
pub fn check(problem: &Problem, segments: &[Segment]) -> Result<Vec<BigInt>> {
    problem.validate()?;
    let mut marking: Vec<_> = problem.initial.iter().copied().map(BigInt::from).collect();
    for segment in segments {
        let count = segment
            .repetitions
            .parse::<BigUint>()
            .context("invalid repetition count")?;
        let word = summary(problem, &segment.word)?;
        marking = word
            .repeat(&count)
            .apply(&marking)
            .context("disabled repeated word")?;
    }
    for constraint in &problem.target {
        let value: BigInt = constraint
            .coefficients
            .iter()
            .zip(&marking)
            .map(|(&c, m)| m * c)
            .sum();
        let bound = BigInt::from(constraint.bound);
        ensure!(
            if constraint.equality {
                value == bound
            } else {
                value >= bound
            },
            "target not satisfied"
        );
    }
    Ok(marking)
}

/// Parse only the requested nonnegative scalar values; the exact checker decides acceptance.
pub fn decode(words: &[Vec<usize>], depth: usize, model: &str) -> Result<Vec<Segment>> {
    let normalized = model.replace(['(', ')'], " ");
    let mut tokens = normalized.split_whitespace();
    ensure!(tokens.next() == Some("sat"), "no satisfiable model");
    let mut values = std::collections::HashMap::new();
    while let Some(name) = tokens.next() {
        let value = tokens.next().context("missing model value")?;
        ensure!(
            values.insert(name, value).is_none(),
            "duplicate model variable"
        );
    }
    ensure!(
        values.len() == depth.checked_mul(2).context("depth overflow")?,
        "unexpected model variables"
    );
    (0..depth)
        .map(|i| {
            let choice = values
                .get(format!("w{i}").as_str())
                .context("missing word choice")?
                .parse::<usize>()?;
            let count = values
                .get(format!("n{i}").as_str())
                .context("missing repetition count")?;
            count
                .parse::<BigUint>()
                .context("invalid repetition count")?;
            Ok(Segment {
                word: words
                    .get(choice)
                    .context("word choice out of range")?
                    .clone(),
                repetitions: count.to_string(),
            })
        })
        .collect()
}
