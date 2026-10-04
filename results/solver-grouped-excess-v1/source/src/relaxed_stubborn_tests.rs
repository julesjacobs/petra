use super::*;
use crate::model::{Constraint, Transition};

type Arcs = Vec<(Vec<(usize, u64)>, Vec<(usize, u64)>)>;

fn problem(initial: Vec<u64>, arcs: Arcs, target: Vec<Constraint>) -> Problem {
    Problem {
        places: (0..initial.len()).map(|i| format!("p{i}")).collect(),
        initial,
        transitions: arcs
            .into_iter()
            .enumerate()
            .map(|(i, (pre, post))| Transition {
                name: format!("t{i}"),
                pre,
                post,
            })
            .collect(),
        target,
    }
}

fn goal(coefficients: Vec<i64>, bound: i64, equality: bool) -> Constraint {
    Constraint {
        coefficients,
        bound,
        equality,
    }
}

fn marking(values: &[u64]) -> Marking {
    values
        .iter()
        .copied()
        .enumerate()
        .filter(|&(_, n)| n != 0)
        .collect::<Vec<_>>()
        .into()
}

// Closure tests include transitions that the production relevance slice removes.
fn unsliced_graph(p: &Problem) -> Graph {
    let mut facts: Vec<_> = p
        .transitions
        .iter()
        .flat_map(|t| t.pre.iter().copied())
        .collect();
    facts.sort_unstable();
    facts.dedup();
    let actions = p
        .transitions
        .iter()
        .enumerate()
        .map(|(original, t)| {
            let mut delta = vec![0i128; p.places.len()];
            for &(place, weight) in &t.pre {
                delta[place] -= i128::from(weight);
            }
            for &(place, weight) in &t.post {
                delta[place] += i128::from(weight);
            }
            Action {
                original,
                guards: t
                    .pre
                    .iter()
                    .map(|arc| facts.binary_search(arc).unwrap())
                    .collect(),
                delta: delta
                    .into_iter()
                    .enumerate()
                    .filter(|&(_, d)| d != 0)
                    .collect(),
                produces: vec![],
                effects: vec![],
            }
        })
        .collect();
    Graph {
        retained_places: vec![true; p.places.len()],
        users: vec![vec![]; facts.len()],
        facts,
        actions,
    }
}

fn reduced_actions(selection: Selection) -> Vec<usize> {
    match selection {
        Selection::Reduced(successors) => successors.into_iter().map(|(t, _)| t).collect(),
        Selection::Full(reason) => panic!("expected a reduction, got {reason:?}"),
        Selection::TargetReduced(actions) => actions,
    }
}

fn assert_full(selection: Selection, expected: FullExpansion) {
    match selection {
        Selection::Full(reason) => assert_eq!(reason, expected),
        Selection::Reduced(_) | Selection::TargetReduced(_) => panic!("expected full expansion"),
    }
}

#[test]
fn weighted_necessary_enablers_include_net_producers_and_exclude_read_loops() {
    let p = problem(
        vec![1, 1, 0, 0],
        vec![
            (vec![(0, 1)], vec![(2, 1)]),
            (vec![(0, 1), (1, 3)], vec![(3, 1)]),
            (vec![(1, 1)], vec![(1, 2)]),
            (vec![(1, 1)], vec![(1, 1)]),
            (vec![], vec![(3, 1)]),
            (vec![], vec![(1, 1)]),
        ],
        vec![goal(vec![0, 0, 0, 1], 1, false)],
    );
    let graph = unsliced_graph(&p);
    let deadline = Instant::now() + Duration::from_secs(2);
    let index = Stubborn::new(&graph, &p, deadline).unwrap();
    let m = marking(&p.initial);
    let seen = HashSet::from([m.clone()]);
    assert_eq!(
        reduced_actions(
            index
                .select(&m, &[0, 2, 3, 4, 5], 1, &seen, deadline)
                .unwrap()
        ),
        vec![0, 2, 5]
    );
    let m = marking(&[1, 3, 0, 0]);
    assert_full(
        index
            .select(&m, &[0, 1, 2, 3, 4, 5], 1, &seen, deadline)
            .unwrap(),
        FullExpansion::Visible,
    );
}

#[test]
fn symmetric_dependencies_include_readers_disabled_by_a_consumer() {
    let p = problem(
        vec![1, 0, 0],
        vec![
            (vec![(0, 1)], vec![(1, 1)]),
            (vec![(0, 1)], vec![(0, 1), (2, 1)]),
        ],
        vec![goal(vec![0, 0, 1], 1, false)],
    );
    let graph = unsliced_graph(&p);
    let deadline = Instant::now() + Duration::from_secs(2);
    let index = Stubborn::new(&graph, &p, deadline).unwrap();
    let m = marking(&p.initial);
    assert_full(
        index
            .select(&m, &[0, 1], 1, &HashSet::from([m.clone()]), deadline)
            .unwrap(),
        FullExpansion::Visible,
    );
}

