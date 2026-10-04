use super::*;
use crate::model::{Constraint, Transition};

fn deadline() -> Instant {
    Instant::now() + Duration::from_secs(10)
}

fn problem(initial: Vec<u64>, transitions: Vec<Transition>) -> Problem {
    Problem {
        places: (0..initial.len()).map(|i| format!("p{i}")).collect(),
        initial,
        transitions,
        target: vec![],
    }
}

fn transition(pre: &[(usize, u64)], post: &[(usize, u64)]) -> Transition {
    Transition {
        name: "t".into(),
        pre: pre.to_vec(),
        post: post.to_vec(),
    }
}

fn trace(result: Realization) -> Vec<usize> {
    match result {
        Realization::Witness(trace) => trace,
        _ => panic!("expected a realized count vector"),
    }
}

#[test]
fn weighted_blocks_follow_dependencies_and_keep_firing_accounting() {
    let mut p = problem(
        vec![4, 0, 0],
        vec![
            transition(&[(1, 2)], &[(2, 1)]),
            transition(&[(0, 2)], &[(1, 3)]),
        ],
    );
    p.target.push(Constraint {
        coefficients: vec![0, 0, 1],
        bound: 3,
        equality: true,
    });
    let order = acyclic_order(&p, deadline()).unwrap();
    let mut states = 2;
    let result = realize_acyclic(&p, &[3, 2], &order, deadline(), 8, &mut states).unwrap();
    let witness = trace(result);
    assert_eq!(witness, vec![1, 1, 0, 0, 0]);
    assert_eq!(states, 7);
    assert_eq!(p.check_witness(&witness).unwrap(), vec![0, 0, 3]);
}

#[test]
fn sources_sinks_shared_resources_and_zero_counts_are_exact() {
    let p = problem(
        vec![0, 0, 0],
        vec![
            transition(&[(0, 2)], &[(1, 1)]),
            transition(&[(0, 4)], &[(2, 1)]),
            transition(&[], &[(0, 2)]),
            transition(&[(2, 1)], &[]),
        ],
    );
    let order = acyclic_order(&p, deadline()).unwrap();
    let mut states = 0;
    let result = realize_acyclic(&p, &[2, 1, 4, 0], &order, deadline(), 8, &mut states).unwrap();
    assert_eq!(p.check_witness(&trace(result)).unwrap(), vec![0, 2, 1]);
    assert_eq!(states, 7);
}

#[test]
fn read_arcs_and_cycles_use_the_existing_realizer() {
    for (p, counts, expected) in [
        (
            problem(vec![3], vec![transition(&[(0, 2)], &[(0, 1)])]),
            vec![2],
            vec![1],
        ),
        (
            problem(
                vec![1, 0],
                vec![
                    transition(&[(0, 1)], &[(1, 1)]),
                    transition(&[(1, 1)], &[(0, 1)]),
                ],
            ),
            vec![2, 2],
            vec![1, 0],
        ),
        (
            problem(vec![1], vec![transition(&[(0, 1)], &[(0, 1)])]),
            vec![0],
            vec![1],
        ),
    ] {
        assert!(acyclic_order(&p, deadline()).is_none());
        let mut states = 0;
        let witness = trace(realize(&p, &counts, deadline(), 10, &mut states));
        assert_eq!(p.check_witness(&witness).unwrap(), expected);
    }
}

#[test]
fn topological_overflow_falls_back_to_a_representable_order() {
    let p = problem(
        vec![u64::MAX],
        vec![transition(&[(0, 1)], &[]), transition(&[], &[(0, 1)])],
    );
    let order = acyclic_order(&p, deadline()).unwrap();
    let mut states = 0;
    assert!(realize_acyclic(&p, &[1, 1], &order, deadline(), 3, &mut states).is_none());
    assert_eq!(states, 0);
    let witness = trace(realize(&p, &[1, 1], deadline(), 3, &mut states));
    assert_eq!(witness, vec![0, 1]);
    assert_eq!(p.check_witness(&witness).unwrap(), vec![u64::MAX]);
}

#[test]
fn disabled_blocks_do_not_accept_infeasible_counts() {
    let p = problem(vec![1, 0], vec![transition(&[(0, 2)], &[(1, 1)])]);
    let order = acyclic_order(&p, deadline()).unwrap();
    let mut states = 0;
    assert!(realize_acyclic(&p, &[1], &order, deadline(), 2, &mut states).is_none());
    assert_eq!(states, 0);
    assert!(matches!(
        realize(&p, &[1], deadline(), 2, &mut states),
        Realization::Impossible
    ));
}

