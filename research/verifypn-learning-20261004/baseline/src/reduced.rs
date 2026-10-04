//! Demand-driven source creation and eager private completion, with trace lifting.
use crate::{guided, model::Problem, search::Outcome};
use std::time::{Duration, Instant};

pub(crate) struct Prepared {
    pub net: Problem,
    pub recipes: Vec<Vec<usize>>,
}

impl Prepared {
    pub fn identity(p: &Problem) -> Self {
        Self {
            net: p.clone(),
            recipes: (0..p.transitions.len()).map(|t| vec![t]).collect(),
        }
    }

    pub fn new(p: &Problem, protected: &[usize], deadline: Instant) -> Result<Self, &'static str> {
        prepare(p, protected, || Instant::now() >= deadline)
    }

    pub fn lift(&self, trace: &[usize]) -> Vec<usize> {
        trace
            .iter()
            .flat_map(|&t| self.recipes[t].iter().copied())
            .collect()
    }

    pub fn solve(&self, original: &Problem, deadline: Instant, max_states: usize) -> Outcome {
        if Instant::now() >= deadline {
            return Outcome::unknown("reduced-guided", "time limit", 0);
        }
        let mut out = guided::solve_quotient(
            &self.net,
            deadline.saturating_duration_since(Instant::now()),
            max_states,
        );
        if Instant::now() >= deadline {
            return Outcome::unknown("reduced-guided", "time limit", out.states);
        }
        if out.verdict == "reachable" {
            let trace = self.lift(&out.trace);
            match original.check_witness(&trace) {
                Ok(marking) => {
                    out.trace = trace;
                    out.marking = Some(marking);
                    out.reason = "replayed lifted demand-source/eager-completion witness".into();
                }
                Err(_) => {
                    return Outcome::unknown(
                        "reduced-guided",
                        "lifted witness check failed",
                        out.states,
                    );
                }
            }
        }
        if Instant::now() >= deadline {
            return Outcome::unknown("reduced-guided", "time limit", out.states);
        }
        out.method = "reduced-guided".into();
        out
    }
}

pub fn transform(p: &Problem) -> Result<(Problem, Vec<Vec<usize>>), &'static str> {
    transform_protected(p, &[])
}
pub fn transform_protected(
    p: &Problem,
    protected: &[usize],
) -> Result<(Problem, Vec<Vec<usize>>), &'static str> {
    let prepared = prepare(p, protected, || false)?;
    Ok((prepared.net, prepared.recipes))
}