#[test]
fn no_op_read_loop_forces_seen_successor_fallback() {
    let p = problem(
        vec![1, 0],
        vec![
            (vec![(0, 1)], vec![(0, 1)]),
            (vec![(0, 1)], vec![(0, 1), (1, 1)]),
        ],
        vec![goal(vec![0, 1], 1, false)],
    );
    let graph = unsliced_graph(&p);
    let deadline = Instant::now() + Duration::from_secs(2);
    let index = Stubborn::new(&graph, &p, deadline).unwrap();
    let m = marking(&p.initial);
    assert_full(
        index
            .select(&m, &[0, 1], 1, &HashSet::from([m.clone()]), deadline)
            .unwrap(),
        FullExpansion::Seen,
    );
}

#[test]
fn any_seen_successor_forces_full_expansion_even_when_another_is_fresh() {
    let p = problem(
        vec![1, 0, 0, 0],
        vec![
            (vec![(0, 1)], vec![(1, 1)]),
            (vec![(0, 1)], vec![(2, 1)]),
            (vec![], vec![(3, 1)]),
        ],
        vec![goal(vec![0, 0, 0, 1], 1, false)],
    );
    let graph = unsliced_graph(&p);
    let deadline = Instant::now() + Duration::from_secs(2);
    let index = Stubborn::new(&graph, &p, deadline).unwrap();
    let m = marking(&p.initial);
    let mut seen = HashSet::from([m.clone()]);
    assert_eq!(
        reduced_actions(index.select(&m, &[0, 1, 2], 1, &seen, deadline).unwrap()),
        vec![0, 1]
    );
    seen.insert(graph.fire(&m, 1).unwrap().unwrap());
    for depth in [1, 2, 7, 9, 17] {
        assert_full(
            index
                .select(&m, &[0, 1, 2], depth, &seen, deadline)
                .unwrap(),
            FullExpansion::Seen,
        );
    }
}

#[test]
fn duplicate_fresh_successors_share_the_pre_expansion_seen_snapshot() {
    let p = problem(
        vec![1, 0, 0],
        vec![
            (vec![(0, 1)], vec![(1, 1)]),
            (vec![(0, 1)], vec![(1, 1)]),
            (vec![], vec![(2, 1)]),
        ],
        vec![goal(vec![0, 0, 1], 1, false)],
    );
    let graph = unsliced_graph(&p);
    let deadline = Instant::now() + Duration::from_secs(2);
    let index = Stubborn::new(&graph, &p, deadline).unwrap();
    let m = marking(&p.initial);
    let seen = HashSet::from([m.clone()]);
    assert_eq!(
        reduced_actions(index.select(&m, &[1, 0, 2], 1, &seen, deadline).unwrap()),
        vec![1, 0]
    );
    assert_eq!(seen.len(), 1);
}

#[test]
fn target_support_visibility_covers_signed_inequalities_and_equalities() {
    for target in [
        vec![goal(vec![1, 0], 0, true), goal(vec![0, 1], 1, false)],
        vec![goal(vec![-1, 1], 1, false)],
        vec![goal(vec![-1, 1], 1, true)],
    ] {
        let p = problem(
            vec![0, 0],
            vec![(vec![], vec![(0, 1)]), (vec![], vec![(1, 1)])],
            target,
        );
        let graph = unsliced_graph(&p);
        let deadline = Instant::now() + Duration::from_secs(2);
        let index = Stubborn::new(&graph, &p, deadline).unwrap();
        let m = marking(&p.initial);
        assert_full(
            index
                .select(&m, &[0, 1], 1, &HashSet::from([m.clone()]), deadline)
                .unwrap(),
            FullExpansion::Visible,
        );
        let out = run(
            &p,
            Duration::from_secs(2),
            100,
            false,
            Reduction::Invisible,
            false,
        );
        assert_eq!(out.verdict, "reachable", "{}", out.reason);
        p.check_witness(&out.trace).unwrap();
    }
}

#[test]
fn periodic_full_expansion_breaks_unbounded_acyclic_postponement() {
    let p = problem(
        vec![1, 0, 0, 0],
        vec![
            (vec![(0, 1)], vec![(1, 1)]),
            (vec![], vec![(2, 1)]),
            (vec![(1, 1)], vec![(1, 1), (3, 1)]),
            (vec![(2, 100)], vec![(2, 100), (3, 1)]),
        ],
        vec![goal(vec![0, 0, 0, 1], 1, false)],
    );
    let start = Instant::now();
    let deadline = start + Duration::from_secs(2);
    let graph = Graph::new(&p, start, Duration::from_secs(2)).unwrap();
    assert_eq!(
        graph.actions.iter().map(|a| a.original).collect::<Vec<_>>(),
        vec![0, 1, 2, 3]
    );
    let mut index = Stubborn::new(&graph, &p, deadline).unwrap();
    let initial = marking(&p.initial);
    let mut m = graph.fire(&initial, 0).unwrap().unwrap();
    let mut seen = HashSet::from([initial, m.clone()]);
    let mut trace = vec![0];
    for depth in 1..FULL_EXPANSION_PERIOD {
        let selection = index.select(&m, &[1, 2], depth, &seen, deadline).unwrap();
        let Selection::Reduced(successors) = selection else {
            panic!("expected invisible growth");
        };
        assert_eq!(successors.len(), 1);
        let (t, next) = successors.into_iter().next().unwrap();
        assert_eq!(t, 1);
        trace.push(t);
        seen.insert(next.clone());
        m = next;
    }
    assert_full(
        index
            .select(&m, &[1, 2], FULL_EXPANSION_PERIOD, &seen, deadline)
            .unwrap(),
        FullExpansion::Periodic,
    );
    trace.push(2);
    p.check_witness(&trace).unwrap();
    index.full_period = 1;
    for depth in 0..16 {
        assert_full(
            index.select(&m, &[1, 2], depth, &seen, deadline).unwrap(),
            FullExpansion::Periodic,
        );
    }
}

