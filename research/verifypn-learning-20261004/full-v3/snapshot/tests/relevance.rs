use serde_json::json;
use std::{
    collections::{HashSet, VecDeque},
    time::{Duration, Instant},
};
use vass_reach::{
    model::{Constraint, Problem, Transition},
    relevance,
};

fn deadline() -> Instant {
    Instant::now() + Duration::from_secs(10)
}
const WORK: usize = 1_000_000;
type ArcPair = (Vec<(usize, u64)>, Vec<(usize, u64)>);
fn net(
    initial: &[u64],
    arcs: &[ArcPair],
    coefficients: &[i64],
    bound: i64,
    equality: bool,
) -> Problem {
    Problem {
        places: (0..initial.len()).map(|i| format!("p{i}")).collect(),
        initial: initial.to_vec(),
        transitions: arcs
            .iter()
            .enumerate()
            .map(|(i, (pre, post))| Transition {
                name: format!("t{i}"),
                pre: pre.clone(),
                post: post.clone(),
            })
            .collect(),
        target: vec![Constraint {
            coefficients: coefficients.to_vec(),
            bound,
            equality,
        }],
    }
}
fn closure(p: &Problem) -> bool {
    let mut seen = HashSet::from([p.initial.clone()]);
    let mut queue = VecDeque::from([p.initial.clone()]);
    while let Some(marking) = queue.pop_front() {
        if p.accepts(&marking).unwrap() {
            return true;
        }
        for t in 0..p.transitions.len() {
            if let Some(next) = p.fire(&marking, t).unwrap()
                && seen.insert(next.clone())
            {
                queue.push_back(next);
            }
        }
        assert!(seen.len() < 10000);
    }
    false
}

#[test]
fn weighted_read_dependencies_and_original_witness_mapping() {
    let p = net(
        &[0, 1, 0, 0, 29],
        &[
            (vec![], vec![(4, 1)]),
            (vec![(1, 1)], vec![(1, 1), (2, 2)]),
            (vec![(2, 5)], vec![(3, 1), (2, 5), (4, 7)]),
        ],
        &[0, 0, 0, 1, 0],
        1,
        true,
    );
    let q = relevance::prepare(&p, deadline(), WORK).unwrap();
    assert_eq!(q.places, vec![1, 2, 3]);
    assert_eq!(q.transitions, vec![1, 2]);
    assert_eq!(q.problem.transitions[1].pre, vec![(1, 5)]);
    assert_eq!(q.problem.transitions[1].post, vec![(2, 1), (1, 5)]);
    let (trace, marking) = q.lift_witness(&p, &[0, 0, 0, 1], deadline(), WORK).unwrap();
    assert_eq!(trace, vec![1, 1, 1, 2]);
    assert_eq!(marking, vec![0, 1, 6, 1, 36]);
    assert_eq!(p.check_witness(&trace).unwrap(), marking);
    let proof = q
        .wrap_proof(json!({"kind":"test-inner"}), deadline(), WORK)
        .unwrap();
    let (checked, inner) = relevance::verify_reduction(&p, &proof, deadline(), WORK).unwrap();
    assert_eq!(
        serde_json::to_value(&q.problem).unwrap(),
        serde_json::to_value(checked.problem).unwrap()
    );
    assert_eq!(inner, &json!({"kind":"test-inner"}));
}

#[test]
fn signed_target_cleanup_and_discarded_consumers() {
    let p = net(
        &[2, 0, 0],
        &[
            (vec![(0, 1)], vec![(2, 1)]),
            (vec![(0, 2)], vec![(0, 2), (1, 1)]),
        ],
        &[0, 1, 0],
        2,
        true,
    );
    let q = relevance::prepare(&p, deadline(), WORK).unwrap();
    assert_eq!(q.places, vec![0, 1]);
    assert_eq!(q.transitions, vec![1]);
    assert_eq!(
        q.lift_witness(&p, &[0, 0], deadline(), WORK).unwrap().0,
        vec![1, 1]
    );
    let p = net(&[2, 0], &[(vec![(0, 1)], vec![(1, 1)])], &[-1, 1], 2, true);
    let q = relevance::prepare(&p, deadline(), WORK).unwrap();
    assert_eq!(q.transitions, vec![0]);
    q.lift_witness(&p, &[0, 0], deadline(), WORK).unwrap();
}

