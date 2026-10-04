//! Bounded sequences of exactly accelerated transition words, encoded in QF_LIA.
use crate::summary::{SparseWordSummary, sparse_summary};
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
    ensure!(
        accelerated || words.iter().all(|w| w.len() == 1),
        "ordinary BMC requires singleton words"
    );
    let mut encoder = Encoder::new(problem, if depth == 0 { &[] } else { words }, accelerated)?;
    let mut out = encoder.initial()?;
    out.push_str(&encoder.extend_to(depth)?);
    out.push_str(&encoder.target()?);
    writeln!(out, "(check-sat)")?;
    out.push_str(&encoder.values());
    Ok(out)
}

/// Reusable prefix encoder. Target assertions must be scoped by the SMT caller.
/// Extension is monotone; each returned fragment is sent exactly once.
pub struct Encoder<'a> {
    problem: &'a Problem,
    summaries: Vec<SparseWordSummary>,
    effects: Vec<Vec<(usize, BigInt)>>,
    accelerated: bool,
    depth: usize,
}

impl<'a> Encoder<'a> {
    pub fn new(problem: &'a Problem, words: &[Vec<usize>], accelerated: bool) -> Result<Self> {
        problem.validate()?;
        ensure!(
            accelerated || words.iter().all(|w| w.len() == 1),
            "ordinary BMC requires singleton words"
        );
        let summaries = words
            .iter()
            .map(|w| sparse_summary(problem, w))
            .collect::<Result<Vec<_>>>()?;
        let mut effects = vec![Vec::new(); problem.places.len()];
        for (choice, word) in summaries.iter().enumerate() {
            for (&place, (_, effect)) in &word.places {
                if !effect.is_zero() {
                    effects[place].push((choice, effect.clone()));
                }
            }
        }
        Ok(Self {
            problem,
            summaries,
            effects,
            accelerated,
            depth: 0,
        })
    }

    fn marking(&self, out: &mut String, step: usize) -> Result<()> {
        for place in 0..self.problem.places.len() {
            writeln!(
                out,
                "(declare-const m{step}_{place} Int)\n(assert (>= m{step}_{place} 0))"
            )?;
        }
        Ok(())
    }

    pub fn initial(&self) -> Result<String> {
        let mut out = String::from("(set-logic QF_LIA)\n(set-option :produce-models true)\n");
        self.marking(&mut out, 0)?;
        for (place, marking) in self.problem.initial.iter().enumerate() {
            writeln!(out, "(assert (= m0_{place} {marking}))")?;
        }
        Ok(out)
    }

    pub fn depth(&self) -> usize {
        self.depth
    }

    pub fn extend_to(&mut self, depth: usize) -> Result<String> {
        ensure!(depth >= self.depth, "cannot shrink an SMT prefix");
        ensure!(
            !self.summaries.is_empty() || depth == 0,
            "empty word vocabulary"
        );
        let mut out = String::new();
        for step in self.depth..depth {
            self.marking(&mut out, step + 1)?;
            self.step(&mut out, step)?;
        }
        self.depth = depth;
        Ok(out)
    }

    fn step(&self, out: &mut String, step: usize) -> Result<()> {
        writeln!(
            out,
            "(declare-const w{step} Int)\n(declare-const n{step} Int)\n(assert (and (<= 0 w{step}) (< w{step} {}) (>= n{step} 0)))",
            self.summaries.len()
        )?;
        if !self.accelerated {
            writeln!(out, "(assert (<= n{step} 1))")?;
        }
        let next = step + 1;
        for (choice, word) in self.summaries.iter().enumerate() {
            writeln!(
                out,
                "(assert (=> (and (= w{step} {choice}) (> n{step} 0)) (and true"
            )?;
            for (&place, (hurdle, effect)) in &word.places {
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
        for (place, place_effects) in self.effects.iter().enumerate() {
            write!(out, "(assert (= m{next}_{place} (+ m{step}_{place} ")?;
            for (choice, effect) in place_effects {
                write!(
                    out,
                    "(ite (= w{step} {choice}) (* n{step} {}) ",
                    integer(effect)
                )?;
            }
            write!(out, "0")?;
            for _ in 0..place_effects.len() {
                write!(out, ")")?;
            }
            writeln!(out, ")))")?;
        }

        Ok(())
    }

    pub fn target(&self) -> Result<String> {
        let depth = self.depth;
        let mut out = String::new();
        for constraint in &self.problem.target {
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

        Ok(out)
    }

    pub fn values(&self) -> String {
        if self.depth == 0 {
            return String::new();
        }
        let variables = (0..self.depth)
            .map(|i| format!("w{i} n{i}"))
            .collect::<Vec<_>>()
            .join(" ");
        format!("(get-value ({variables}))\n")
    }
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Transition;

    #[test]
    fn sparse_summaries_match_dense_composition() {
        let mut problem = Problem {
            places: (0..5).map(|i| format!("p{i}")).collect(),
            initial: vec![0; 5],
            transitions: Vec::new(),
            target: Vec::new(),
        };
        for pre in 0..4 {
            for post in 0..4 {
                problem.transitions.push(Transition {
                    name: format!("t{pre}_{post}"),
                    pre: vec![(1, pre + 1), (3, 4 - post)],
                    post: vec![(1, post + 1), (3, 4 - pre)],
                });
            }
        }
        problem.transitions.push(Transition {
            name: "source".into(),
            pre: vec![],
            post: vec![(1, u64::MAX)],
        });
        problem.transitions.push(Transition {
            name: "sink".into(),
            pre: vec![(1, u64::MAX)],
            post: vec![],
        });
        problem.validate().unwrap();
        for a in 0..problem.transitions.len() {
            for b in 0..problem.transitions.len() {
                for c in 0..problem.transitions.len() {
                    let word = [a, b, c];
                    let sparse = sparse_summary(&problem, &word).unwrap();
                    let dense = summary(&problem, &word).unwrap();
                    for p in 0..problem.places.len() {
                        let (h, e) = sparse.places.get(&p).cloned().unwrap_or_default();
                        assert_eq!(h, dense.hurdle[p], "{word:?}, place {p}");
                        assert_eq!(e, dense.effect[p], "{word:?}, place {p}");
                    }
                    assert!(sparse.places.len() <= 2);
                }
            }
        }
    }

    #[test]
    fn cancelled_effect_retains_read_guard() {
        let problem = Problem {
            places: vec!["p".into()],
            initial: vec![0],
            transitions: vec![
                Transition {
                    name: "add".into(),
                    pre: vec![],
                    post: vec![(0, 1)],
                },
                Transition {
                    name: "take".into(),
                    pre: vec![(0, 1)],
                    post: vec![],
                },
            ],
            target: vec![],
        };
        assert!(sparse_summary(&problem, &[0, 1]).unwrap().places.is_empty());
        assert_eq!(
            sparse_summary(&problem, &[1, 0]).unwrap().places[&0],
            (BigInt::from(1), BigInt::zero())
        );
    }
}