#[test]
fn closure_budget_deadline_and_depth_overflow_never_accept_a_partial_reduction() {
    let p = problem(
        vec![1, 0, 0],
        vec![
            (vec![(0, 1)], vec![(1, 1)]),
            (vec![(0, 1)], vec![(0, 1), (2, 1)]),
        ],
        vec![goal(vec![0, 0, 1], 1, false)],
    );
    let graph = unsliced_graph(&p);
    let deadline = Instant::now() + Duration::from_secs(2);
    let mut index = Stubborn::new(&graph, &p, deadline).unwrap();
    let m = marking(&p.initial);
    let seen = HashSet::from([m.clone()]);
    for budget in 0..5 {
        index.work_limit = budget;
        assert_full(
            index.select(&m, &[0, 1], 1, &seen, deadline).unwrap(),
            FullExpansion::ClosureLimit,
        );
    }
    index.work_limit = CLOSURE_WORK_LIMIT;
    assert_full(
        index.select(&m, &[0, 1], 1, &seen, Instant::now()).unwrap(),
        FullExpansion::ClosureLimit,
    );
    assert!(matches!(
        index.select(&m, &[0, 1], u64::MAX, &seen, deadline),
        Err("discovery depth overflow")
    ));
}

#[test]
fn first_visible_action_is_never_skipped_to_choose_an_invisible_seed() {
    let p = problem(
        vec![0, 0],
        vec![(vec![], vec![(0, 1)]), (vec![], vec![(1, 1)])],
        vec![goal(vec![0, 1], 1, false)],
    );
    let graph = unsliced_graph(&p);
    let deadline = Instant::now() + Duration::from_secs(2);
    let index = Stubborn::new(&graph, &p, deadline).unwrap();
    let m = marking(&p.initial);
    assert_full(
        index
            .select(&m, &[1, 0], 1, &HashSet::from([m.clone()]), deadline)
            .unwrap(),
        FullExpansion::Visible,
    );
}

#[test]
fn bounded_differential_exercises_unrestricted_stubborn_fallback() {
    let mut seed = 681u64;
    for _ in 0..160 {
        let mut next = || {
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            seed >> 32
        };
        let arcs = (0..10)
            .map(|_| {
                let source = next() as usize % 4;
                let destination = next() as usize % 4;
                let weight = next() % 3 + 1;
                (vec![(source, weight)], vec![(destination, weight)])
            })
            .collect();
        let p = problem(
            vec![6, 0, 0, 0],
            arcs,
            vec![goal(
                vec![0, 0, -1, 1],
                next() as i64 % 13 - 6,
                next() % 2 == 0,
            )],
        );
        let baseline = crate::search::solve(&p, false, Duration::from_secs(1), 10_000);
        assert_ne!(baseline.verdict, "unknown");
        for stubborn in [false, true] {
            let out = run(
                &p,
                Duration::from_secs(1),
                10_000,
                false,
                if stubborn {
                    Reduction::Invisible
                } else {
                    Reduction::Off
                },
                false,
            );
            if baseline.verdict == "reachable" {
                assert_eq!(out.verdict, "reachable", "{}", out.reason);
                assert_eq!(p.check_witness(&out.trace).unwrap(), out.marking.unwrap());
            } else {
                assert_eq!(out.verdict, "unknown");
                assert_eq!(out.reason, "search exhausted; no negative certificate");
            }
        }
    }
}

fn target_selection(index: &mut TargetStubborn<'_>, p: &Problem, m: &Marking) -> Vec<usize> {
    let enabled: Vec<_> = index
        .index
        .graph
        .actions
        .iter()
        .enumerate()
        .filter_map(|(t, action)| {
            action
                .guards
                .iter()
                .all(|&g| {
                    let (place, weight) = index.index.graph.facts[g];
                    tokens(m, place) >= weight
                })
                .then_some(t)
        })
        .collect();
    match index.select(p, m, &enabled, Instant::now() + Duration::from_secs(2)) {
        Selection::Full(_) => enabled,
        Selection::TargetReduced(actions) => actions,
        Selection::Reduced(_) => panic!("target-directed selection used visibility provisos"),
    }
}