#[test]
fn forged_mappings_reject_every_failed_obligation() {
    let p = net(
        &[1, 0, 0],
        &[
            (vec![(0, 1)], vec![(0, 1), (1, 1)]),
            (vec![], vec![(0, 1)]),
            (vec![(1, 1)], vec![]),
        ],
        &[0, 1, 0],
        2,
        true,
    );
    let good = relevance::prepare(&p, deadline(), WORK)
        .unwrap()
        .wrap_proof(json!({}), deadline(), WORK)
        .unwrap();
    for (key, value) in [
        ("places", json!([0])),
        ("places", json!([1])),
        ("places", json!([0, 1, 1])),
        ("places", json!([1, 0])),
        ("places", json!([0, 1, 3])),
        ("transitions", json!([0, 2])),
        ("transitions", json!([0, 1])),
        ("transitions", json!([0, 1, 2, 2])),
        ("transitions", json!([2, 1, 0])),
        ("transitions", json!([0, 1, 9])),
        ("transitions", json!([-1])),
        ("kind", json!("other")),
    ] {
        let mut proof = good.clone();
        proof[key] = value;
        assert!(
            relevance::verify_reduction(&p, &proof, deadline(), WORK).is_err(),
            "accepted {proof}"
        );
    }
    let mut missing = good;
    missing.as_object_mut().unwrap().remove("inner");
    assert!(relevance::verify_reduction(&p, &missing, deadline(), WORK).is_err());
}

#[test]
fn constant_and_empty_targets_keep_no_dynamics() {
    for (bound, equality) in [(0, true), (1, true), (-1, false), (1, false)] {
        let p = net(&[1], &[(vec![], vec![(0, 1)])], &[0], bound, equality);
        let q = relevance::prepare(&p, deadline(), WORK).unwrap();
        assert!(q.places.is_empty() && q.transitions.is_empty());
        assert_eq!(
            p.accepts(&p.initial).unwrap(),
            q.problem.accepts(&[]).unwrap()
        );
        let proof = q.wrap_proof(json!({}), deadline(), WORK).unwrap();
        relevance::verify_reduction(&p, &proof, deadline(), WORK).unwrap();
    }
    let mut p = net(&[1], &[], &[0], 1, true);
    p.target.clear();
    let q = relevance::prepare(&p, deadline(), WORK).unwrap();
    assert!(q.problem.target.is_empty());
    q.lift_witness(&p, &[], deadline(), WORK).unwrap();
}

#[test]
fn resource_limits_invalid_inputs_and_forged_traces_fail() {
    let p = net(&[1, 0], &[(vec![(0, 1)], vec![(1, 1)])], &[0, 1], 1, true);
    assert!(relevance::prepare(&p, Instant::now(), WORK).is_err());
    assert!(relevance::prepare(&p, deadline(), 0).is_err());
    let q = relevance::prepare(&p, deadline(), WORK).unwrap();
    assert!(q.lift_witness(&p, &[2], deadline(), WORK).is_err());
    assert!(q.lift_witness(&p, &[0, 0], deadline(), WORK).is_err());
    assert!(q.lift_witness(&p, &[], deadline(), WORK).is_err());
    assert!(q.lift_witness(&p, &[0], deadline(), 0).is_err());
    assert!(q.wrap_proof(json!({}), deadline(), 0).is_err());
    let proof = q.wrap_proof(json!({}), deadline(), WORK).unwrap();
    assert!(relevance::verify_reduction(&p, &proof, deadline(), 0).is_err());
    let overflow = net(
        &[0, u64::MAX],
        &[(vec![], vec![(0, 1), (1, 1)])],
        &[1, 0],
        1,
        true,
    );
    let projected = relevance::prepare(&overflow, deadline(), WORK).unwrap();
    assert!(projected.problem.check_witness(&[0]).is_ok());
    assert!(
        projected
            .lift_witness(&overflow, &[0], deadline(), WORK)
            .is_err()
    );
    let mut bad = p.clone();
    bad.transitions[0].pre.push((0, 1));
    assert!(relevance::prepare(&bad, deadline(), WORK).is_err());
    let mut bad = p;
    bad.transitions[0].post[0].0 = 2;
    assert!(relevance::prepare(&bad, deadline(), WORK).is_err());
}

#[test]
fn exhaustive_bounded_nets_preserve_signed_and_equality_reachability() {
    let choices: Vec<_> = (0..3)
        .flat_map(|from| (0..3).map(move |to| (vec![(from, 1)], vec![(to, 1)])))
        .collect();
    for mask in 0..512usize {
        let arcs: Vec<_> = choices
            .iter()
            .enumerate()
            .filter(|(i, _)| mask & (1 << i) != 0)
            .map(|(_, arc)| arc.clone())
            .collect();
        for (coefficients, bound, equality) in [
            ([0, 1, 0], 1, false),
            ([1, -1, 0], 0, true),
            ([0, -1, 0], -2, true),
            ([0, 0, 1], 0, true),
        ] {
            let p = net(&[2, 0, 0], &arcs, &coefficients, bound, equality);
            let q = relevance::prepare(&p, deadline(), WORK).unwrap();
            assert_eq!(
                closure(&p),
                closure(&q.problem),
                "mask {mask}, target {coefficients:?}"
            );
            let proof = q.wrap_proof(json!({}), deadline(), WORK).unwrap();
            relevance::verify_reduction(&p, &proof, deadline(), WORK).unwrap();
        }
    }
}