#[test]
fn state_budget_boundary_matches_expanded_realization() {
    let p = problem(vec![4, 0], vec![transition(&[(0, 1)], &[(1, 1)])]);
    let order = acyclic_order(&p, deadline()).unwrap();
    let mut states = 3;
    assert!(realize_acyclic(&p, &[4], &order, deadline(), 7, &mut states).is_none());
    assert_eq!(states, 3);
    assert!(matches!(
        realize(&p, &[4], deadline(), 7, &mut states),
        Realization::Limited
    ));
    assert_eq!(states, 7);
    states = 3;
    let result = realize_acyclic(&p, &[4], &order, deadline(), 8, &mut states).unwrap();
    assert_eq!(trace(result).len(), 4);
    assert_eq!(states, 7);
}

#[test]
fn empty_net_neutral_sources_and_resource_limits_are_handled() {
    for (p, counts) in [
        (problem(vec![], vec![]), vec![]),
        (problem(vec![], vec![transition(&[], &[])]), vec![3]),
    ] {
        let order = acyclic_order(&p, deadline()).unwrap();
        let mut states = 0;
        let result = realize_acyclic(&p, &counts, &order, deadline(), 4, &mut states).unwrap();
        let witness = trace(result);
        assert_eq!(states, witness.len());
        assert_eq!(p.check_witness(&witness).unwrap(), Vec::<u64>::new());
        assert!(matches!(
            realize_acyclic(&p, &counts, &order, deadline(), 0, &mut states),
            Some(Realization::Limited)
        ));
        assert!(matches!(
            realize_acyclic(&p, &counts, &order, Instant::now(), 4, &mut states),
            Some(Realization::Limited)
        ));
        assert!(acyclic_order(&p, Instant::now()).is_none());
    }
    let p = problem(vec![], vec![transition(&[], &[]), transition(&[], &[])]);
    let order = acyclic_order(&p, deadline()).unwrap();
    let mut states = 0;
    assert!(
        realize_acyclic(
            &p,
            &[u64::MAX, u64::MAX],
            &order,
            deadline(),
            usize::MAX,
            &mut states
        )
        .is_none()
    );
    assert_eq!(states, 0);
    let p = problem(vec![0; MAX_DENSE_ENTRIES / 3 + 1], vec![]);
    assert!(acyclic_order(&p, deadline()).is_none());
}

#[test]
fn weighted_acyclic_counts_agree_with_nonnegative_state_equation() {
    let mut seed = 20261004u64;
    let mut next = || {
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        seed >> 32
    };
    for _ in 0..400 {
        let initial = next() % 7;
        let input = 1 + next() % 3;
        let middle = next() % 4;
        let consumed = 1 + next() % 3;
        let counts = [next() % 4, next() % 4];
        let p = problem(
            vec![initial, 0, 0],
            vec![
                transition(&[(1, consumed)], &[(2, 1)]),
                transition(
                    &[(0, input)],
                    &if middle == 0 {
                        vec![]
                    } else {
                        vec![(1, middle)]
                    },
                ),
            ],
        );
        let order = acyclic_order(&p, deadline()).unwrap();
        let expected = endpoint(&p, &counts);
        let mut states = 0;
        let result = realize_acyclic(&p, &counts, &order, deadline(), 10, &mut states);
        if let Some(expected) = expected {
            let witness = trace(result.unwrap());
            assert_eq!(p.check_witness(&witness).unwrap(), expected);
            let mut actual = [0u64; 2];
            for &t in &witness {
                actual[t] += 1;
            }
            assert_eq!(actual, counts);
            assert_eq!(states, witness.len());
        } else {
            assert!(result.is_none());
            assert_eq!(states, 0);
        }
    }
}

#[test]
fn sparse_solver_returns_the_existing_replayed_witness_format() {
    let mut p = problem(
        vec![128, 0, 0],
        vec![
            transition(&[(1, 1)], &[(2, 1)]),
            transition(&[(0, 1)], &[(1, 1)]),
        ],
    );
    p.target.push(Constraint {
        coefficients: vec![0, 0, 1],
        bound: 128,
        equality: true,
    });
    let outcome = solve_sparse_with_cap(&p, Duration::from_secs(10), 257, 256);
    assert_eq!(outcome.verdict, "reachable", "{}", outcome.reason);
    assert_eq!(outcome.trace.len(), 256);
    assert_eq!(outcome.states, 256);
    assert!(outcome.proof.is_none());
    assert_eq!(p.check_witness(&outcome.trace).unwrap(), vec![0, 0, 128]);
}