#[test]
fn target_all_improving_alternatives_are_seeds() {
    let p = problem(
        vec![0, 0, 0],
        vec![
            (vec![], vec![(0, 1)]),
            (vec![], vec![(0, 1), (1, 1)]),
            (vec![], vec![(2, 1)]),
        ],
        vec![goal(vec![1, 0, 0], 1, true), goal(vec![0, 1, 0], 1, true)],
    );
    let graph = unsliced_graph(&p);
    let mut index =
        TargetStubborn::new(&graph, &p, Instant::now() + Duration::from_secs(2)).unwrap();
    assert_eq!(
        target_selection(&mut index, &p, &marking(&p.initial)),
        vec![0, 1]
    );
    let out = run(
        &p,
        Duration::from_secs(2),
        100,
        false,
        Reduction::TargetDirected,
        false,
    );
    assert_eq!(out.verdict, "reachable", "{}", out.reason);
    assert_eq!(out.trace, vec![1]);
    p.check_witness(&out.trace).unwrap();
}

#[test]
fn target_disabled_weighted_seeds_retain_every_necessary_producer() {
    let p = problem(
        vec![1, 0, 0, 0],
        vec![
            (vec![(1, 3)], vec![(2, 1)]),
            (vec![(0, 1)], vec![(0, 1), (1, 2)]),
            (vec![], vec![(1, 1)]),
            (vec![], vec![(3, 1)]),
        ],
        vec![goal(vec![0, 0, 1, 0], 1, true)],
    );
    let graph = unsliced_graph(&p);
    let mut index =
        TargetStubborn::new(&graph, &p, Instant::now() + Duration::from_secs(2)).unwrap();
    assert_eq!(
        target_selection(&mut index, &p, &marking(&p.initial)),
        vec![1, 2]
    );
    assert_eq!(
        target_selection(&mut index, &p, &marking(&[1, 3, 0, 0])),
        vec![0]
    );
    let out = run(
        &p,
        Duration::from_secs(2),
        100,
        false,
        Reduction::TargetDirected,
        false,
    );
    assert_eq!(out.verdict, "reachable", "{}", out.reason);
    assert!(out.trace.len() >= 3);
    p.check_witness(&out.trace).unwrap();
}

#[test]
fn target_symmetric_read_dependencies_allow_seen_no_op_successors() {
    let p = problem(
        vec![1, 0, 0, 0],
        vec![
            (vec![(0, 1)], vec![(0, 1), (1, 1)]),
            (vec![(0, 1)], vec![(2, 1)]),
            (vec![(0, 1)], vec![(0, 1)]),
            (vec![], vec![(3, 1)]),
        ],
        vec![
            goal(vec![0, 0, 1, 0], 1, true),
            goal(vec![0, 1, 0, 0], 1, true),
        ],
    );
    let graph = unsliced_graph(&p);
    let mut index =
        TargetStubborn::new(&graph, &p, Instant::now() + Duration::from_secs(2)).unwrap();
    let m = marking(&p.initial);
    assert_eq!(target_selection(&mut index, &p, &m), vec![0, 1, 2]);
    assert_eq!(graph.fire(&m, 2).unwrap().unwrap(), m);
    assert_eq!(
        reduced_actions(index.select(
            &p,
            &m,
            &[2, 1, 0, 3],
            Instant::now() + Duration::from_secs(2)
        )),
        vec![2, 1, 0]
    );
    let out = run(
        &p,
        Duration::from_secs(2),
        100,
        false,
        Reduction::TargetDirected,
        false,
    );
    assert_eq!(out.verdict, "reachable", "{}", out.reason);
    assert_eq!(out.trace, vec![0, 1]);
    p.check_witness(&out.trace).unwrap();
}

#[test]
fn target_equality_selects_increases_below_and_decreases_above() {
    let p = problem(
        vec![0, 0],
        vec![
            (vec![], vec![(0, 1)]),
            (vec![(0, 1)], vec![]),
            (vec![], vec![(1, 1)]),
        ],
        vec![goal(vec![-1, 0], -2, true)],
    );
    let graph = unsliced_graph(&p);
    let mut index =
        TargetStubborn::new(&graph, &p, Instant::now() + Duration::from_secs(2)).unwrap();
    assert_eq!(target_selection(&mut index, &p, &marking(&[0, 0])), vec![0]);
    assert_eq!(target_selection(&mut index, &p, &marking(&[3, 0])), vec![1]);
    for initial in [vec![0, 0], vec![3, 0]] {
        let mut p = p.clone();
        p.initial = initial;
        let out = run(
            &p,
            Duration::from_secs(2),
            100,
            false,
            Reduction::TargetDirected,
            false,
        );
        assert_eq!(out.verdict, "reachable", "{}", out.reason);
        p.check_witness(&out.trace).unwrap();
    }
}

