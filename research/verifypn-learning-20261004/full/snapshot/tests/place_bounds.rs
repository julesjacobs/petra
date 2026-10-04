use num_bigint::BigInt;
use std::{
    collections::BTreeSet,
    time::{Duration, Instant},
};
use vass_reach::{
    model::{Problem, Transition},
    place_bounds::{self, Certificate, Potential},
};

fn problem(initial: Vec<u64>, transitions: Vec<Transition>) -> Problem {
    Problem {
        places: (0..initial.len()).map(|p| format!("p{p}")).collect(),
        initial,
        transitions,
        target: vec![],
    }
}

fn transition(pre: Vec<(usize, u64)>, post: Vec<(usize, u64)>) -> Transition {
    Transition {
        name: "t".into(),
        pre,
        post,
    }
}

fn certificate(weights: Vec<(usize, &str)>) -> Certificate {
    Certificate {
        potentials: vec![Potential {
            weights: weights.into_iter().map(|(p, w)| (p, w.into())).collect(),
        }],
        ..Certificate::default()
    }
}

#[test]
fn rational_nonconservative_potential_bounds_reachable_states() {
    let problem = problem(
        vec![5, 0],
        vec![
            transition(vec![(0, 2)], vec![(1, 3)]),
            transition(vec![(1, 1)], vec![]),
        ],
    );
    let proof = certificate(vec![(0, "3/2"), (1, "1")]);
    let bounds = place_bounds::check(&problem, &proof).unwrap();
    assert_eq!(bounds, vec![Some(5.into()), Some(7.into())]);
    let mut seen = BTreeSet::from([problem.initial.clone()]);
    let mut pending = vec![problem.initial.clone()];
    while let Some(marking) = pending.pop() {
        for (p, value) in marking.iter().enumerate() {
            assert!(BigInt::from(*value) <= *bounds[p].as_ref().unwrap());
        }
        for t in 0..problem.transitions.len() {
            if let Some(next) = problem.fire(&marking, t).unwrap()
                && seen.insert(next.clone())
            {
                pending.push(next);
            }
        }
    }
    assert!(seen.len() > 5);
    let roundtrip: Certificate =
        serde_json::from_str(&serde_json::to_string(&proof).unwrap()).unwrap();
    assert_eq!(place_bounds::check(&problem, &roundtrip).unwrap(), bounds);
}

#[test]
fn arbitrary_precision_bounds_and_tightest_certificate() {
    let problem = problem(vec![0, 2], vec![]);
    let huge = "1000000000000000000000000000000000000000000000000000000000000";
    let mut proof = certificate(vec![(0, "1"), (1, huge)]);
    assert_eq!(
        place_bounds::check(&problem, &proof).unwrap()[0],
        Some(huge.parse::<BigInt>().unwrap() * 2)
    );
    proof.potentials.push(Potential {
        weights: vec![(0, "1/7".into())],
    });
    assert_eq!(
        place_bounds::check(&problem, &proof).unwrap(),
        vec![Some(0.into()), Some(2.into())]
    );
}

#[test]
fn checks_large_arc_weights_without_machine_arithmetic() {
    let problem = problem(
        vec![u64::MAX, 0],
        vec![transition(vec![(0, u64::MAX)], vec![(1, u64::MAX - 1)])],
    );
    let proof = certificate(vec![
        (0, "18446744073709551614/18446744073709551615"),
        (1, "1"),
    ]);
    assert_eq!(
        place_bounds::check(&problem, &proof).unwrap(),
        vec![Some(u64::MAX.into()), Some((u64::MAX - 1).into())]
    );
}

#[test]
fn rejects_forged_potentials_and_invalid_problem() {
    let problem = problem(vec![1, 0], vec![transition(vec![(0, 1)], vec![(1, 2)])]);
    for weights in [
        vec![(0, "-1")],
        vec![(0, "0")],
        vec![(2, "1")],
        vec![(0, "1"), (0, "1")],
        vec![(1, "1"), (0, "1")],
        vec![(0, "1/0")],
        vec![(0, "garbage")],
        vec![],
        vec![(0, "1"), (1, "1")],
    ] {
        assert!(place_bounds::check(&problem, &certificate(weights)).is_err());
    }
    let mut proof = certificate(vec![(0, "2"), (1, "1")]);
    proof.kind = "forged".into();
    assert!(place_bounds::check(&problem, &proof).is_err());
    let mut invalid = problem;
    invalid.initial.pop();
    assert!(place_bounds::check(&invalid, &Certificate::default()).is_err());
}

#[test]
fn discovery_reuses_potential_and_leaves_unbounded_place_unknown() {
    let problem = problem(
        vec![3, 0, 0],
        vec![
            transition(vec![(0, 1)], vec![(1, 2)]),
            transition(vec![(1, 2)], vec![(0, 1)]),
            transition(vec![], vec![(2, 1)]),
        ],
    );
    let proof = place_bounds::discover(&problem, Instant::now() + Duration::from_secs(2));
    assert_eq!(proof.potentials.len(), 1);
    assert_eq!(
        place_bounds::check(&problem, &proof).unwrap(),
        vec![Some(3.into()), Some(6.into()), None]
    );
    let expired = place_bounds::discover(&problem, Instant::now());
    assert_eq!(
        place_bounds::check(&problem, &expired).unwrap(),
        vec![None; 3]
    );
}
