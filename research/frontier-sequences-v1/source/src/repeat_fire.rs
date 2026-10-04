//! Exact finite repetition of one transition, preserving every prefix guard.
use crate::model::Problem;
use anyhow::{Context, Result, ensure};
use std::collections::BTreeMap;

struct Arc {
    place: usize,
    pre: u64,
    post: u64,
}

struct Limits {
    enabled: u64,
    representable: u64,
}

/// Hot-loop bound for validated sparse guards and incidence effects.
/// Guards and effects contain each place at most once; effects are sorted by place
/// and fit a difference
/// of two `u64` arc weights. The callback supplies tokens in the same projection.
pub(crate) fn maximum_sparse(
    guards: impl Iterator<Item = (usize, u64)>,
    delta: &[(usize, i128)],
    tokens: impl Fn(usize) -> u64,
) -> Option<u64> {
    let mut maximum = u64::MAX;
    for (place, weight) in guards {
        let count = tokens(place);
        if count < weight {
            return None;
        }
        if let Ok(i) = delta.binary_search_by_key(&place, |&(p, _)| p) {
            let effect = delta[i].1;
            if effect < 0 {
                maximum = maximum.min(1 + (count - weight) / u64::try_from(-effect).ok()?);
            }
        }
    }
    for &(place, effect) in delta {
        let count = tokens(place);
        let bound = if effect > 0 {
            (u64::MAX - count) / u64::try_from(effect).ok()?
        } else if effect < 0 {
            count / u64::try_from(-effect).ok()?
        } else {
            u64::MAX
        };
        maximum = maximum.min(bound);
    }
    Some(maximum)
}

fn incidence(problem: &Problem, marking: &[u64], transition: usize) -> Result<Vec<Arc>> {
    problem.validate()?;
    ensure!(
        marking.len() == problem.places.len(),
        "marking dimension mismatch"
    );
    let transition = problem
        .transitions
        .get(transition)
        .context("invalid transition index")?;
    let mut arcs = BTreeMap::<usize, (u64, u64)>::new();
    for &(place, weight) in &transition.pre {
        arcs.entry(place).or_default().0 = weight;
    }
    for &(place, weight) in &transition.post {
        arcs.entry(place).or_default().1 = weight;
    }
    Ok(arcs
        .into_iter()
        .map(|(place, (pre, post))| Arc { place, pre, post })
        .collect())
}

fn limits(marking: &[u64], arcs: &[Arc]) -> Result<Option<Limits>> {
    let mut enabled = u64::MAX;
    let mut representable = u64::MAX;
    for arc in arcs {
        let tokens = marking[arc.place];
        if tokens < arc.pre {
            return Ok(None);
        }
        if arc.pre > arc.post {
            let decrease = u128::from(arc.pre - arc.post);
            let count = 1u128
                .checked_add(u128::from(tokens - arc.pre) / decrease)
                .context("repetition limit overflow")?;
            enabled = enabled.min(u64::try_from(count).context("repetition limit exceeds u64")?);
        } else if arc.post > arc.pre {
            let increase = arc.post - arc.pre;
            representable = representable.min((u64::MAX - tokens) / increase);
        }
    }
    Ok(Some(Limits {
        enabled,
        representable,
    }))
}

/// Maximum repetitions whose every prefix is enabled and fits in `u64` counters.
///
/// Validates the complete problem, marking dimension, and transition index.
/// Returns `None` for an initially disabled transition, `Some(0)` when enabled
/// but its first firing overflows, and `Some(u64::MAX)` when that many firings
/// are possible (including transitions with zero effect).
pub fn maximum(problem: &Problem, marking: &[u64], transition: usize) -> Result<Option<u64>> {
    let arcs = incidence(problem, marking, transition)?;
    Ok(limits(marking, &arcs)?.map(|bound| bound.enabled.min(bound.representable)))
}