#[test]
fn target_exact_signs_and_false_conjunct_survive_cancellation_beyond_i128() {
    let max = i64::MAX;
    let weight = u64::MAX;
    let large = vec![(0, weight), (1, weight), (2, weight), (3, weight)];
    let mut increasing = large.clone();
    increasing.push((4, 1));
    let p = problem(
        vec![0; 5],
        vec![
            (vec![], large.clone()),
            (vec![], increasing),
            (vec![(4, 1)], large),
        ],
        vec![goal(vec![max, max, -max, -max, 1], 0, true)],
    );
    let mut graph = unsliced_graph(&p);
    for action in &mut graph.actions {
        action.effects = vec![i128::MIN];
    }
    let mut index =
        TargetStubborn::new(&graph, &p, Instant::now() + Duration::from_secs(2)).unwrap();
    let m = marking(&[weight, weight, weight, weight, 1]);
    assert_eq!(target_selection(&mut index, &p, &m), vec![2]);
    let DirectionCache::Complete(directions) = &index.directions[0] else {
        panic!("incomplete signs");
    };
    assert_eq!(directions.increasing, vec![1]);
    assert_eq!(directions.decreasing, vec![2]);
    let mut cache = DirectionCache::Building(DirectionBuilder::default());
    let mut completed = false;
    for _ in 0..20 {
        let mut work = ClosureWork {
            used: 0,
            limit: 2,
            deadline: Instant::now() + Duration::from_secs(2),
        };
        if let Some(directions) = cache.complete(&graph, &p.target[0].coefficients, &mut work) {
            assert_eq!(directions.increasing, vec![1]);
            assert_eq!(directions.decreasing, vec![2]);
            completed = true;
            break;
        }
    }
    assert!(completed);
    let mut p = p;
    p.target[0].bound = 1;
    let mut index =
        TargetStubborn::new(&graph, &p, Instant::now() + Duration::from_secs(2)).unwrap();
    assert_eq!(
        target_selection(
            &mut index,
            &p,
            &marking(&[weight, weight, weight, weight, 0])
        ),
        vec![1]
    );
}

#[test]
fn target_empty_seeds_and_disabled_closure_return_unknown_without_a_certificate() {
    for arcs in [
        vec![(vec![], vec![(1, 1)])],
        vec![(vec![], vec![(1, 1)]), (vec![(2, 1)], vec![(0, 1)])],
    ] {
        let p = problem(vec![0, 0, 0], arcs, vec![goal(vec![1, 0, 0], 1, false)]);
        let graph = unsliced_graph(&p);
        let mut index =
            TargetStubborn::new(&graph, &p, Instant::now() + Duration::from_secs(2)).unwrap();
        assert!(target_selection(&mut index, &p, &marking(&p.initial)).is_empty());
        let out = run(
            &p,
            Duration::from_secs(2),
            100,
            false,
            Reduction::TargetDirected,
            false,
        );
        assert_eq!(out.verdict, "unknown");
        assert_eq!(out.reason, "search exhausted; no negative certificate");
        assert!(out.certificate.is_none() && out.proof.is_none());
    }
}

#[test]
fn target_partial_sign_indices_seeding_and_closure_fall_back_to_full() {
    let p = problem(
        vec![0, 0, 0],
        vec![
            (vec![], vec![(0, 1)]),
            (vec![], vec![(0, 1), (1, 1)]),
            (vec![], vec![(2, 1)]),
        ],
        vec![goal(vec![1, 0, 0], 1, false)],
    );
    let graph = unsliced_graph(&p);
    let deadline = Instant::now() + Duration::from_secs(2);
    let mut index = TargetStubborn::new(&graph, &p, deadline).unwrap();
    let m = marking(&p.initial);
    for budget in 0..8 {
        index.directions[0] = DirectionCache::Building(DirectionBuilder::default());
        index.index.work_limit = budget;
        assert_full(
            index.select(&p, &m, &[0, 1, 2], deadline),
            FullExpansion::ClosureLimit,
        );
        assert!(matches!(index.directions[0], DirectionCache::Building(_)));
    }
    index.index.work_limit = CLOSURE_WORK_LIMIT;
    assert_eq!(target_selection(&mut index, &p, &m), vec![0, 1]);
    for budget in 0..5 {
        index.index.work_limit = budget;
        assert_full(
            index.select(&p, &m, &[0, 1, 2], deadline),
            FullExpansion::ClosureLimit,
        );
    }
    index.index.work_limit = CLOSURE_WORK_LIMIT;
    assert_full(
        index.select(&p, &m, &[0, 1, 2], Instant::now()),
        FullExpansion::ClosureLimit,
    );
}

#[test]
fn target_selected_counter_overflow_remains_unknown() {
    let p = problem(
        vec![u64::MAX, 0],
        vec![(vec![(0, 1)], vec![(0, 2), (1, 1)])],
        vec![goal(vec![0, 1], 1, true)],
    );
    let out = run(
        &p,
        Duration::from_secs(2),
        100,
        false,
        Reduction::TargetDirected,
        false,
    );
    assert_eq!(out.verdict, "unknown");
    assert_eq!(out.reason, "counter overflow");
}

