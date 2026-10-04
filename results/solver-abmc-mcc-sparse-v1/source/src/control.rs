//! One-hot control projections certified by exact token conservation.
use crate::model::Problem;
use anyhow::{Context, Result, ensure};
use microlp::{ComparisonOp, OptimizationDirection};
use std::{collections::BTreeMap, time::Instant};

#[derive(Clone, Debug)]
pub struct Control {
    pub places: Vec<usize>,
    /// Original occupied place for each mode index.
    pub modes: Vec<usize>,
    pub initial: usize,
    pub edges: Vec<Edge>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Edge {
    pub source: usize,
    pub target: usize,
    pub transition: usize,
}

pub fn build(p: &Problem, places: &[usize], max_edges: usize) -> Result<Control> {
    construct(p, places, max_edges, None)
}

pub fn build_until(
    p: &Problem,
    places: &[usize],
    max_edges: usize,
    deadline: Instant,
) -> Result<Control> {
    construct(p, places, max_edges, Some(deadline))
}

fn construct(
    p: &Problem,
    places: &[usize],
    max_edges: usize,
    deadline: Option<Instant>,
) -> Result<Control> {
    let in_time = || deadline.is_none_or(|limit| Instant::now() < limit);
    ensure!(in_time(), "control deadline exhausted");
    p.validate()?;
    ensure!(!places.is_empty(), "empty control projection");
    ensure!(
        places.windows(2).all(|pair| pair[0] < pair[1])
            && places.iter().all(|&place| place < p.places.len()),
        "control places must be sorted, unique, and in range"
    );
    let mut selected = vec![false; p.places.len()];
    let mut tokens = 0u128;
    for &place in places {
        selected[place] = true;
        tokens = tokens
            .checked_add(u128::from(p.initial[place]))
            .context("control token sum overflow")?;
    }
    ensure!(tokens == 1, "control initially requires exactly one token");
    let initial_place = places
        .iter()
        .copied()
        .find(|&place| p.initial[place] == 1)
        .context("missing initial control place")?;
    let mut stuttering = vec![];
    let mut outgoing = vec![vec![]; p.places.len()];
    for (transition, tr) in p.transitions.iter().enumerate() {
        ensure!(in_time(), "control deadline exhausted");
        let sum = |arcs: &[(usize, u64)]| -> Result<u128> {
            arcs.iter().filter(|&&(place, _)| selected[place]).try_fold(
                0u128,
                |sum, &(_, weight)| {
                    sum.checked_add(u128::from(weight))
                        .context("control arc sum overflow")
                },
            )
        };
        let pre = sum(&tr.pre)?;
        let post = sum(&tr.post)?;
        ensure!(
            pre == post,
            "transition {transition} changes control token sum"
        );
        if pre == 0 {
            stuttering.push(transition);
        } else if pre == 1 {
            let source = tr
                .pre
                .iter()
                .find(|&&(place, _)| selected[place])
                .unwrap()
                .0;
            let target = tr
                .post
                .iter()
                .find(|&&(place, _)| selected[place])
                .unwrap()
                .0;
            outgoing[source].push((transition, target));
        }
        // Consuming two selected tokens is disabled in every one-hot marking,
        // including when the same tokens would subsequently be produced.
    }
    let mut control = Control {
        places: places.to_vec(),
        modes: vec![initial_place],
        initial: 0,
        edges: vec![],
    };
    let mut mode_of_place = vec![None; p.places.len()];
    mode_of_place[initial_place] = Some(0);
    let mut source = 0;
    while source < control.modes.len() {
        ensure!(in_time(), "control deadline exhausted");
        let place = control.modes[source];
        for (transition, target_place) in stuttering
            .iter()
            .map(|&transition| (transition, place))
            .chain(outgoing[place].iter().copied())
        {
            ensure!(in_time(), "control deadline exhausted");
            ensure!(
                control.edges.len() < max_edges,
                "control edge limit exhausted"
            );
            let target = match mode_of_place[target_place] {
                Some(mode) => mode,
                None => {
                    let mode = control.modes.len();
                    mode_of_place[target_place] = Some(mode);
                    control.modes.push(target_place);
                    mode
                }
            };
            control.edges.push(Edge {
                source,
                target,
                transition,
            });
        }
        source += 1;
    }
    Ok(control)
}

pub fn discover(p: &Problem, deadline: Instant, max_edges: usize) -> Option<Control> {
    if Instant::now() >= deadline || p.validate().is_err() || p.places.is_empty() {
        return None;
    }
    let mut lp = microlp::Problem::new(OptimizationDirection::Maximize);
    let mut variables = Vec::with_capacity(p.places.len());
    for _ in &p.places {
        if Instant::now() >= deadline {
            return None;
        }
        variables.push(lp.add_binary_var(1.0));
    }
    lp.add_constraint(
        p.initial
            .iter()
            .enumerate()
            .filter(|&(_, &tokens)| tokens != 0)
            .map(|(place, &tokens)| (variables[place], tokens as f64)),
        ComparisonOp::Eq,
        1.0,
    );
    for tr in &p.transitions {
        if Instant::now() >= deadline {
            return None;
        }
        let mut incidence = BTreeMap::<usize, i128>::new();
        for &(place, weight) in &tr.pre {
            *incidence.entry(place).or_default() -= i128::from(weight);
        }
        for &(place, weight) in &tr.post {
            *incidence.entry(place).or_default() += i128::from(weight);
        }
        lp.add_constraint(
            incidence
                .into_iter()
                .filter(|&(_, effect)| effect != 0)
                .map(|(place, effect)| (variables[place], effect as f64)),
            ComparisonOp::Eq,
            0.0,
        );
    }
    if Instant::now() >= deadline {
        return None;
    }
    lp.set_time_limit(deadline.saturating_duration_since(Instant::now()));
    let solution = lp.solve().ok()?.into_solution().ok()?;
    let mut places = vec![];
    for (place, &variable) in variables.iter().enumerate() {
        let value = solution.var_value(variable).round();
        if !value.is_finite() || !(0.0..=1.0).contains(&value) {
            return None;
        }
        if value == 1.0 {
            places.push(place);
        }
    }
    construct(p, &places, max_edges, Some(deadline)).ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Transition;
    use std::time::Duration;

    fn example() -> Problem {
        Problem {
            places: vec!["a".into(), "b".into(), "unreachable".into(), "data".into()],
            initial: vec![1, 0, 0, 0],
            transitions: vec![
                Transition {
                    name: "advance".into(),
                    pre: vec![(0, 1), (3, 7)],
                    post: vec![(1, 1)],
                },
                Transition {
                    name: "read".into(),
                    pre: vec![(1, 1)],
                    post: vec![(1, 1), (3, 1)],
                },
                Transition {
                    name: "source".into(),
                    pre: vec![],
                    post: vec![(3, 1)],
                },
                Transition {
                    name: "weighted_read".into(),
                    pre: vec![(1, 2)],
                    post: vec![(1, 2)],
                },
                Transition {
                    name: "two_controls".into(),
                    pre: vec![(0, 1), (1, 1)],
                    post: vec![(0, 1), (1, 1)],
                },
            ],
            target: vec![],
        }
    }

    #[test]
    fn control_edges_preserve_reads_and_ignore_data_enabling() {
        let p = example();
        let control = build(&p, &[0, 1, 2], 100).unwrap();
        assert_eq!(control.places, [0, 1, 2]);
        assert_eq!(control.modes, [0, 1]);
        assert_eq!(control.initial, 0);
        let mut edges: Vec<_> = control
            .edges
            .iter()
            .map(|edge| (edge.source, edge.target, edge.transition))
            .collect();
        edges.sort_unstable();
        assert_eq!(edges, [(0, 0, 2), (0, 1, 0), (1, 1, 1), (1, 1, 2)]);
    }

    #[test]
    fn invalid_selected_sets_are_rejected() {
        let p = example();
        for places in [&[][..], &[0, 0], &[1, 0], &[4], &[1], &[0], &[0, 1, 3]] {
            assert!(build(&p, places, 100).is_err(), "accepted {places:?}");
        }
        let mut changed = p.clone();
        changed.initial[1] = 1;
        assert!(build(&changed, &[0, 1, 2], 100).is_err());
        changed.initial[1] = 0;
        changed.transitions[0].post[0].1 = 2;
        assert!(build(&changed, &[0, 1, 2], 100).is_err());
    }

    #[test]
    fn mode_indices_are_distinct_from_original_places() {
        let mut p = example();
        p.initial = vec![0, 0, 1, 0];
        let control = build(&p, &[0, 1, 2], 100).unwrap();
        assert_eq!(control.modes, [2]);
        assert_eq!(control.initial, 0);
        assert_eq!(
            control.edges,
            [Edge {
                source: 0,
                target: 0,
                transition: 2,
            }]
        );
    }

    #[test]
    fn large_arc_totals_are_checked_exactly() {
        let mut p = example();
        p.transitions = vec![Transition {
            name: "huge".into(),
            pre: vec![(0, u64::MAX), (1, u64::MAX)],
            post: vec![(0, u64::MAX), (1, u64::MAX)],
        }];
        assert!(build(&p, &[0, 1], 0).unwrap().edges.is_empty());
        p.transitions[0].post[1].1 -= 1;
        assert!(build(&p, &[0, 1], 0).is_err());
    }

    #[test]
    fn edge_limit_never_returns_a_partial_graph() {
        let p = example();
        assert!(build(&p, &[0, 1], 3).is_err());
        assert_eq!(build(&p, &[0, 1], 4).unwrap().edges.len(), 4);
    }

    #[test]
    fn discovery_works_beyond_twelve_places_without_names() {
        let size = 20;
        let p = Problem {
            places: (0..size).map(|_| String::new()).collect(),
            initial: (0..size).map(|place| u64::from(place == 0)).collect(),
            transitions: (0..size)
                .map(|place| Transition {
                    name: String::new(),
                    pre: vec![(place, 1)],
                    post: vec![((place + 1) % size, 1)],
                })
                .collect(),
            target: vec![],
        };
        let control = discover(&p, Instant::now() + Duration::from_secs(2), 100).unwrap();
        assert_eq!(control.places.len(), size);
        assert_eq!(control.modes.len(), size);
        assert_eq!(control.edges.len(), size);
    }

    #[test]
    fn discovery_rejects_an_expired_deadline_or_no_invariant() {
        let mut p = example();
        assert!(discover(&p, Instant::now(), 100).is_none());
        p.initial.fill(0);
        assert!(discover(&p, Instant::now() + Duration::from_secs(1), 100).is_none());
    }
}