fn prepare(
    p: &Problem,
    protected: &[usize],
    mut expired: impl FnMut() -> bool,
) -> Result<Prepared, &'static str> {
    let mut tick = || {
        if expired() {
            Err("preparation time limit")
        } else {
            Ok(())
        }
    };
    tick()?;
    let mut disposable: Vec<_> = p.initial.iter().map(|&n| n == 0).collect();
    for &place in protected {
        *disposable.get_mut(place).ok_or("invalid protected place")? = false;
    }
    for c in &p.target {
        tick()?;
        let zero_support = c.equality
            && c.bound == 0
            && (c.coefficients.iter().all(|&a| a >= 0) || c.coefficients.iter().all(|&a| a <= 0));
        if !zero_support {
            for (place, &a) in c.coefficients.iter().enumerate() {
                disposable[place] &= a == 0;
            }
        }
    }
    let mut producers = vec![vec![]; p.places.len()];
    let mut consumers = vec![vec![]; p.places.len()];
    for (t, tr) in p.transitions.iter().enumerate() {
        tick()?;
        for &(place, _) in &tr.pre {
            consumers[place].push(t);
        }
        for &(place, _) in &tr.post {
            producers[place].push(t);
        }
    }
    tick()?;
    let mut net = p.clone();
    let mut before = vec![vec![]; p.transitions.len()];
    let mut after = before.clone();
    let mut disabled = vec![false; p.transitions.len()];
    for place in 0..p.places.len() {
        tick()?;
        if !disposable[place] {
            continue;
        }
        if let [source] = producers[place].as_slice() {
            let source = *source;
            let tr = &p.transitions[source];
            if tr.pre.is_empty() && tr.post == vec![(place, 1)] {
                disabled[source] = true;
                for &t in &consumers[place] {
                    tick()?;
                    let tr = &mut net.transitions[t];
                    if let Some(pos) = tr.pre.iter().position(|&(i, _)| i == place) {
                        let (_, w) = tr.pre.remove(pos);
                        if w > 1024 {
                            return Err("source expansion limit");
                        }
                        before[t].extend(std::iter::repeat_n(source, w as usize));
                    }
                }
            }
        }
        if let [sink] = consumers[place].as_slice() {
            let sink = *sink;
            let tr = &p.transitions[sink];
            if tr.pre == vec![(place, 1)] && tr.post.iter().all(|&(i, _)| consumers[i].is_empty()) {
                disabled[sink] = true;
                // Added post-arcs go only to originally unread places. They cannot
                // become later private sinks, so original incidence suffices here.
                for &t in &producers[place] {
                    tick()?;
                    let nt = &mut net.transitions[t];
                    if let Some(pos) = nt.post.iter().position(|&(i, _)| i == place) {
                        let (_, w) = nt.post.remove(pos);
                        if w > 1024 {
                            return Err("completion expansion limit");
                        }
                        for &(i, v) in &tr.post {
                            let v = v.checked_mul(w).ok_or("arc overflow")?;
                            if let Some((_, old)) = nt.post.iter_mut().find(|(j, _)| *j == i) {
                                *old = old.checked_add(v).ok_or("arc overflow")?;
                            } else {
                                nt.post.push((i, v));
                            }
                        }
                        after[t].extend(std::iter::repeat_n(sink, w as usize));
                    }
                }
            }
        }
    }
    let mut recipes = Vec::new();
    let mut transitions = Vec::new();
    for (original, tr) in net.transitions.into_iter().enumerate() {
        tick()?;
        if disabled[original] {
            continue;
        }
        let mut recipe = std::mem::take(&mut before[original]);
        recipe.push(original);
        recipe.append(&mut after[original]);
        recipes.push(recipe);
        transitions.push(tr);
    }
    net.transitions = transitions;
    tick()?;
    Ok(Prepared { net, recipes })
}