fn shortest_unsliced(
    p: &Problem,
    target_directed: bool,
    nonempty_reductions: &mut usize,
) -> Option<usize> {
    use std::collections::VecDeque;
    let graph = unsliced_graph(p);
    let deadline = Instant::now() + Duration::from_secs(2);
    let mut index = TargetStubborn::new(&graph, p, deadline).unwrap();
    let mut queue = VecDeque::from([(p.initial.clone(), 0)]);
    let mut seen = HashSet::from([p.initial.clone()]);
    while let Some((m, distance)) = queue.pop_front() {
        if p.accepts(&m).unwrap() {
            return Some(distance);
        }
        let successors: Vec<_> = (0..p.transitions.len())
            .filter_map(|t| p.fire(&m, t).unwrap().map(|next| (t, next)))
            .collect();
        let enabled: Vec<_> = successors.iter().map(|&(t, _)| t).collect();
        let chosen = if target_directed {
            match index.select(p, &marking(&m), &enabled, deadline) {
                Selection::Full(reason) => {
                    assert_eq!(reason, FullExpansion::AllEnabled);
                    enabled
                }
                Selection::TargetReduced(actions) => {
                    *nonempty_reductions += usize::from(!actions.is_empty());
                    actions
                }
                Selection::Reduced(_) => panic!("unexpected invisible reduction"),
            }
        } else {
            enabled
        };
        for (t, next) in successors {
            if chosen.contains(&t) && seen.insert(next.clone()) {
                queue.push_back((next, distance + 1));
            }
        }
        assert!(seen.len() <= 10_000);
    }
    None
}

#[test]
fn target_exhaustive_bounded_unsliced_reachability_and_shortest_distance() {
    let alphabet: Vec<_> = (0..3)
        .flat_map(|from| {
            (0..3)
                .filter(move |&to| to != from)
                .map(move |to| (vec![(from, 1)], vec![(to, 1)]))
        })
        .collect();
    let mut cases = 0;
    let mut nonempty_reductions = 0;
    for mask in 0..64 {
        let arcs: Arcs = alphabet
            .iter()
            .enumerate()
            .filter(|&(i, _)| mask & (1 << i) != 0)
            .map(|(_, arcs)| arcs.clone())
            .collect();
        for a in 0..=2 {
            for b in 0..=2 - a {
                for coefficients in [
                    vec![1, 0, 0],
                    vec![0, 1, 0],
                    vec![0, 0, 1],
                    vec![1, -1, 0],
                    vec![0, 1, -1],
                    vec![-1, 0, 1],
                ] {
                    for bound in -2..=2 {
                        for equality in [false, true] {
                            let p = problem(
                                vec![a, b, 2 - a - b],
                                arcs.clone(),
                                vec![goal(coefficients.clone(), bound, equality)],
                            );
                            let expected = shortest_unsliced(&p, false, &mut 0);
                            let actual = shortest_unsliced(&p, true, &mut nonempty_reductions);
                            assert_eq!(
                                actual, expected,
                                "mask={mask}, initial={:?}, target={:?}",
                                p.initial, p.target
                            );
                            cases += 1;
                        }
                    }
                }
            }
        }
    }
    assert_eq!(cases, 23_040);
    assert!(nonempty_reductions > 0);
}

#[test]
fn target_direction_cache_resumes_many_actions_and_large_single_actions() {
    for large_action in [false, true] {
        let arcs = if large_action {
            vec![
                (vec![], (0..30).map(|place| (place, 1)).collect()),
                (vec![], vec![(31, 1)]),
            ]
        } else {
            (0..30)
                .map(|t| (vec![], vec![(if t == 0 { 0 } else { 1 }, 1)]))
                .collect()
        };
        let mut coefficients = vec![0; 32];
        coefficients[0] = 1;
        let p = problem(vec![0; 32], arcs, vec![goal(coefficients, 1, false)]);
        let graph = unsliced_graph(&p);
        let deadline = Instant::now() + Duration::from_secs(2);
        let mut index = TargetStubborn::new(&graph, &p, deadline).unwrap();
        index.index.work_limit = 12;
        let enabled: Vec<_> = (0..p.transitions.len()).collect();
        let m = marking(&p.initial);
        let mut previous = (0, 0);
        let mut incomplete = 0;
        let mut reduced = false;
        for _ in 0..20 {
            let selection = index.select(&p, &m, &enabled, deadline);
            match &index.directions[0] {
                DirectionCache::Building(builder) => {
                    assert!((builder.action, builder.term) > previous);
                    previous = (builder.action, builder.term);
                    incomplete += 1;
                    assert_full(selection, FullExpansion::ClosureLimit);
                }
                DirectionCache::Complete(directions) => {
                    assert_eq!(directions.increasing, vec![0]);
                    match selection {
                        Selection::TargetReduced(actions) => {
                            assert_eq!(actions, vec![0]);
                            reduced = true;
                            break;
                        }
                        Selection::Full(reason) => assert_eq!(reason, FullExpansion::ClosureLimit),
                        Selection::Reduced(_) => panic!("unexpected invisible reduction"),
                    }
                }
            }
        }
        assert!(incomplete > 0);
        assert!(reduced);
    }
}

