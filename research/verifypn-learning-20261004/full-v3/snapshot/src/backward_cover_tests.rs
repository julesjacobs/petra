use super::*;
use crate::model::{Constraint, Transition as OriginalTransition};

fn work() -> Work {
    Work {
        deadline: Instant::now() + Duration::from_secs(30),
        remaining: 20_000_000,
    }
}

fn problem(pre: [u64; 2], post: [u64; 2]) -> Problem {
    let arcs = |values: [u64; 2]| {
        values
            .into_iter()
            .enumerate()
            .filter(|&(_, n)| n != 0)
            .collect()
    };
    Problem {
        places: vec!["p".into(), "q".into()],
        initial: vec![0, 0],
        transitions: vec![OriginalTransition {
            name: "t".into(),
            pre: arcs(pre),
            post: arcs(post),
        }],
        target: vec![],
    }
}

fn sparse(values: [u64; 2]) -> Marking {
    values
        .into_iter()
        .enumerate()
        .filter(|&(_, n)| n != 0)
        .collect()
}

#[test]
fn repeated_predecessors_match_every_prefix_guard_on_small_weighted_nets() {
    let mut seed = 20261004_u64;
    let mut next = || {
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        seed >> 32
    };
    for _ in 0..128 {
        let p = problem([next() % 4, next() % 4], [next() % 4, next() % 4]);
        let target = [next() % 6, next() % 6];
        let goal = sparse(target);
        let mut index = Index::new(&p, &mut work()).unwrap();
        index.token_bound = None;
        for repeats in 1..=4 {
            let batch = index
                .predecessor_many(&goal, 0, repeats, &mut work())
                .unwrap()
                .unwrap();
            let mut iterative = goal.clone();
            for _ in 0..repeats {
                iterative = index
                    .predecessor(&iterative, 0, &mut work())
                    .unwrap()
                    .unwrap();
            }
            assert_eq!(batch, iterative);
            for a in 0..8 {
                for b in 0..8 {
                    let mut current = Some(vec![a, b]);
                    for _ in 0..repeats {
                        current = current.and_then(|m| p.fire(&m, 0).unwrap());
                    }
                    let reaches = current.is_some_and(|m| m[0] >= target[0] && m[1] >= target[1]);
                    assert_eq!(
                        dominates(&sparse([a, b]), &batch, &mut work()).unwrap(),
                        reaches
                    );
                }
            }
        }
    }
}

#[test]
fn repeated_preimage_keeps_read_guards_and_negative_prefix_hurdles() {
    let p = problem([3, 4], [3, 2]);
    let mut index = Index::new(&p, &mut work()).unwrap();
    index.token_bound = None;
    assert_eq!(
        index
            .predecessor_many(&vec![(1, 1)], 0, 3, &mut work())
            .unwrap(),
        Some(vec![(0, 3), (1, 8)])
    );
    assert!(index.predecessor_many(&vec![], 0, 0, &mut work()).is_err());
}

#[test]
fn repetitions_are_distinct_capped_and_derived_from_positive_effects() {
    let p = problem([2, 1], [4, 2]);
    let index = Index::new(&p, &mut work()).unwrap();
    assert_eq!(
        index
            .repetitions(&vec![(0, 9), (1, 3)], 0, 100, &mut work())
            .unwrap(),
        vec![5, 3]
    );
    assert_eq!(
        index
            .repetitions(&vec![(0, 9), (1, 3)], 0, 3, &mut work())
            .unwrap(),
        vec![3]
    );
    assert!(
        index
            .repetitions(&vec![(0, 9), (1, 3)], 0, 1, &mut work())
            .unwrap()
            .is_empty()
    );
    let p = problem([2, 1], [2, 0]);
    let index = Index::new(&p, &mut work()).unwrap();
    assert!(
        index
            .repetitions(&vec![(0, 9), (1, 3)], 0, 100, &mut work())
            .unwrap()
            .is_empty()
    );
}

#[test]
fn repeated_coordinate_overflow_and_mass_bound_only_skip_the_proposal() {
    let p = problem([u64::MAX, 0], [0, 1]);
    let mut index = Index::new(&p, &mut work()).unwrap();
    index.token_bound = None;
    assert!(
        index
            .predecessor_many(&vec![(1, 2)], 0, 2, &mut work())
            .unwrap()
            .is_none()
    );
    assert_eq!(
        index.predecessor(&vec![(1, 1)], 0, &mut work()).unwrap(),
        Some(vec![(0, u64::MAX)])
    );
    let p = problem([2, 0], [0, 1]);
    let mut index = Index::new(&p, &mut work()).unwrap();
    index.token_bound = Some(3);
    assert!(
        index
            .predecessor_many(&vec![(1, 2)], 0, 2, &mut work())
            .unwrap()
            .is_none()
    );
    assert_eq!(
        index.predecessor(&vec![(1, 2)], 0, &mut work()).unwrap(),
        Some(vec![(0, 2), (1, 1)])
    );
}

#[test]
fn accelerated_witness_is_expanded_and_negative_certificate_keeps_one_step_closure() {
    let mut p = problem([1, 0], [0, 1]);
    p.initial[0] = 1000;
    p.target.push(Constraint {
        coefficients: vec![0, 1],
        bound: 1000,
        equality: false,
    });
    let answer = solve(&p, Duration::from_secs(2), 3);
    assert_eq!(answer.verdict, "reachable", "{}", answer.reason);
    assert_eq!(answer.trace, vec![0; 1000]);
    assert_eq!(p.check_witness(&answer.trace).unwrap(), vec![0, 1000]);

    p.transitions[0].pre = vec![(0, 2)];
    p.transitions[0].post = vec![(0, 2), (1, 1)];
    p.initial = vec![1, 0];
    let answer = solve(&p, Duration::from_secs(2), 10);
    assert_eq!(answer.verdict, "unreachable", "{}", answer.reason);
    verify(
        &p,
        answer.proof.as_ref().unwrap(),
        Instant::now() + Duration::from_secs(2),
    )
    .unwrap();
}

#[test]
fn repeated_operations_obey_work_and_deadline_limits() {
    let p = problem([1, 0], [0, 1]);
    let index = Index::new(&p, &mut work()).unwrap();
    for mut work in [
        Work {
            deadline: Instant::now(),
            remaining: 1000,
        },
        Work {
            deadline: Instant::now() + Duration::from_secs(1),
            remaining: 0,
        },
    ] {
        assert!(
            index
                .predecessor_many(&vec![(1, 3)], 0, 3, &mut work)
                .is_err()
        );
        assert!(index.repetitions(&vec![(1, 3)], 0, 3, &mut work).is_err());
    }
}
