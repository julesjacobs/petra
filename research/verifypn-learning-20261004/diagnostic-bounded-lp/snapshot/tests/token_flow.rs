use num_bigint::BigInt;
use num_traits::Zero;
use std::time::{Duration, Instant};
use vass_reach::{
    control,
    model::{Constraint, Problem, Transition},
    token_flow,
};

fn phase_net() -> Problem {
    Problem {
        places: vec!["before".into(), "after".into(), "x".into(), "y".into()],
        initial: vec![1, 0, 0, 0],
        transitions: vec![
            Transition {
                name: "early".into(),
                pre: vec![(0, 1)],
                post: vec![(0, 1), (2, 1)],
            },
            Transition {
                name: "switch".into(),
                pre: vec![(0, 1)],
                post: vec![(1, 1)],
            },
            Transition {
                name: "late".into(),
                pre: vec![(1, 1), (2, 1)],
                post: vec![(1, 1), (3, 1)],
            },
        ],
        target: vec![Constraint {
            coefficients: vec![0, 1, 0, 0],
            bound: 1,
            equality: true,
        }],
    }
}

fn lift(p: &Problem, controls: &[usize], trace: &[usize]) {
    let graph = control::build(p, controls, 8192).unwrap();
    let e = graph.edges.len();
    let n = p.places.len();
    let mut values = vec![BigInt::zero(); e + n + e * n];
    let mut marking = p.initial.clone();
    let mut q = graph.initial;
    for &t in trace {
        let index = graph
            .edges
            .iter()
            .position(|edge| edge.source == q && edge.transition == t)
            .unwrap();
        let edge = &graph.edges[index];
        values[index] += 1;
        for (i, &m) in marking.iter().enumerate() {
            values[e + n + index * n + i] += m;
        }
        marking = p.fire(&marking, t).unwrap().unwrap();
        q = edge.target;
    }
    for (i, &m) in marking.iter().enumerate() {
        values[e + i] = m.into();
    }
    let system = token_flow::relaxation(p, &graph, q).unwrap();
    assert_eq!(system.variables, values.len());
    for (i, row) in system.rows.iter().enumerate() {
        let lhs: BigInt = row.coefficients.iter().map(|(j, a)| a * &values[*j]).sum();
        assert!(
            lhs >= row.bound,
            "concrete trace rejected by row {i}: {trace:?}"
        );
    }
}

#[test]
fn concrete_runs_satisfy_token_moments_including_stutters_and_empty_runs() {
    let mut p = phase_net();
    p.target.clear();
    lift(&p, &[0, 1], &[]);
    for count in 0..20 {
        let mut trace = vec![0; count];
        lift(&p, &[0, 1], &trace);
        trace.push(1);
        trace.extend(vec![2; count]);
        lift(&p, &[0, 1], &trace);
    }
    p.transitions.push(Transition {
        name: "back".into(),
        pre: vec![(1, 1)],
        post: vec![(0, 1)],
    });
    lift(&p, &[0, 1], &[0, 1, 2, 3, 0, 1, 2, 3]);
}

#[test]
fn reachable_target_cannot_have_a_refutation() {
    let p = phase_net();
    let graph = control::build(&p, &[0, 1], 8192).unwrap();
    let final_mode = graph.modes.iter().position(|&i| i == 1).unwrap();
    let system = token_flow::relaxation(&p, &graph, final_mode).unwrap();
    assert!(
        system
            .refute(Instant::now() + Duration::from_secs(2))
            .is_none()
    );
    lift(&p, &[0, 1], &[0, 0, 1, 2]);
}

#[test]
fn proof_requires_all_terminal_modes_and_original_arcs() {
    let mut p = phase_net();
    p.target.push(Constraint {
        coefficients: vec![0, 0, 1, 1],
        bound: -1,
        equality: true,
    });
    let graph = control::build(&p, &[0, 1], 8192).unwrap();
    let terminals: Vec<_> = (0..graph.modes.len())
        .map(|q| {
            token_flow::relaxation(&p, &graph, q)
                .unwrap()
                .refute(Instant::now() + Duration::from_secs(2))
                .unwrap()
        })
        .collect();
    let proof = serde_json::to_value(token_flow::Certificate {
        kind: "token-moment-v1".into(),
        controls: vec![0, 1],
        terminals,
    })
    .unwrap();
    token_flow::verify_certificate(&p, &proof).unwrap();
    let mut missing = proof.clone();
    missing["terminals"].as_array_mut().unwrap().pop();
    assert!(token_flow::verify_certificate(&p, &missing).is_err());
    let mut wrong = proof.clone();
    wrong["controls"] = serde_json::json!([0]);
    assert!(token_flow::verify_certificate(&p, &wrong).is_err());
    p.target.pop();
    assert!(token_flow::verify_certificate(&p, &proof).is_err());
}

#[test]
fn weighted_read_arcs_are_counted_before_production() {
    let mut p = phase_net();
    p.initial[2] = 5;
    p.transitions[0].pre.push((2, 3));
    p.transitions[0].post.retain(|&(i, _)| i != 2);
    p.transitions[0].post.push((2, 4));
    p.target.clear();
    lift(&p, &[0, 1], &[0, 0, 0, 1, 2, 2]);
}