#[test]
fn target_weighted_read_nets_preserve_shortest_conjunctive_target_distance() {
    let mut seed = 2197u64;
    let mut nonempty_reductions = 0;
    for _ in 0..240 {
        let mut next = || {
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            seed >> 32
        };
        let mut initial = vec![0; 4];
        for _ in 0..6 {
            initial[next() as usize % 4] += 1;
        }
        let arcs = (0..10)
            .map(|_| {
                let source = next() as usize % 4;
                let destination = next() as usize % 4;
                let weight = next() % 3 + 1;
                let mut pre = vec![(source, weight)];
                let mut post = vec![(destination, weight)];
                if next() % 2 == 0 {
                    let reader = (0..4).find(|&p| p != source && p != destination).unwrap();
                    let guard = next() % 3 + 1;
                    pre.push((reader, guard));
                    post.push((reader, guard));
                }
                (pre, post)
            })
            .collect();
        let target = (0..2)
            .map(|_| {
                let coefficients = (0..4).map(|_| (next() % 3) as i64 - 1).collect();
                goal(coefficients, (next() % 13) as i64 - 6, next() % 2 == 0)
            })
            .collect();
        let p = problem(initial, arcs, target);
        p.validate().unwrap();
        assert_eq!(
            shortest_unsliced(&p, true, &mut nonempty_reductions),
            shortest_unsliced(&p, false, &mut 0),
            "{p:?}"
        );
    }
}

#[test]
fn target_checked_acceptance_overflow_is_unknown() {
    let max = i64::MAX;
    let p = problem(
        vec![u64::MAX; 4],
        vec![],
        vec![goal(vec![max, max, -max, -max], 1, true)],
    );
    let out = run(
        &p,
        Duration::from_secs(2),
        100,
        false,
        Reduction::TargetDirected,
        false,
    );
    assert_eq!(out.verdict, "unknown");
    assert_eq!(out.reason, "target arithmetic overflow");
}

fn reference_target_closure(
    index: &Stubborn<'_>,
    m: &Marking,
    mut selected: Vec<bool>,
) -> Vec<bool> {
    loop {
        let before = selected.clone();
        for (t, &present) in before.iter().enumerate() {
            if !present {
                continue;
            }
            let action = &index.graph.actions[t];
            let deficient = action.guards.iter().find_map(|&guard| {
                let (place, weight) = index.graph.facts[guard];
                (tokens(m, place) < weight).then_some(place)
            });
            if let Some(place) = deficient {
                for &u in &index.producers[place] {
                    selected[u] = true;
                }
            } else {
                for &guard in &action.guards {
                    for &u in &index.consumers[index.graph.facts[guard].0] {
                        selected[u] = true;
                    }
                }
                for &(place, effect) in &action.delta {
                    if effect < 0 {
                        for &u in &index.readers[place] {
                            selected[u] = true;
                        }
                    }
                }
            }
        }
        if before == selected {
            return selected;
        }
    }
}

#[test]
fn target_once_only_closure_matches_reference_for_all_seeds_and_weighted_markings() {
    let p = problem(
        vec![0; 3],
        vec![
            (vec![(0, 2)], vec![(1, 1)]),
            (vec![(0, 1)], vec![(0, 1), (1, 1)]),
            (vec![(1, 1)], vec![(0, 2)]),
            (vec![(0, 2)], vec![(0, 2)]),
            (vec![(0, 1)], vec![(0, 2)]),
            (vec![], vec![(2, 1)]),
        ],
        vec![goal(vec![0, 1, 0], 3, true)],
    );
    let graph = unsliced_graph(&p);
    let deadline = Instant::now() + Duration::from_secs(10);
    let index = Stubborn::new(&graph, &p, deadline).unwrap();
    let mut stats = TargetDiagnostics::default();
    let mut completed = 0;
    let mut early = 0;
    for a in 0..=3 {
        for b in 0..=2 {
            for c in 0..=1 {
                let m = marking(&[a, b, c]);
                let enabled: Vec<_> = (0..graph.actions.len())
                    .filter(|&t| graph.fire(&m, t).unwrap().is_some())
                    .collect();
                for mask in 0..64 {
                    let mut selected: Vec<_> = (0..6).map(|t| mask & (1 << t) != 0).collect();
                    let expected = reference_target_closure(&index, &m, selected.clone());
                    let mut pending: Vec<_> = (0..6).filter(|&t| selected[t]).collect();
                    let mut closure = TargetClosure::new(&index, &enabled, &mut stats);
                    for &t in &pending {
                        closure.select(t);
                    }
                    let mut work = ClosureWork {
                        used: 0,
                        limit: CLOSURE_WORK_LIMIT,
                        deadline,
                    };
                    let result = if closure.remaining == 0 {
                        Err(FullExpansion::AllEnabled)
                    } else {
                        index.close(
                            &m,
                            &mut selected,
                            &mut pending,
                            false,
                            &mut work,
                            Some(&mut closure),
                        )
                    };
                    match result {
                        Ok(()) => {
                            assert_eq!(selected, expected, "marking={m:?}, seeds={mask}");
                            completed += 1;
                        }
                        Err(FullExpansion::AllEnabled) => {
                            assert!(enabled.iter().all(|&t| selected[t] && expected[t]));
                            early += 1;
                        }
                        Err(reason) => panic!("unexpected fallback: {reason:?}"),
                    }
                }
            }
        }
    }
    assert_eq!(completed + early, 1536);
    assert!(completed > 0 && early > 0);
    assert!(stats.target_repeated_lists_avoided > 0);
}

