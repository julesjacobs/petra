//! Sufficient nonmembership goals inferred from the serial response language.
use crate::{model::Constraint, raw_target::RawQuery, reduced::Prepared, search::Outcome};
use std::time::{Duration, Instant};

const GOAL_LIMIT: usize = 32;

struct Candidate {
    positive: usize,
    negative: Option<usize>,
    bound: i64,
}

impl Candidate {
    fn rank(&self) -> (i64, bool) {
        (self.bound, self.negative.is_some())
    }
}

fn candidates(q: &RawQuery, mut expired: impl FnMut() -> bool) -> Vec<Candidate> {
    let mut result: Vec<Candidate> = Vec::with_capacity(GOAL_LIMIT);
    let rs = &q.target.response_places;
    'enumerate: for &positive in rs {
        for negative in
            std::iter::once(None).chain(rs.iter().copied().filter(|&i| i != positive).map(Some))
        {
            if expired() {
                break 'enumerate;
            }
            let mut bound = None::<i128>;
            let mut valid = true;
            if let Some(a) = &q.target.excluded_automaton {
                bound = automaton_bound(a, positive, negative, &mut expired);
                valid = bound.is_some();
            }
            for component in &q.target.excluded_semilinear {
                if expired() {
                    break 'enumerate;
                }
                let value = |v: &[(usize, u64)]| {
                    v.iter().fold(0i128, |sum, &(i, w)| {
                        sum + if i == positive {
                            i128::from(w)
                        } else if Some(i) == negative {
                            -i128::from(w)
                        } else {
                            0
                        }
                    })
                };
                if component.periods.iter().any(|period| value(period) > 0) {
                    valid = false;
                    break;
                }
                let b = value(&component.base);
                bound = Some(bound.map_or(b, |old| old.max(b)));
            }
            if valid && let Some(bound) = bound.and_then(|b| i64::try_from(b + 1).ok()) {
                let candidate = Candidate {
                    positive,
                    negative,
                    bound,
                };
                // Inserting after equal ranks preserves enumeration order for ties.
                let index = result.partition_point(|old| old.rank() <= candidate.rank());
                if index < GOAL_LIMIT {
                    if result.len() == GOAL_LIMIT {
                        result.pop();
                    }
                    result.insert(index, candidate);
                }
            }
        }
    }
    result
}

fn automaton_bound(
    a: &crate::raw_target::SerialAutomaton,
    positive: usize,
    negative: Option<usize>,
    expired: &mut impl FnMut() -> bool,
) -> Option<i128> {
    use std::collections::{HashMap, HashSet};
    let mut vertices = HashSet::from([a.initial]);
    for edge in &a.edges {
        if expired() {
            return None;
        }
        vertices.insert(edge.source);
        vertices.insert(edge.target);
    }
    let mut distance = HashMap::from([(a.initial, 0i128)]);
    for pass in 0..vertices.len() {
        let mut changed = false;
        for edge in &a.edges {
            if expired() {
                return None;
            }
            if let Some(&prefix) = distance.get(&edge.source) {
                let weight = i128::from(edge.response == positive)
                    - i128::from(Some(edge.response) == negative);
                let value = prefix.checked_add(weight)?;
                if distance.get(&edge.target).is_none_or(|&old| value > old) {
                    distance.insert(edge.target, value);
                    changed = true;
                }
            }
        }
        if !changed {
            return a
                .accepting
                .iter()
                .filter_map(|state| distance.get(state))
                .copied()
                .max();
        }
        if pass + 1 == vertices.len() {
            // A reachable positive cycle prevents this conservative finite bound.
            return None;
        }
    }
    None
}

fn remove_dominated(candidates: &mut Vec<Candidate>) {
    let unary: Vec<_> = candidates
        .iter()
        .filter(|c| c.negative.is_none())
        .map(|c| (c.positive, c.bound))
        .collect();
    candidates.retain(|c| {
        c.negative.is_none()
            || !unary
                .iter()
                .any(|&(p, bound)| p == c.positive && bound <= c.bound)
    });
}

