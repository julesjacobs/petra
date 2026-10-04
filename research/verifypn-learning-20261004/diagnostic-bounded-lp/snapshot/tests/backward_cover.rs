use serde_json::json;
use std::time::{Duration, Instant};
use vass_reach::{
    backward_cover,
    model::{Constraint, Problem, Transition},
    search,
};

fn transition(pre: &[(usize, u64)], post: &[(usize, u64)]) -> Transition {
    Transition {
        name: "t".into(),
        pre: pre.to_vec(),
        post: post.to_vec(),
    }
}

fn problem(initial: Vec<u64>, transitions: Vec<Transition>, target: Vec<Constraint>) -> Problem {
    Problem {
        places: (0..initial.len()).map(|i| format!("p{i}")).collect(),
        initial,
        transitions,
        target,
    }
}

fn lower(place: usize, bound: i64, dimension: usize) -> Constraint {
    let mut coefficients = vec![0; dimension];
    coefficients[place] = 1;
    Constraint {
        coefficients,
        bound,
        equality: false,
    }
}

#[test]
fn complete_for_lower_bound_conjunctions_on_small_weighted_conservative_nets() {
    let mut seed = 41u64;
    let mut next = || {
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        seed >> 32
    };
    for case in 0..128 {
        let dimension = 2 + case % 3;
        let mut initial = vec![0; dimension];
        for _ in 0..4 {
            initial[next() as usize % dimension] += 1;
        }
        let mut transitions = Vec::new();
        for _ in 0..8 {
            let mass = next() % 4;
            let mut arcs = || {
                let mut counts = vec![0; dimension];
                for _ in 0..mass {
                    counts[next() as usize % dimension] += 1;
                }
                counts
                    .into_iter()
                    .enumerate()
                    .filter(|&(_, n)| n > 0)
                    .collect()
            };
            transitions.push(Transition {
                name: "t".into(),
                pre: arcs(),
                post: arcs(),
            });
        }
        for bound in 1..=5 {
            let p = problem(
                initial.clone(),
                transitions.clone(),
                vec![lower(0, bound, dimension), lower(1, 1, dimension)],
            );
            let expected = search::solve(&p, false, Duration::from_secs(2), 10_000);
            let answer = backward_cover::solve(&p, Duration::from_secs(2), 10_000);
            assert_eq!(
                answer.verdict, expected.verdict,
                "case {case}, bound {bound}: {}",
                answer.reason
            );
            if answer.verdict == "reachable" {
                assert_eq!(
                    p.check_witness(&answer.trace).unwrap(),
                    answer.marking.unwrap()
                );
            } else {
                backward_cover::verify(
                    &p,
                    answer.proof.as_ref().unwrap(),
                    Instant::now() + Duration::from_secs(2),
                )
                .unwrap();
            }
        }
    }
}

#[test]
fn read_guards_remain_in_predecessors() {
    let mut p = problem(
        vec![1, 0],
        vec![transition(&[(0, 2)], &[(0, 2), (1, 1)])],
        vec![lower(1, 1, 2)],
    );
    let answer = backward_cover::solve(&p, Duration::from_secs(2), 1000);
    assert_eq!(answer.verdict, "unreachable", "{}", answer.reason);
    backward_cover::verify(
        &p,
        answer.proof.as_ref().unwrap(),
        Instant::now() + Duration::from_secs(2),
    )
    .unwrap();
    p.initial[0] = 2;
    let answer = backward_cover::solve(&p, Duration::from_secs(2), 1000);
    assert_eq!(answer.verdict, "reachable");
    assert_eq!(answer.trace, vec![0]);
}

#[test]
fn necessary_target_witness_must_satisfy_all_original_rows() {
    let p = problem(
        vec![0, 1],
        vec![transition(&[], &[(0, 1)])],
        vec![Constraint {
            coefficients: vec![1, -1],
            bound: 1,
            equality: false,
        }],
    );
    let answer = backward_cover::solve(&p, Duration::from_secs(2), 1000);
    assert_eq!(answer.verdict, "unknown");
    assert!(answer.proof.is_none());
}

#[test]
fn rejects_false_and_malformed_closures() {
    let p = problem(
        vec![1, 0],
        vec![transition(&[], &[(1, 1)])],
        vec![lower(0, 2, 2)],
    );
    let valid = json!({"kind":"backward-cover-v1", "requirements":[{"target_row":0,"sign":1,"place":0,"required":2}], "basis":[[[0,2]]]});
    let verify = |p: &Problem, proof: &serde_json::Value| {
        backward_cover::verify(p, proof, Instant::now() + Duration::from_secs(2))
    };
    verify(&p, &valid).unwrap();
    let mut wrong = valid.clone();
    wrong["basis"] = json!([]);
    assert!(verify(&p, &wrong).is_err());
    let mut wrong = valid.clone();
    wrong["basis"] = json!([[[0, 1]]]);
    assert!(verify(&p, &wrong).is_err());
    let mut wrong = valid.clone();
    wrong["requirements"][0]["required"] = json!(3);
    assert!(verify(&p, &wrong).is_err());
    let mut wrong = valid.clone();
    wrong["requirements"][0]["sign"] = json!(-1);
    assert!(verify(&p, &wrong).is_err());
    let mut wrong = valid.clone();
    wrong["basis"] = json!([[[0, 2], [0, 3]]]);
    assert!(verify(&p, &wrong).is_err());
    let mut open = p;
    open.transitions.push(transition(&[(1, 1)], &[(0, 1)]));
    assert!(verify(&open, &valid).is_err());
}

#[test]
fn total_token_bound_and_large_weights_are_checked() {
    let p = problem(
        vec![1],
        vec![transition(&[(0, 1)], &[(0, 1)])],
        vec![lower(0, 2, 1)],
    );
    let answer = backward_cover::solve(&p, Duration::from_secs(1), 1000);
    assert_eq!(answer.verdict, "unreachable");
    assert_eq!(answer.proof.as_ref().unwrap()["basis"], json!([]));
    let p = problem(
        vec![u64::MAX, 0],
        vec![transition(&[(0, u64::MAX)], &[(1, u64::MAX)])],
        vec![lower(1, i64::MAX, 2)],
    );
    let answer = backward_cover::solve(&p, Duration::from_secs(1), 1000);
    assert_eq!(answer.verdict, "reachable", "{}", answer.reason);
    assert_eq!(answer.trace, vec![0]);
}