#[test]
fn target_early_full_waits_for_complete_directions_and_counts_only_enabled_seeds() {
    let p = problem(
        vec![0, 0],
        vec![
            (vec![(1, 2)], vec![(0, 1)]),
            (vec![], vec![(0, 1)]),
            (vec![(1, 1)], vec![(1, 2)]),
        ],
        vec![goal(vec![1, 0], 1, false)],
    );
    let graph = unsliced_graph(&p);
    let deadline = Instant::now() + Duration::from_secs(2);
    let mut index = TargetStubborn::new(&graph, &p, deadline).unwrap();
    let m = marking(&p.initial);
    index.index.work_limit = 4;
    assert_full(
        index.select(&p, &m, &[1], deadline),
        FullExpansion::ClosureLimit,
    );
    assert!(matches!(index.directions[0], DirectionCache::Building(_)));
    assert_eq!(index.stats.target_early_all_enabled, 0);
    assert_eq!(index.stats.target_limit_directions, 1);
    let mut work = ClosureWork {
        used: 0,
        limit: CLOSURE_WORK_LIMIT,
        deadline,
    };
    index.directions[0]
        .complete(&graph, &p.target[0].coefficients, &mut work)
        .unwrap();
    index.index.work_limit = 2;
    assert_full(
        index.select(&p, &m, &[1], deadline),
        FullExpansion::ClosureLimit,
    );
    assert_eq!(index.stats.target_limit_seeds, 1);
    index.index.work_limit = 3;
    assert_full(
        index.select(&p, &m, &[1], deadline),
        FullExpansion::AllEnabled,
    );
    assert_eq!(index.stats.target_early_all_enabled, 1);
    assert_eq!(index.stats.target_limit_closure, 0);
}

#[test]
fn target_partial_dependency_list_falls_back_and_next_selection_restarts_lists() {
    let p = problem(
        vec![0; 3],
        vec![
            (vec![(0, 2)], vec![(1, 1)]),
            (vec![], vec![(0, 1)]),
            (vec![], vec![(0, 2)]),
            (vec![], vec![(0, 3)]),
            (vec![], vec![(2, 1)]),
        ],
        vec![goal(vec![0, 1, 0], 1, false)],
    );
    let graph = unsliced_graph(&p);
    let deadline = Instant::now() + Duration::from_secs(2);
    let mut index = TargetStubborn::new(&graph, &p, deadline).unwrap();
    let mut work = ClosureWork {
        used: 0,
        limit: CLOSURE_WORK_LIMIT,
        deadline,
    };
    index.directions[0]
        .complete(&graph, &p.target[0].coefficients, &mut work)
        .unwrap();
    index.index.work_limit = 6;
    assert_full(
        index.select(&p, &marking(&p.initial), &[1, 2, 3, 4], deadline),
        FullExpansion::ClosureLimit,
    );
    assert_eq!(index.stats.target_limit_closure, 1);
    index.index.work_limit = CLOSURE_WORK_LIMIT;
    assert_eq!(
        target_selection(&mut index, &p, &marking(&p.initial)),
        vec![1, 2, 3]
    );
    assert_eq!(
        target_selection(&mut index, &p, &marking(&[2, 0, 0])),
        vec![0]
    );
    assert_eq!(
        target_selection(&mut index, &p, &marking(&p.initial)),
        vec![1, 2, 3]
    );
}

#[test]
fn target_empty_enabled_and_expired_deadline_use_full_fallback() {
    let p = problem(
        vec![0],
        vec![(vec![(0, 1)], vec![(0, 2)])],
        vec![goal(vec![1], 1, false)],
    );
    let graph = unsliced_graph(&p);
    let deadline = Instant::now() + Duration::from_secs(2);
    let mut index = TargetStubborn::new(&graph, &p, deadline).unwrap();
    let m = marking(&p.initial);
    assert_full(
        index.select(&p, &m, &[], deadline),
        FullExpansion::AllEnabled,
    );
    assert_eq!(index.stats.target_early_all_enabled, 1);
    assert_full(
        index.select(&p, &m, &[], Instant::now()),
        FullExpansion::ClosureLimit,
    );
    assert_eq!(index.stats.target_limit_evaluation, 1);
}