pub fn goals(q: &RawQuery, deadline: Instant) -> Vec<Constraint> {
    let mut retained = candidates(q, || Instant::now() >= deadline);
    remove_dominated(&mut retained);
    retained
        .into_iter()
        .map(|candidate| {
            let mut coefficients = vec![0; q.places.len()];
            coefficients[candidate.positive] = 1;
            if let Some(i) = candidate.negative {
                coefficients[i] = -1;
            }
            Constraint {
                coefficients,
                bound: candidate.bound,
                equality: false,
            }
        })
        .collect()
}
struct Profile {
    enabled: bool,
    start: Instant,
}
impl Profile {
    fn record(&self, phase: &str, details: impl FnOnce() -> serde_json::Value) {
        if self.enabled {
            eprintln!(
                "{}",
                serde_json::json!({
                    "raw_profile": phase,
                    "elapsed_seconds": self.start.elapsed().as_secs_f64(),
                    "details": details(),
                })
            );
        }
    }
}

pub fn solve(q: &RawQuery, timeout: Duration, max_states: usize) -> Outcome {
    let start = Instant::now();
    let deadline = start + timeout;
    let profile = Profile {
        enabled: std::env::var_os("VASS_RAW_PROFILE").is_some(),
        start,
    };
    if let Err(error) = q.validate() {
        return Outcome::unknown("raw-potential", &error.to_string(), 0);
    }
    let candidates = goals(q, start + timeout / 10);
    profile.record(
        "goals",
        || serde_json::json!({"candidates": candidates.len()}),
    );
    if Instant::now() >= deadline {
        return Outcome::unknown("raw-potential", "time limit", 0);
    }
    let original = q.net();
    let mut prepared = match Prepared::new(&original, &q.target.response_places, deadline) {
        Ok(prepared) => prepared,
        Err(_) if Instant::now() >= deadline => {
            return Outcome::unknown("raw-potential", "preparation time limit", 0);
        }
        Err(_) => Prepared::identity(&original),
    };
    profile.record("prepared", || {
        serde_json::json!({
            "places": original.places.len(),
            "original_transitions": original.transitions.len(),
            "reduced_transitions": prepared.net.transitions.len(),
        })
    });
    for (i, c) in candidates.iter().enumerate() {
        if Instant::now() >= deadline {
            break;
        }
        prepared.net.target.push(c.clone());
        let remaining = deadline.saturating_duration_since(Instant::now());
        let budget = remaining
            .min(timeout / 4)
            .min(remaining / (candidates.len() - i).min(8) as u32);
        profile.record("attempt-start", || serde_json::json!({
            "index": i, "budget_seconds": budget.as_secs_f64(), "bound": c.bound,
            "terms": c.coefficients.iter().enumerate().filter(|(_, a)| **a != 0).collect::<Vec<_>>(),
        }));
        let mut out = prepared.solve(
            &original,
            (Instant::now() + budget).min(deadline),
            max_states,
        );
        prepared.net.target.pop();
        profile.record("attempt-end", || {
            serde_json::json!({
                "index": i, "states": out.states, "verdict": out.verdict, "reason": out.reason,
            })
        });
        if out.verdict == "reachable"
            && matches!(
                q.accepts(
                    out.marking.as_ref().unwrap(),
                    deadline,
                    max_states.saturating_mul(10)
                ),
                Ok(true)
            )
            && Instant::now() < deadline
        {
            profile.record("accepted", || serde_json::json!({"index": i}));
            out.method = "raw-potential".into();
            out.reason =
                "serial-language potential violated; original raw target and trace checked".into();
            return out;
        }
    }
    profile.record("fallback-start", || serde_json::json!({}));
    let mut out =
        crate::raw_search::solve_prepared(q, &original, &prepared, deadline, max_states, true);
    profile.record("fallback-end", || {
        serde_json::json!({
            "states": out.states, "verdict": out.verdict, "reason": out.reason,
        })
    });
    out.method = "raw-potential".into();
    out
}
#[cfg(test)]
mod tests {
    use super::*;
    use crate::raw_target::{LinearSet, RawTarget};

    fn query(places: usize, responses: Vec<usize>, components: Vec<LinearSet>) -> RawQuery {
        RawQuery {
            format: "ser-raw-v1".into(),
            places: (0..places).map(|i| format!("p{i}")).collect(),
            initial: vec![0; places],
            transitions: vec![],
            target: RawTarget {
                excluded_automaton: None,
                kind: "completed-outside-semilinear".into(),
                zero_places: vec![],
                response_places: responses,
                excluded_semilinear: components,
            },
        }
    }

