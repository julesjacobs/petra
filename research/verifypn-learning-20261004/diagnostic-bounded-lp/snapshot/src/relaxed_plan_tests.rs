use super::*;
use crate::model::{Constraint, Transition};

fn sparse(values: &[u64], retained: &[bool]) -> Marking {
    values
        .iter()
        .enumerate()
        .filter_map(|(place, &count)| (retained[place] && count != 0).then_some((place, count)))
        .collect::<Vec<_>>()
        .into()
}

#[test]
fn zero_cost_actions_match_exact_weighted_successors_after_relevance() {
    let mut seed = 20261004_u64;
    let mut next = || {
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        seed >> 32
    };
    for case in 0..256 {
        let places = 1 + case % 7;
        let p = Problem {
            places: (0..places).map(|place| format!("p{place}")).collect(),
            initial: (0..places).map(|_| next() % 5).collect(),
            transitions: (0..12)
                .map(|t| {
                    let mut arcs = || {
                        (0..places)
                            .filter_map(|place| {
                                let weight = next() % 5;
                                (weight < 3).then_some((place, weight + 1))
                            })
                            .collect()
                    };
                    Transition {
                        name: format!("t{t}"),
                        pre: arcs(),
                        post: arcs(),
                    }
                })
                .collect(),
            target: (0..2)
                .map(|_| Constraint {
                    coefficients: (0..places).map(|_| (next() % 5) as i64 - 2).collect(),
                    bound: (next() % 13) as i64 - 3,
                    equality: next().is_multiple_of(2),
                })
                .collect(),
        };
        p.validate().unwrap();
        let start = Instant::now();
        let timeout = Duration::from_secs(2);
        let graph = Graph::new(&p, start, timeout).unwrap();
        let marking = sparse(&p.initial, &graph.retained_places);
        let plan = graph.plan(&p, &marking, start, timeout).unwrap();
        let exact: Vec<_> = graph
            .actions
            .iter()
            .enumerate()
            .filter_map(|(t, action)| {
                p.transitions[action.original]
                    .pre
                    .iter()
                    .all(|&(place, weight)| p.initial[place] >= weight)
                    .then_some(t)
            })
            .collect();
        assert_eq!(plan.enabled, exact, "case {case}");
        assert!(
            plan.helpful
                .iter()
                .all(|t| plan.enabled.binary_search(t).is_ok())
        );
        for &t in &plan.enabled {
            let expected = p
                .fire(&p.initial, graph.actions[t].original)
                .unwrap()
                .unwrap();
            let actual = graph.fire(&marking, t).unwrap().unwrap();
            assert_eq!(
                actual,
                sparse(&expected, &graph.retained_places),
                "case {case}, action {t}"
            );
        }
    }
}

#[test]
fn source_weighted_read_and_negative_equality_plans_keep_their_scores() {
    let mut p = Problem {
        places: vec!["gate".into(), "goal".into()],
        initial: vec![0, 0],
        transitions: vec![
            Transition {
                name: "supply".into(),
                pre: vec![],
                post: vec![(0, 1)],
            },
            Transition {
                name: "read".into(),
                pre: vec![(0, 3)],
                post: vec![(0, 3), (1, 2)],
            },
            Transition {
                name: "consume".into(),
                pre: vec![(1, 1)],
                post: vec![],
            },
        ],
        target: vec![Constraint {
            coefficients: vec![0, 1],
            bound: 5,
            equality: false,
        }],
    };
    let variants = [
        ([0, 0], 5, false, 6, vec![0], vec![0]),
        ([3, 0], 5, false, 3, vec![0, 1], vec![1]),
        ([3, 5], 0, true, 5, vec![0, 1, 2], vec![2]),
    ];
    for (initial, bound, equality, score, enabled, helpful) in variants {
        p.initial = initial.to_vec();
        p.target[0].bound = bound;
        p.target[0].equality = equality;
        let start = Instant::now();
        let timeout = Duration::from_secs(2);
        let graph = Graph::new(&p, start, timeout).unwrap();
        let plan = graph
            .plan(
                &p,
                &sparse(&p.initial, &graph.retained_places),
                start,
                timeout,
            )
            .unwrap();
        assert_eq!(plan.score, score);
        assert_eq!(plan.enabled, enabled);
        assert_eq!(plan.helpful, helpful);
    }
}
