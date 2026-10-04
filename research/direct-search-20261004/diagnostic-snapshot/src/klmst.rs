//! Bounded linear-path-scheme search with exact word acceleration.
//!
//! This is a KLM-inspired witness engine, not the KLMST decision procedure:
//! there are no generalized VASS decompositions or complete refinements.
//! Ordinary transitions retain a fair search frontier; selected repeated words
//! add exact edges. Limits are unknown, and every positive result is replayed.
use crate::{model::Problem, search::Outcome};
use std::{
    cmp::Reverse,
    collections::{BinaryHeap, HashMap, VecDeque},
    time::{Duration, Instant},
};

const METHOD: &str = "klm-schemes";
const MAX_TRACE: usize = 1_000_000;

#[derive(Clone, Debug)]
struct Word {
    transitions: Vec<usize>,
    requirement: Vec<i128>,
    effect: Vec<i128>,
}
impl Word {
    fn new(p: &Problem, transitions: Vec<usize>) -> Option<Self> {
        let mut effect = vec![0i128; p.initial.len()];
        let mut requirement = vec![0i128; p.initial.len()];
        for &t in &transitions {
            for &(q, w) in &p.transitions[t].pre {
                requirement[q] = requirement[q].max(i128::from(w).checked_sub(effect[q])?);
            }
            for &(q, w) in &p.transitions[t].pre {
                effect[q] = effect[q].checked_sub(i128::from(w))?;
            }
            for &(q, w) in &p.transitions[t].post {
                effect[q] = effect[q].checked_add(i128::from(w))?;
            }
        }
        Some(Self {
            transitions,
            requirement,
            effect,
        })
    }
    fn repeat(&self, m: &[u64], n: usize) -> Option<Vec<u64>> {
        if n == 0 {
            return Some(m.to_vec());
        }
        m.iter()
            .zip(&self.requirement)
            .zip(&self.effect)
            .map(|((&x, &r), &d)| {
                let need = r.checked_add((n as i128 - 1).checked_mul(d.checked_neg()?.max(0))?)?;
                if i128::from(x) < need {
                    return None;
                }
                u64::try_from(i128::from(x).checked_add((n as i128).checked_mul(d)?)?).ok()
            })
            .collect()
    }
    fn candidates(&self, p: &Problem, m: &[u64], capacity: usize) -> Vec<usize> {
        let maximum = capacity / self.transitions.len();
        if maximum < 2 {
            return vec![];
        }
        let mut candidates = vec![];
        // Powers of two allow compositions of schemes even when this word alone
        // cannot reach the target. Exact constraint boundaries avoid unit pumping.
        let mut power = 2;
        while power <= maximum.min(1024) {
            candidates.push(power);
            power *= 2;
        }
        let target_interval = (|| {
            let mut low = 2i128;
            let mut high = maximum as i128;
            for c in &p.target {
                let mut base = 0i128;
                let mut delta = 0i128;
                for ((&a, &x), &d) in c.coefficients.iter().zip(m).zip(&self.effect) {
                    base = base.checked_add(i128::from(a).checked_mul(i128::from(x))?)?;
                    delta = delta.checked_add(i128::from(a).checked_mul(d)?)?;
                }
                constrain(
                    &mut low,
                    &mut high,
                    delta,
                    i128::from(c.bound).checked_sub(base)?,
                )?;
                if c.equality {
                    constrain(
                        &mut low,
                        &mut high,
                        delta.checked_neg()?,
                        base.checked_sub(i128::from(c.bound))?,
                    )?;
                }
            }
            (low <= high).then_some(low as usize)
        })();
        if let Some(n) = target_interval {
            candidates.push(n);
        }
        // Pump enough to enable each next transition, allowing a different word
        // or a final transition after the repeated segment.
        for t in &p.transitions {
            let mut low = 2i128;
            let mut high = maximum as i128;
            let mut possible = true;
            for &(q, w) in &t.pre {
                if constrain(
                    &mut low,
                    &mut high,
                    self.effect[q],
                    i128::from(w) - i128::from(m[q]),
                )
                .is_none()
                {
                    possible = false;
                    break;
                }
            }
            if possible && low <= high {
                candidates.push(low as usize);
            }
        }
        candidates.sort_unstable();
        candidates.dedup();
        candidates
    }
}
// Restrict integer n by coefficient*n >= bound, using mathematical floor/ceil.
fn constrain(low: &mut i128, high: &mut i128, coefficient: i128, bound: i128) -> Option<()> {
    if coefficient > 0 {
        let quotient = bound.checked_div_euclid(coefficient)?;
        let ceil = quotient.checked_add(i128::from(bound.checked_rem_euclid(coefficient)? != 0))?;
        *low = (*low).max(ceil);
    } else if coefficient < 0 {
        let positive = coefficient.checked_neg()?;
        *high = (*high).min(bound.checked_neg()?.checked_div_euclid(positive)?);
    } else if bound > 0 {
        return None;
    }
    (*low <= *high).then_some(())
}
struct Entry {
    marking: Vec<u64>,
    parent: Option<(usize, Vec<usize>, usize)>,
    length: usize,
    expanded: bool,
}
fn score(p: &Problem, m: &[u64]) -> u128 {
    p.target
        .iter()
        .map(|c| {
            let value = c.coefficients.iter().zip(m).fold(0i128, |a, (&x, &y)| {
                a.saturating_add(i128::from(x) * i128::from(y))
            });
            let gap = i128::from(c.bound).saturating_sub(value);
            if c.equality {
                gap.unsigned_abs()
            } else {
                gap.max(0) as u128
            }
        })
        .fold(0, u128::saturating_add)
}
fn suffix(nodes: &[Entry], mut id: usize) -> Vec<usize> {
    let mut reversed = vec![];
    while let Some((parent, word, count)) = &nodes[id].parent {
        for _ in 0..(*count).min(4) {
            for &t in word.iter().rev() {
                reversed.push(t);
                if reversed.len() == 4 {
                    reversed.reverse();
                    return reversed;
                }
            }
        }
        id = *parent;
    }
    reversed.reverse();
    reversed
}
fn witness(p: &Problem, nodes: &[Entry], mut id: usize) -> Outcome {
    let mut segments = vec![];
    let length = nodes[id].length;
    while let Some((parent, word, count)) = &nodes[id].parent {
        segments.push((word, count));
        id = *parent;
    }
    let mut trace = Vec::with_capacity(length);
    for (word, count) in segments.into_iter().rev() {
        for _ in 0..*count {
            trace.extend_from_slice(word);
        }
    }
    match p.check_witness(&trace) {
        Ok(marking) => Outcome {
            verdict: "reachable",
            method: METHOD.into(),
            reason: "replayed exact path-scheme witness".into(),
            states: nodes.len(),
            trace,
            marking: Some(marking),
            certificate: None,
            proof: None,
        },
        Err(e) => Outcome::unknown(METHOD, &format!("witness check failed: {e}"), nodes.len()),
    }
}
pub fn solve(p: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    let start = Instant::now();
    let singletons: Vec<_> = (0..p.transitions.len())
        .filter_map(|t| Word::new(p, vec![t]))
        .collect();
    let mut nodes = vec![Entry {
        marking: p.initial.clone(),
        parent: None,
        length: 0,
        expanded: false,
    }];
    let mut seen = HashMap::from([(p.initial.clone(), 0)]);
    let mut queue = VecDeque::from([0]);
    let mut heap = BinaryHeap::from([Reverse((score(p, &p.initial), 0usize))]);
    let mut iteration = 0usize;
    let mut truncated = false;
    loop {
        if start.elapsed() >= timeout {
            return Outcome::unknown(METHOD, "time limit", nodes.len());
        }
        iteration += 1;
        let mut next = None;
        if iteration.is_multiple_of(4) {
            while let Some(id) = queue.pop_front() {
                if !nodes[id].expanded {
                    next = Some(id);
                    break;
                }
            }
        }
        if next.is_none() {
            while let Some(Reverse((_, id))) = heap.pop() {
                if !nodes[id].expanded {
                    next = Some(id);
                    break;
                }
            }
        }
        let Some(id) = next else {
            if truncated {
                return Outcome::unknown(METHOD, "witness expansion limit", nodes.len());
            }
            let mut out = Outcome::unknown(
                METHOD,
                "finite reachable state space exhausted",
                nodes.len(),
            );
            out.verdict = "unreachable";
            return out;
        };
        nodes[id].expanded = true;
        match p.accepts(&nodes[id].marking) {
            Ok(true) => return witness(p, &nodes, id),
            Err(e) => return Outcome::unknown(METHOD, &e.to_string(), nodes.len()),
            _ => {}
        }
        let capacity = MAX_TRACE.saturating_sub(nodes[id].length);
        if capacity == 0 {
            truncated = true;
            continue;
        }
        let history = suffix(&nodes, id);
        let words: Vec<_> = (2..=history.len())
            .filter_map(|n| Word::new(p, history[history.len() - n..].to_vec()))
            .collect();
        for word in singletons.iter().chain(&words) {
            if start.elapsed() >= timeout {
                return Outcome::unknown(METHOD, "time limit", nodes.len());
            }
            if word.repeat(&nodes[id].marking, 1).is_none() {
                if word.transitions.len() == 1
                    && let Err(e) = p.fire(&nodes[id].marking, word.transitions[0])
                {
                    return Outcome::unknown(METHOD, &e.to_string(), nodes.len());
                }
                continue;
            }
            let mut counts = word.candidates(p, &nodes[id].marking, capacity);
            if word.transitions.len() == 1 {
                counts.insert(0, 1);
            }
            for count in counts {
                let Some(marking) = word.repeat(&nodes[id].marking, count) else {
                    // Unit firings use Problem::fire to distinguish disabled from
                    // overflowing transitions, which must not prove exhaustion.
                    if count == 1
                        && let Err(e) = p.fire(&nodes[id].marking, word.transitions[0])
                    {
                        return Outcome::unknown(METHOD, &e.to_string(), nodes.len());
                    }
                    continue;
                };
                if seen.contains_key(&marking) {
                    continue;
                }
                if nodes.len() >= max_states {
                    return Outcome::unknown(METHOD, "state limit", nodes.len());
                }
                let child = nodes.len();
                heap.push(Reverse((score(p, &marking), child)));
                queue.push_back(child);
                seen.insert(marking.clone(), child);
                nodes.push(Entry {
                    marking,
                    parent: Some((id, word.transitions.clone(), count)),
                    length: nodes[id].length + word.transitions.len() * count,
                    expanded: false,
                });
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Constraint, Transition};
    fn problem(
        initial: Vec<u64>,
        transitions: Vec<Transition>,
        coefficients: Vec<i64>,
        bound: i64,
    ) -> Problem {
        Problem {
            places: (0..initial.len()).map(|i| i.to_string()).collect(),
            initial,
            transitions,
            target: vec![Constraint {
                coefficients,
                bound,
                equality: true,
            }],
        }
    }
    fn transition(pre: Vec<(usize, u64)>, post: Vec<(usize, u64)>) -> Transition {
        Transition {
            name: "t".into(),
            pre,
            post,
        }
    }
    #[test]
    fn word_summary_matches_replay() {
        let p = problem(
            vec![0, 0],
            vec![
                transition(vec![(0, 2)], vec![(1, 3)]),
                transition(vec![(1, 2)], vec![(0, 1)]),
            ],
            vec![1, 0],
            0,
        );
        for word in [vec![0], vec![1], vec![0, 1], vec![1, 0], vec![0, 1, 0]] {
            let summary = Word::new(&p, word.clone()).unwrap();
            for a in 0..10 {
                for b in 0..10 {
                    for n in 0..8 {
                        let mut replay = Some(vec![a, b]);
                        for _ in 0..n {
                            for &t in &word {
                                replay = replay.and_then(|m| p.fire(&m, t).unwrap());
                            }
                        }
                        assert_eq!(summary.repeat(&[a, b], n), replay);
                    }
                }
            }
        }
    }
    #[test]
    fn accelerates_two_transition_word() {
        let p = problem(
            vec![1, 0, 0],
            vec![
                transition(vec![(0, 1)], vec![(1, 1), (2, 1)]),
                transition(vec![(1, 1)], vec![(0, 1)]),
            ],
            vec![0, 0, 1],
            10_000,
        );
        let out = solve(&p, Duration::from_secs(2), 300);
        assert_eq!(out.verdict, "reachable", "{}", out.reason);
        assert!(out.states < 300);
        assert!(p.check_witness(&out.trace).is_ok());
    }
    #[test]
    fn decrement_boundary_and_read_arc() {
        let p = problem(
            vec![5, 1],
            vec![transition(vec![(0, 2), (1, 1)], vec![(0, 1), (1, 1)])],
            vec![1, 0],
            0,
        );
        let w = Word::new(&p, vec![0]).unwrap();
        assert_eq!(w.repeat(&p.initial, 4), Some(vec![1, 1]));
        assert_eq!(w.repeat(&p.initial, 5), None);
        assert_eq!(w.repeat(&[5, 0], 1), None);
        assert_eq!(
            solve(&p, Duration::from_secs(1), 100).verdict,
            "unreachable"
        );
    }
    #[test]
    fn limits_do_not_refute_parity() {
        let p = problem(vec![0], vec![transition(vec![], vec![(0, 2)])], vec![1], 3);
        assert_eq!(solve(&p, Duration::from_secs(1), 50).verdict, "unknown");
    }
    #[test]
    fn overflow_is_unknown() {
        let p = problem(
            vec![u64::MAX],
            vec![transition(vec![], vec![(0, 1)])],
            vec![1],
            0,
        );
        assert_eq!(solve(&p, Duration::from_secs(1), 50).verdict, "unknown");
    }
}