    fn exhaustive(q: &RawQuery, pair_limit: usize) -> Vec<Constraint> {
        let mut result = Vec::new();
        let mut pairs = 0;
        'enumerate: for &positive in &q.target.response_places {
            for negative in std::iter::once(None).chain(
                q.target
                    .response_places
                    .iter()
                    .copied()
                    .filter(|&i| i != positive)
                    .map(Some),
            ) {
                if pairs == pair_limit {
                    break 'enumerate;
                }
                pairs += 1;
                let mut coefficients = vec![0; q.places.len()];
                coefficients[positive] = 1;
                if let Some(i) = negative {
                    coefficients[i] = -1;
                }
                let value = |v: &[(usize, u64)]| -> i128 {
                    v.iter()
                        .map(|&(i, w)| i128::from(coefficients[i]) * i128::from(w))
                        .sum()
                };
                if q.target
                    .excluded_semilinear
                    .iter()
                    .flat_map(|component| &component.periods)
                    .any(|period| value(period) > 0)
                {
                    continue;
                }
                if let Some(bound) = q
                    .target
                    .excluded_semilinear
                    .iter()
                    .map(|component| value(&component.base))
                    .max()
                    .and_then(|bound| i64::try_from(bound + 1).ok())
                {
                    result.push(Constraint {
                        coefficients,
                        bound,
                        equality: false,
                    });
                }
            }
        }
        result.sort_by_key(|c| (c.bound, c.coefficients.iter().filter(|&&x| x != 0).count()));
        result.truncate(GOAL_LIMIT);
        result
    }

    #[test]
    fn bounded_retention_matches_exhaustive_ranking() {
        let mut seed = 271828u64;
        let mut next = || {
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            seed >> 32
        };
        for case in 0..96 {
            let count = 2 + case % 7;
            let responses: Vec<_> = (1..=count).rev().collect();
            let components = (0..case % 4)
                .map(|_| LinearSet {
                    base: responses.iter().map(|&i| (i, next() % 5)).collect(),
                    periods: (0..(case / 4) % 3)
                        .map(|_| responses.iter().map(|&i| (i, next() % 3)).collect())
                        .collect(),
                })
                .collect();
            let q = query(count + 2, responses, components);
            let actual = goals(&q, Instant::now() + Duration::from_secs(30));
            assert_eq!(
                serde_json::to_value(actual).unwrap(),
                serde_json::to_value(prune_reference(exhaustive(&q, usize::MAX))).unwrap(),
                "case {case}"
            );
        }
    }

    #[test]
    fn large_response_set_materializes_only_best_32_goals() {
        let q = query(
            1314,
            (0..512).rev().collect(),
            vec![LinearSet {
                base: vec![],
                periods: vec![],
            }],
        );
        let result = goals(&q, Instant::now() + Duration::from_secs(30));
        assert_eq!(result.len(), GOAL_LIMIT);
        assert_eq!(
            result.iter().map(|c| c.coefficients.len()).sum::<usize>(),
            32 * 1314
        );
        for (i, c) in result.iter().enumerate() {
            assert_eq!(c.bound, 1);
            assert_eq!(c.coefficients[511 - i], 1);
            assert_eq!(c.coefficients.iter().filter(|&&x| x != 0).count(), 1);
        }
    }

    #[test]
    fn deadline_returns_ranked_completed_candidates_only() {
        let q = query(
            3,
            vec![0, 1, 2],
            vec![
                LinearSet {
                    base: vec![(0, 5)],
                    periods: vec![],
                },
                LinearSet {
                    base: vec![(0, 3), (1, 2)],
                    periods: vec![],
                },
            ],
        );
        for expired_at in 0..=27 {
            let mut checks = 0;
            let actual = candidates(&q, || {
                let expired = checks == expired_at;
                checks += 1;
                expired
            });
            let expected = exhaustive(&q, expired_at / 3);
            let actual: Vec<_> = actual
                .iter()
                .map(|c| (c.positive, c.negative, c.bound))
                .collect();
            let expected: Vec<_> = expected
                .iter()
                .map(|c| {
                    (
                        c.coefficients.iter().position(|&x| x == 1).unwrap(),
                        c.coefficients.iter().position(|&x| x == -1),
                        c.bound,
                    )
                })
                .collect();
            assert_eq!(actual, expected, "expired at check {expired_at}");
        }
    }

    #[test]
    fn correlated_periods_give_difference_goals() {
        let q = RawQuery {
            format: "ser-raw-v1".into(),
            places: vec!["a".into(), "b".into()],
            initial: vec![0, 0],
            transitions: vec![],
            target: RawTarget {
                excluded_automaton: None,
                kind: "completed-outside-semilinear".into(),
                zero_places: vec![],
                response_places: vec![0, 1],
                excluded_semilinear: vec![LinearSet {
                    base: vec![(0, 1)],
                    periods: vec![vec![(0, 1), (1, 1)]],
                }],
            },
        };
        let cs = goals(&q, Instant::now() + Duration::from_secs(1));
        assert!(
            cs.iter()
                .any(|c| c.coefficients == vec![1, -1] && c.bound == 2)
        );
        for n in 0..20 {
            for c in &cs {
                let m = [n + 1, n];
                let value: i64 = c.coefficients.iter().zip(m).map(|(&a, v)| a * v).sum();
                assert!(value < c.bound);
            }
        }
    }
    #[test]
    fn reused_fallback_checks_nonmembership_without_potential_goals() {
        let mut q = query(
            1,
            vec![0],
            vec![LinearSet {
                base: vec![],
                periods: vec![vec![(0, 2)]],
            }],
        );
        q.transitions.push(crate::model::Transition {
            name: "emit".into(),
            pre: vec![],
            post: vec![(0, 1)],
        });
        assert!(goals(&q, Instant::now() + Duration::from_secs(1)).is_empty());
        let result = solve(&q, Duration::from_secs(1), 100);
        assert_eq!(result.verdict, "reachable");
        let m = q.net().check_witness(&result.trace).unwrap();
        assert_eq!(m, vec![1]);
        assert!(
            q.accepts(&m, Instant::now() + Duration::from_secs(1), 100)
                .unwrap()
        );
        assert_eq!(solve(&q, Duration::ZERO, 100).verdict, "unknown");
    }

    #[test]
    fn failed_goals_do_not_prove_raw_unreachability() {
        let q = query(
            2,
            vec![0, 1],
            vec![LinearSet {
                base: vec![],
                periods: vec![],
            }],
        );
        assert!(!goals(&q, Instant::now() + Duration::from_secs(1)).is_empty());
        let result = solve(&q, Duration::from_secs(1), 100);
        assert_eq!(result.verdict, "unknown");
    }
    fn prune_reference(goals: Vec<Constraint>) -> Vec<Constraint> {
        goals
            .iter()
            .filter(|goal| {
                let positive = goal.coefficients.iter().position(|&a| a == 1).unwrap();
                !goal.coefficients.contains(&-1)
                    || !goals.iter().any(|other| {
                        other.coefficients[positive] == 1
                            && other.coefficients.iter().filter(|&&a| a != 0).count() == 1
                            && other.bound <= goal.bound
                    })
            })
            .cloned()
            .collect()
    }

    #[test]
    fn dominance_preserves_goal_union_over_nonnegative_markings() {
        for unary_bound in -2..=5 {
            for pair_bound in -2..=5 {
                let mut candidates = vec![
                    Candidate {
                        positive: 0,
                        negative: None,
                        bound: unary_bound,
                    },
                    Candidate {
                        positive: 0,
                        negative: Some(1),
                        bound: pair_bound,
                    },
                    Candidate {
                        positive: 1,
                        negative: Some(0),
                        bound: pair_bound,
                    },
                ];
                let accepts = |cs: &[Candidate], m: [i64; 2]| {
                    cs.iter()
                        .any(|c| m[c.positive] - c.negative.map_or(0, |i| m[i]) >= c.bound)
                };
                let before: Vec<_> = (0..8)
                    .flat_map(|a| (0..8).map(move |b| [a, b]))
                    .map(|m| (m, accepts(&candidates, m)))
                    .collect();
                remove_dominated(&mut candidates);
                assert_eq!(
                    candidates.len(),
                    if unary_bound <= pair_bound { 2 } else { 3 }
                );
                for (m, expected) in before {
                    assert_eq!(accepts(&candidates, m), expected);
                }
                assert!(
                    candidates
                        .iter()
                        .any(|c| c.positive == 1 && c.negative == Some(0))
                );
            }
        }
    }
}