pub fn solve(p: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    let deadline = Instant::now() + timeout;
    match Prepared::new(p, &[], deadline) {
        Ok(prepared) => prepared.solve(p, deadline, max_states),
        Err(reason) => Outcome::unknown("reduced-guided", reason, 0),
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Constraint, Transition};
    fn disposable(p: &Problem, place: usize) -> bool {
        p.initial[place] == 0
            && p.target.iter().all(|c| {
                c.coefficients[place] == 0
                    || (c.equality
                        && c.bound == 0
                        && c.coefficients
                            .iter()
                            .enumerate()
                            .all(|(i, &a)| i == place || a == 0))
            })
    }
    fn reference(
        p: &Problem,
        protected: &[usize],
    ) -> Result<(Problem, Vec<Vec<usize>>), &'static str> {
        let mut net = p.clone();
        let mut before = vec![vec![]; p.transitions.len()];
        let mut after = before.clone();
        let mut disabled = vec![false; p.transitions.len()];
        for place in 0..p.places.len() {
            if protected.contains(&place) || !disposable(p, place) {
                continue;
            }
            let producers: Vec<_> = p
                .transitions
                .iter()
                .enumerate()
                .filter(|(_, t)| t.post.iter().any(|&(i, _)| i == place))
                .map(|(i, _)| i)
                .collect();
            if producers.len() == 1 {
                let source = producers[0];
                let tr = &p.transitions[source];
                if tr.pre.is_empty() && tr.post == vec![(place, 1)] {
                    disabled[source] = true;
                    for (t, tr) in net.transitions.iter_mut().enumerate() {
                        if let Some(pos) = tr.pre.iter().position(|&(i, _)| i == place) {
                            let (_, w) = tr.pre.remove(pos);
                            if w > 1024 {
                                return Err("source expansion limit");
                            }
                            before[t].extend(std::iter::repeat_n(source, w as usize));
                        }
                    }
                }
            }
            let consumers: Vec<_> = p
                .transitions
                .iter()
                .enumerate()
                .filter(|(_, t)| t.pre.iter().any(|&(i, _)| i == place))
                .map(|(i, _)| i)
                .collect();
            if consumers.len() == 1 {
                let sink = consumers[0];
                let tr = &p.transitions[sink];
                if tr.pre == vec![(place, 1)]
                    && tr.post.iter().all(|&(i, _)| {
                        p.transitions
                            .iter()
                            .all(|t| t.pre.iter().all(|&(j, _)| i != j))
                    })
                {
                    disabled[sink] = true;
                    for (t, nt) in net.transitions.iter_mut().enumerate() {
                        if let Some(pos) = nt.post.iter().position(|&(i, _)| i == place) {
                            let (_, w) = nt.post.remove(pos);
                            if w > 1024 {
                                return Err("completion expansion limit");
                            }
                            for &(i, v) in &tr.post {
                                let Some(v) = v.checked_mul(w) else {
                                    return Err("arc overflow");
                                };
                                if let Some((_, old)) = nt.post.iter_mut().find(|(j, _)| *j == i) {
                                    let Some(sum) = old.checked_add(v) else {
                                        return Err("arc overflow");
                                    };
                                    *old = sum;
                                } else {
                                    nt.post.push((i, v));
                                }
                            }
                            after[t].extend(std::iter::repeat_n(sink, w as usize));
                        }
                    }
                }
            }
        }
        let map: Vec<_> = (0..p.transitions.len()).filter(|&i| !disabled[i]).collect();
        net.transitions = map.iter().map(|&i| net.transitions[i].clone()).collect();
        let recipes = map
            .iter()
            .map(|&original| {
                let mut recipe = before[original].clone();
                recipe.push(original);
                recipe.extend_from_slice(&after[original]);
                recipe
            })
            .collect();
        Ok((net, recipes))
    }

    #[test]
    fn lifted_trace() {
        let p = Problem {
            places: vec!["pending".into(), "done".into(), "response".into()],
            initial: vec![0, 0, 0],
            transitions: vec![
                Transition {
                    name: "spawn".into(),
                    pre: vec![],
                    post: vec![(0, 1)],
                },
                Transition {
                    name: "run".into(),
                    pre: vec![(0, 1)],
                    post: vec![(1, 1)],
                },
                Transition {
                    name: "finish".into(),
                    pre: vec![(1, 1)],
                    post: vec![(2, 1)],
                },
            ],
            target: vec![
                Constraint {
                    coefficients: vec![1, 0, 0],
                    bound: 0,
                    equality: true,
                },
                Constraint {
                    coefficients: vec![0, 1, 0],
                    bound: 0,
                    equality: true,
                },
                Constraint {
                    coefficients: vec![0, 0, 1],
                    bound: 2,
                    equality: false,
                },
            ],
        };
        let out = solve(&p, Duration::from_secs(1), 100);
        assert_eq!(out.verdict, "reachable");
        p.check_witness(&out.trace).unwrap();
    }
    fn weighted() -> Problem {
        Problem {
            places: ["source", "pending", "response", "other_pending"]
                .map(str::to_owned)
                .to_vec(),
            initial: vec![0; 4],
            transitions: vec![
                Transition {
                    name: "source".into(),
                    pre: vec![],
                    post: vec![(0, 1)],
                },
                Transition {
                    name: "work".into(),
                    pre: vec![(0, 2)],
                    post: vec![(1, 3), (3, 2)],
                },
                Transition {
                    name: "finish".into(),
                    pre: vec![(1, 1)],
                    post: vec![(2, 4)],
                },
                Transition {
                    name: "finish_other".into(),
                    pre: vec![(3, 1)],
                    post: vec![(2, 5)],
                },
            ],
            target: [0, 1, 3]
                .map(|i| {
                    let mut coefficients = vec![0; 4];
                    coefficients[i] = 1;
                    Constraint {
                        coefficients,
                        bound: 0,
                        equality: true,
                    }
                })
                .to_vec(),
        }
    }

    fn same_as_reference(p: &Problem, protected: &[usize]) {
        let actual = transform_protected(p, protected);
        let mut expanded = p.clone();
        expanded.target = p
            .target
            .iter()
            .flat_map(|c| {
                let terms: Vec<_> = c
                    .coefficients
                    .iter()
                    .enumerate()
                    .filter(|(_, a)| **a != 0)
                    .collect();
                if c.equality
                    && c.bound == 0
                    && terms
                        .windows(2)
                        .all(|pair| pair[0].1.signum() == pair[1].1.signum())
                {
                    terms
                        .iter()
                        .map(|&(i, _)| {
                            let mut coefficients = vec![0; p.places.len()];
                            coefficients[i] = 1;
                            Constraint {
                                coefficients,
                                bound: 0,
                                equality: true,
                            }
                        })
                        .collect::<Vec<_>>()
                } else {
                    vec![c.clone()]
                }
            })
            .collect();
        let expected = reference(&expanded, protected).map(|(mut net, recipes)| {
            net.target = p.target.clone();
            (net, recipes)
        });
        assert_eq!(
            serde_json::to_value(actual).unwrap(),
            serde_json::to_value(expected).unwrap()
        );
    }

    #[test]
    fn indexed_reduction_matches_original_scans() {
        let mut seed = 20260927u64;
        let mut next = || {
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            seed >> 32
        };
        for case in 0..512 {
            let mut p = weighted();
            for _ in 0..case % 5 {
                let mut arcs = || {
                    (0..4)
                        .filter_map(|i| {
                            let w = next() % 5;
                            (w > 2).then(|| (i, w - 2))
                        })
                        .collect()
                };
                p.transitions.push(Transition {
                    name: "extra".into(),
                    pre: arcs(),
                    post: arcs(),
                });
            }
            for n in &mut p.initial {
                *n = u64::from(next() % 8 == 0);
            }
            if case % 2 == 0 {
                p.target.push(Constraint {
                    coefficients: (0..4).map(|_| (next() % 3) as i64 - 1).collect(),
                    bound: (next() % 3) as i64 - 1,
                    equality: case % 3 == 0,
                });
            }
            p.validate().unwrap();
            same_as_reference(&p, &[]);
            same_as_reference(&p, &[case % 4]);
        }
        for w in [1, 1024, 1025, u64::MAX] {
            let mut p = weighted();
            p.transitions[1].pre[0].1 = w;
            same_as_reference(&p, &[2]);
            p.transitions[1].pre[0].1 = 2;
            p.transitions[1].post[0].1 = w;
            same_as_reference(&p, &[2]);
            p.transitions[1].post[0].1 = 3;
            p.transitions[2].post[0].1 = w;
            same_as_reference(&p, &[2]);
        }
    }

    #[test]
    fn weighted_recipes_accumulate_shared_sink_outputs() {
        let p = weighted();
        let prepared = Prepared::new(&p, &[2], Instant::now() + Duration::from_secs(1)).unwrap();
        assert_eq!(prepared.net.transitions.len(), 1);
        assert_eq!(prepared.net.transitions[0].post, vec![(2, 22)]);
        assert_eq!(prepared.recipes, vec![vec![0, 0, 1, 2, 2, 2, 3, 3]]);
        let trace = prepared.lift(&[0, 0]);
        assert_eq!(p.check_witness(&trace).unwrap(), vec![0, 0, 44, 0]);
    }

    #[test]
    fn preparation_exhaustion_discards_partial_rewrites() {
        let p = weighted();
        assert_eq!(
            transform_protected(&p, &[p.places.len()]).err(),
            Some("invalid protected place")
        );
        let mut checks = 0;
        prepare(&p, &[2], || {
            checks += 1;
            false
        })
        .unwrap();
        for limit in 0..checks {
            let mut remaining = limit;
            let result = prepare(&p, &[2], || {
                if remaining == 0 {
                    true
                } else {
                    remaining -= 1;
                    false
                }
            });
            assert_eq!(result.err(), Some("preparation time limit"));
        }
        let prepared = Prepared::new(&p, &[2], Instant::now() + Duration::from_secs(1)).unwrap();
        assert_eq!(prepared.solve(&p, Instant::now(), 100).verdict, "unknown");
        assert_eq!(solve(&p, Duration::ZERO, 100).verdict, "unknown");
    }

    #[test]
    fn prepared_goals_preserve_all_response_coordinates() {
        let p = Problem {
            places: vec!["a".into(), "b".into()],
            initial: vec![0, 0],
            transitions: vec![
                Transition {
                    name: "a".into(),
                    pre: vec![],
                    post: vec![(0, 1)],
                },
                Transition {
                    name: "b".into(),
                    pre: vec![],
                    post: vec![(1, 1)],
                },
            ],
            target: vec![],
        };
        let deadline = Instant::now() + Duration::from_secs(2);
        let mut prepared = Prepared::new(&p, &[0, 1], deadline).unwrap();
        assert_eq!(prepared.net.transitions.len(), 2);
        for coefficients in [vec![1, -1], vec![-1, 1]] {
            let goal = Constraint {
                coefficients,
                bound: 2,
                equality: false,
            };
            prepared.net.target.push(goal.clone());
            let result = prepared.solve(&p, deadline, 100);
            assert_eq!(result.verdict, "reachable");
            let mut original_goal = p.clone();
            original_goal.target.push(goal);
            original_goal.check_witness(&result.trace).unwrap();
            prepared.net.target.pop();
        }
        assert!(p.target.is_empty() && prepared.net.target.is_empty());
    }
    #[test]
    fn combined_zero_support_preserves_lifting_and_protection() {
        let expanded = weighted();
        for coefficients in [vec![1, 1, 0, 1], vec![-1, i64::MIN, 0, -5]] {
            let mut combined = expanded.clone();
            combined.target = vec![Constraint {
                coefficients,
                bound: 0,
                equality: true,
            }];
            for protected in [&[2][..], &[1, 2][..]] {
                same_as_reference(&combined, protected);
                let a = transform_protected(&expanded, protected).unwrap();
                let b = transform_protected(&combined, protected).unwrap();
                assert_eq!(
                    serde_json::to_value(&a.0.transitions).unwrap(),
                    serde_json::to_value(&b.0.transitions).unwrap()
                );
                assert_eq!(a.1, b.1);
            }
            let mut prepared =
                Prepared::new(&combined, &[2], Instant::now() + Duration::from_secs(1)).unwrap();
            prepared.net.target.push(Constraint {
                coefficients: vec![0, 0, 1, 0],
                bound: 44,
                equality: false,
            });
            let result = prepared.solve(&combined, Instant::now() + Duration::from_secs(1), 100);
            assert_eq!(result.verdict, "reachable");
            expanded.check_witness(&result.trace).unwrap();
            assert_eq!(result.marking, Some(vec![0, 0, 44, 0]));
        }
    }

    #[test]
    fn mixed_sign_equality_does_not_force_zero_coordinates() {
        let mut p = weighted();
        p.target = vec![Constraint {
            coefficients: vec![1, -1, 0, 0],
            bound: 0,
            equality: true,
        }];
        let (net, recipes) = transform_protected(&p, &[2]).unwrap();
        assert!(net.transitions.iter().any(|t| t.name == "source"));
        assert!(net.transitions.iter().any(|t| t.name == "finish"));
        assert!(recipes.iter().any(|r| r == &[0]));
        same_as_reference(&p, &[2]);
    }
}