/// Fire one transition exactly `repeats` times, without enumerating repetitions.
///
/// Validates inputs even for zero repetitions, which return the original marking.
/// Returns `None` if a required firing is disabled, or an error if an earlier
/// enabled firing overflows a counter. When both limits coincide, the next
/// firing is disabled before its output is evaluated, matching `Problem::fire`.
pub fn fire(
    problem: &Problem,
    marking: &[u64],
    transition: usize,
    repeats: u64,
) -> Result<Option<Vec<u64>>> {
    let arcs = incidence(problem, marking, transition)?;
    if repeats == 0 {
        return Ok(Some(marking.to_vec()));
    }
    let Some(bound) = limits(marking, &arcs)? else {
        return Ok(None);
    };
    if repeats > bound.enabled && bound.enabled <= bound.representable {
        return Ok(None);
    }
    ensure!(
        repeats <= bound.representable,
        "repeated firing counter overflow"
    );
    let mut result = marking.to_vec();
    for arc in arcs {
        let effect = arc.post.abs_diff(arc.pre);
        let total = u128::from(effect)
            .checked_mul(u128::from(repeats))
            .context("repeated effect overflow")?;
        let tokens = u128::from(marking[arc.place]);
        let value = if arc.post >= arc.pre {
            tokens
                .checked_add(total)
                .context("repeated firing addition overflow")?
        } else {
            tokens
                .checked_sub(total)
                .context("repeated firing subtraction overflow")?
        };
        result[arc.place] = u64::try_from(value).context("repeated firing counter overflow")?;
    }
    Ok(Some(result))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Constraint, Transition};

    fn problem(pre: &[u64], post: &[u64]) -> Problem {
        assert_eq!(pre.len(), post.len());
        let arcs = |weights: &[u64]| {
            weights
                .iter()
                .enumerate()
                .filter_map(|(i, &weight)| (weight > 0).then_some((i, weight)))
                .collect()
        };
        Problem {
            places: (0..pre.len()).map(|i| format!("p{i}")).collect(),
            initial: vec![0; pre.len()],
            target: vec![],
            transitions: vec![Transition {
                name: "t".into(),
                pre: arcs(pre),
                post: arcs(post),
            }],
        }
    }

    fn iterative(problem: &Problem, marking: &[u64], repeats: u64) -> Result<Option<Vec<u64>>> {
        let mut current = marking.to_vec();
        for _ in 0..repeats {
            let Some(next) = problem.fire(&current, 0)? else {
                return Ok(None);
            };
            current = next;
        }
        Ok(Some(current))
    }

    #[test]
    fn exhaustive_small_arcs_and_markings_match_iterative_firing() {
        for pre0 in 0..=3 {
            for pre1 in 0..=3 {
                for post0 in 0..=3 {
                    for post1 in 0..=3 {
                        let p = problem(&[pre0, pre1], &[post0, post1]);
                        for x in 0..=5 {
                            for y in 0..=5 {
                                let marking = [x, y];
                                let bound = maximum(&p, &marking, 0).unwrap();
                                let delta: Vec<_> = [
                                    i128::from(post0) - i128::from(pre0),
                                    i128::from(post1) - i128::from(pre1),
                                ]
                                .into_iter()
                                .enumerate()
                                .filter(|&(_, d)| d != 0)
                                .collect();
                                assert_eq!(
                                    maximum_sparse(
                                        p.transitions[0].pre.iter().copied(),
                                        &delta,
                                        |place| marking[place]
                                    ),
                                    bound
                                );
                                assert_eq!(bound.is_none(), x < pre0 || y < pre1);
                                for repeats in 0..=7 {
                                    let expected = iterative(&p, &marking, repeats).unwrap();
                                    assert_eq!(fire(&p, &marking, 0, repeats).unwrap(), expected);
                                    if repeats > 0 {
                                        assert_eq!(
                                            expected.is_some(),
                                            bound.is_some_and(|n| n >= repeats)
                                        );
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    #[test]
    fn draining_selfloop_is_limited_by_prefix_guards() {
        let p = problem(&[5], &[3]);
        assert_eq!(maximum(&p, &[10], 0).unwrap(), Some(3));
        assert_eq!(fire(&p, &[10], 0, 3).unwrap(), Some(vec![4]));
        assert_eq!(fire(&p, &[10], 0, 4).unwrap(), None);
        assert_eq!(maximum(&p, &[4], 0).unwrap(), None);
    }

    #[test]
    fn unchanged_selfloops_still_require_their_full_guard() {
        let p = problem(&[4, 0], &[4, 2]);
        assert_eq!(maximum(&p, &[3, 0], 0).unwrap(), None);
        assert_eq!(fire(&p, &[3, 0], 0, 1).unwrap(), None);
        assert_eq!(maximum(&p, &[4, 0], 0).unwrap(), Some(u64::MAX / 2));
        assert_eq!(
            fire(&p, &[4, 0], 0, u64::MAX / 2).unwrap(),
            Some(vec![4, u64::MAX - 1])
        );
        assert!(fire(&p, &[4, 0], 0, u64::MAX / 2 + 1).is_err());
    }

    #[test]
    fn sources_sinks_and_large_effects_are_exact() {
        let source = problem(&[0], &[u64::MAX]);
        assert_eq!(maximum(&source, &[0], 0).unwrap(), Some(1));
        assert_eq!(fire(&source, &[0], 0, 1).unwrap(), Some(vec![u64::MAX]));
        assert!(fire(&source, &[0], 0, u64::MAX).is_err());
        assert_eq!(maximum(&source, &[1], 0).unwrap(), Some(0));
        assert!(fire(&source, &[1], 0, 1).is_err());
        let sink = problem(&[1], &[0]);
        assert_eq!(maximum(&sink, &[u64::MAX], 0).unwrap(), Some(u64::MAX));
        assert_eq!(
            fire(&sink, &[u64::MAX], 0, u64::MAX).unwrap(),
            Some(vec![0])
        );
        let growing_selfloop = problem(&[u64::MAX - 1], &[u64::MAX]);
        assert_eq!(
            maximum(&growing_selfloop, &[u64::MAX - 1], 0).unwrap(),
            Some(1)
        );
        assert_eq!(
            fire(&growing_selfloop, &[u64::MAX - 1], 0, 1).unwrap(),
            Some(vec![u64::MAX])
        );
        let draining_selfloop = problem(&[u64::MAX], &[u64::MAX - 1]);
        assert_eq!(
            maximum(&draining_selfloop, &[u64::MAX], 0).unwrap(),
            Some(1)
        );
    }

    #[test]
    fn disabling_and_overflow_follow_the_first_failing_prefix() {
        let p = problem(&[1, 0], &[0, 1]);
        for tokens in 0..=4 {
            for headroom in 0..=4 {
                let marking = [tokens, u64::MAX - headroom];
                let bound = maximum(&p, &marking, 0).unwrap();
                assert_eq!(
                    bound,
                    if tokens == 0 {
                        None
                    } else {
                        Some(tokens.min(headroom))
                    }
                );
                for repeats in 0..=6 {
                    let expected = iterative(&p, &marking, repeats);
                    let actual = fire(&p, &marking, 0, repeats);
                    match (actual, expected) {
                        (Ok(a), Ok(b)) => assert_eq!(a, b),
                        (Err(_), Err(_)) => {}
                        (a, b) => panic!(
                            "different prefix result at {marking:?}/{repeats}: {a:?} vs {b:?}"
                        ),
                    }
                }
            }
        }
    }

    #[test]
    fn neutral_and_empty_transitions_allow_every_u64_repeat_count() {
        let p = problem(&[u64::MAX], &[u64::MAX]);
        assert_eq!(maximum(&p, &[u64::MAX], 0).unwrap(), Some(u64::MAX));
        assert_eq!(
            fire(&p, &[u64::MAX], 0, u64::MAX).unwrap(),
            Some(vec![u64::MAX])
        );
        let p = problem(&[], &[]);
        assert_eq!(maximum(&p, &[], 0).unwrap(), Some(u64::MAX));
        assert_eq!(fire(&p, &[], 0, u64::MAX).unwrap(), Some(vec![]));
    }

    #[test]
    fn zero_repetitions_are_identity_even_if_disabled_or_overflowing() {
        let p = problem(&[1, 0], &[0, 1]);
        for marking in [[0, 0], [1, u64::MAX]] {
            assert_eq!(fire(&p, &marking, 0, 0).unwrap(), Some(marking.to_vec()));
        }
    }

    #[test]
    fn validates_all_inputs_even_for_zero_repetitions() {
        let base = problem(&[1], &[2]);
        let mut malformed = Vec::new();
        let mut p = base.clone();
        p.initial.clear();
        malformed.push(p);
        let mut p = base.clone();
        p.target.push(Constraint {
            coefficients: vec![],
            bound: 0,
            equality: true,
        });
        malformed.push(p);
        for arcs in [vec![(1, 1)], vec![(0, 0)], vec![(0, 1), (0, 2)]] {
            let mut p = base.clone();
            p.transitions[0].pre = arcs.clone();
            malformed.push(p);
            let mut p = base.clone();
            p.transitions[0].post = arcs;
            malformed.push(p);
        }
        for p in malformed {
            assert!(maximum(&p, &[1], 0).is_err());
            assert!(fire(&p, &[1], 0, 0).is_err());
        }
        assert!(maximum(&base, &[], 0).is_err());
        assert!(fire(&base, &[], 0, 0).is_err());
        assert!(maximum(&base, &[1], 1).is_err());
        assert!(fire(&base, &[1], 1, 0).is_err());
    }
}
