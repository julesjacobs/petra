use num_bigint::BigInt;
use num_rational::BigRational as Q;
use num_traits::{Signed, Zero};
use std::time::{Duration, Instant};
use vass_reach::{
    control::{self, Control},
    linear::{Row, System},
    model::{Constraint, Problem, Transition},
    token_cut::{self, Cut, Separation},
    token_flow,
};

fn deadline() -> Instant {
    Instant::now() + Duration::from_secs(5)
}

fn phase_net() -> Problem {
    Problem {
        places: ["before", "after", "x", "y"].map(String::from).to_vec(),
        initial: vec![1, 0, 0, 0],
        transitions: vec![
            Transition {
                name: "consume_early".into(),
                pre: vec![(0, 1), (2, 1)],
                post: vec![(0, 1), (3, 1)],
            },
            Transition {
                name: "switch".into(),
                pre: vec![(0, 1)],
                post: vec![(1, 1)],
            },
            Transition {
                name: "produce_late".into(),
                pre: vec![(1, 1)],
                post: vec![(1, 1), (2, 1)],
            },
        ],
        target: vec![],
    }
}

fn row_holds(row: &Row, values: &[Q]) -> bool {
    let lhs: Q = row.coefficients.iter().map(|(i, a)| &values[*i] * a).sum();
    lhs >= Q::from_integer(row.bound.clone())
}

fn system_holds(system: &System, values: &[Q]) -> bool {
    system.variables == values.len()
        && values.iter().all(|v| !v.is_negative())
        && system.rows.iter().all(|row| row_holds(row, values))
}

fn fix_prefix(system: &mut System, values: &[Q]) {
    for (i, value) in values.iter().enumerate() {
        system.rows.push(Row {
            coefficients: vec![(i, value.denom().clone())],
            bound: value.numer().clone(),
        });
        system.rows.push(Row {
            coefficients: vec![(i, -value.denom())],
            bound: -value.numer(),
        });
    }
}

fn candidate(p: &Problem, graph: &Control, counts: &[Q]) -> Vec<Q> {
    assert_eq!(graph.edges.len(), counts.len());
    let mut final_marking: Vec<_> = p
        .initial
        .iter()
        .map(|&n| Q::from_integer(n.into()))
        .collect();
    for (edge, count) in graph.edges.iter().zip(counts) {
        for &(i, weight) in &p.transitions[edge.transition].pre {
            final_marking[i] -= count * BigInt::from(weight);
        }
        for &(i, weight) in &p.transitions[edge.transition].post {
            final_marking[i] += count * BigInt::from(weight);
        }
    }
    counts.iter().cloned().chain(final_marking).collect()
}

fn walks(p: &Problem, graph: &Control, depth: usize) -> Vec<(usize, Vec<Q>)> {
    let mut pending = vec![(
        graph.initial,
        p.initial.clone(),
        vec![Q::zero(); graph.edges.len()],
        0,
    )];
    let mut runs = vec![];
    while let Some((q, marking, counts, length)) = pending.pop() {
        let values: Vec<_> = counts
            .iter()
            .cloned()
            .chain(marking.iter().map(|&m| Q::from_integer(m.into())))
            .collect();
        assert!(system_holds(
            &token_cut::master(p, graph, q).unwrap(),
            &values
        ));
        for i in 0..p.places.len() {
            assert!(
                matches!(
                    token_cut::separate_place(p, graph, q, i, &values, deadline()),
                    Separation::Feasible
                ),
                "concrete execution rejected at place {i}, mode {q}, values {values:?}"
            );
        }
        runs.push((q, values));
        if length == depth {
            continue;
        }
        for (e, edge) in graph
            .edges
            .iter()
            .enumerate()
            .filter(|(_, edge)| edge.source == q)
        {
            if let Some(next) = p.fire(&marking, edge.transition).unwrap() {
                let mut next_counts = counts.clone();
                next_counts[e] += Q::from_integer(1.into());
                pending.push((edge.target, next, next_counts, length + 1));
            }
        }
    }
    runs
}

fn differential(
    p: &Problem,
    graph: &Control,
    q: usize,
    values: &[Q],
    runs: &[(usize, Vec<Q>)],
) -> bool {
    assert!(system_holds(
        &token_cut::master(p, graph, q).unwrap(),
        values
    ));
    let mut all_feasible = true;
    for i in 0..p.places.len() {
        match token_cut::separate_place(p, graph, q, i, values, deadline()) {
            Separation::Feasible => {}
            Separation::Unknown => panic!("unexpected flow timeout or invalid point"),
            Separation::Cut(cut) => {
                all_feasible = false;
                let row = token_cut::cut_row(p, graph, q, &cut).unwrap();
                assert!(!row_holds(&row, values));
                for (_, run) in runs.iter().filter(|(terminal, _)| *terminal == q) {
                    assert!(row_holds(&row, run), "cut excludes concrete execution");
                }
            }
        }
    }
    let mut reference = token_flow::relaxation(p, graph, q).unwrap();
    fix_prefix(&mut reference, values);
    if all_feasible {
        let model = reference
            .rational_model(deadline())
            .expect("feasible flow has no exact reference model");
        assert!(system_holds(&reference, &model));
        assert_eq!(&model[..values.len()], values);
    } else {
        let proof = reference
            .refute(deadline())
            .expect("violated flow cut has no exact reference refutation");
        reference.check(&proof).unwrap();
    }
    all_feasible
}

#[test]
fn rational_flow_separation_matches_fixed_count_reference_moments() {
    let p = phase_net();
    let graph = control::build(&p, &[0, 1], 100).unwrap();
    let runs = walks(&p, &graph, 5);
    let mut feasible = 0;
    let mut refuted = 0;
    for early in 0..5 {
        for late in early..5 {
            let counts: Vec<_> = graph
                .edges
                .iter()
                .map(|edge| match edge.transition {
                    0 => Q::new(early.into(), 2.into()),
                    1 => Q::from_integer(1.into()),
                    2 => Q::new(late.into(), 2.into()),
                    _ => unreachable!(),
                })
                .collect();
            let values = candidate(&p, &graph, &counts);
            if differential(&p, &graph, 1, &values, &runs) {
                feasible += 1;
            } else {
                refuted += 1;
            }
        }
    }
    assert_eq!((feasible, refuted), (5, 10));
}

#[test]
fn mode_numbers_need_not_equal_original_control_places() {
    let mut p = phase_net();
    p.initial.swap(0, 1);
    for transition in &mut p.transitions {
        for arcs in [&mut transition.pre, &mut transition.post] {
            for (place, _) in arcs {
                if *place < 2 {
                    *place = 1 - *place;
                }
            }
        }
    }
    let graph = control::build(&p, &[0, 1], 100).unwrap();
    assert_eq!(graph.modes, vec![1, 0]);
    let values = candidate(
        &p,
        &graph,
        &vec![Q::from_integer(1.into()); graph.edges.len()],
    );
    let runs = walks(&p, &graph, 4);
    assert!(!differential(&p, &graph, 1, &values, &runs));
}

#[test]
fn concrete_walks_preserve_weighted_reads_repeated_controls_and_edge_copies() {
    let mut p = phase_net();
    p.initial[2] = 3;
    p.transitions.push(Transition {
        name: "return".into(),
        pre: vec![(1, 1)],
        post: vec![(0, 1)],
    });
    p.transitions.push(Transition {
        name: "unguarded".into(),
        pre: vec![(2, 2)],
        post: vec![(2, 3)],
    });
    let graph = control::build(&p, &[0, 1], 100).unwrap();
    assert_eq!(
        graph
            .edges
            .iter()
            .filter(|edge| edge.transition == 4)
            .count(),
        2
    );
    let runs = walks(&p, &graph, 4);
    assert!(runs.len() > 30);
    for (q, values) in runs.iter().step_by(13) {
        assert!(differential(&p, &graph, *q, values, &runs));
    }
}

#[test]
fn causal_phase_is_master_feasible_and_moment_refutable() {
    let mut p = phase_net();
    p.target.push(Constraint {
        coefficients: vec![0, 0, 0, 1],
        bound: 1,
        equality: false,
    });
    let graph = control::build(&p, &[0, 1], 100).unwrap();
    let values = candidate(
        &p,
        &graph,
        &vec![Q::from_integer(1.into()); graph.edges.len()],
    );
    assert!(system_holds(
        &token_cut::master(&p, &graph, 1).unwrap(),
        &values
    ));
    let reference = token_flow::relaxation(&p, &graph, 1).unwrap();
    reference
        .check(&reference.refute(deadline()).unwrap())
        .unwrap();
    let out = token_cut::solve(&p, Duration::from_secs(5));
    assert_eq!(out.verdict, "unreachable", "{}", out.reason);
    token_cut::verify_certificate(&p, out.proof.as_ref().unwrap()).unwrap();
}

#[test]
fn zero_count_unbounded_edges_are_not_deleted_or_given_zero_capacity() {
    let mut p = phase_net();
    p.transitions.push(Transition {
        name: "return".into(),
        pre: vec![(1, 1)],
        post: vec![(0, 1)],
    });
    let graph = control::build(&p, &[0, 1], 100).unwrap();
    let counts: Vec<_> = graph
        .edges
        .iter()
        .map(|edge| Q::from_integer(i64::from(edge.transition != 3).into()))
        .collect();
    let values = candidate(&p, &graph, &counts);
    let runs = walks(&p, &graph, 4);
    assert!(differential(&p, &graph, 1, &values, &runs));
    assert!(
        token_cut::cut_row(
            &p,
            &graph,
            1,
            &Cut {
                place: 2,
                modes: vec![1]
            }
        )
        .is_err()
    );
}

fn phase_certificate(p: &Problem) -> serde_json::Value {
    let graph = control::build(p, &[0, 1], 100).unwrap();
    let terminals = (0..graph.modes.len())
        .map(|q| {
            let cuts = vec![Cut {
                place: 2,
                modes: vec![1],
            }];
            let mut system = token_cut::master(p, &graph, q).unwrap();
            for cut in &cuts {
                system
                    .rows
                    .push(token_cut::cut_row(p, &graph, q, cut).unwrap());
            }
            let multipliers = system.refute(deadline()).unwrap();
            token_cut::Terminal { cuts, multipliers }
        })
        .collect();
    serde_json::to_value(token_cut::Certificate {
        kind: "token-cut-v1".into(),
        controls: vec![0, 1],
        terminals,
    })
    .unwrap()
}

#[test]
fn certificates_reconstruct_control_and_reject_malformed_cuts_and_missing_terminals() {
    let mut p = phase_net();
    p.target.push(Constraint {
        coefficients: vec![0, 0, 0, 1],
        bound: 1,
        equality: false,
    });
    let proof = phase_certificate(&p);
    token_cut::verify_certificate(&p, &proof).unwrap();
    let mut missing = proof.clone();
    missing["terminals"].as_array_mut().unwrap().pop();
    assert!(token_cut::verify_certificate(&p, &missing).is_err());
    for controls in [vec![0], vec![0, 0], vec![1, 0], vec![0, 4], vec![0, 1, 2]] {
        let mut wrong = proof.clone();
        wrong["controls"] = serde_json::json!(controls);
        assert!(token_cut::verify_certificate(&p, &wrong).is_err());
    }
    for cut in [
        Cut {
            place: 4,
            modes: vec![1],
        },
        Cut {
            place: 2,
            modes: vec![2],
        },
        Cut {
            place: 2,
            modes: vec![1, 1],
        },
        Cut {
            place: 2,
            modes: vec![1, 0],
        },
        Cut {
            place: 2,
            modes: vec![0],
        },
    ] {
        let mut wrong = proof.clone();
        wrong["terminals"][0]["cuts"][0] = serde_json::to_value(cut).unwrap();
        assert!(token_cut::verify_certificate(&p, &wrong).is_err());
    }
    let mut changed = p.clone();
    changed.transitions.push(Transition {
        name: "produce_early".into(),
        pre: vec![(0, 1)],
        post: vec![(0, 1), (2, 1)],
    });
    assert!(token_cut::verify_certificate(&changed, &proof).is_err());
    let mut wrong = proof.clone();
    wrong["terminals"][1]["cuts"] = serde_json::json!([]);
    assert!(token_cut::verify_certificate(&p, &wrong).is_err());
}

#[test]
fn reachable_noninitial_terminal_and_initial_targets_are_replayed() {
    let mut p = phase_net();
    p.target.push(Constraint {
        coefficients: vec![0, 1, 0, 0],
        bound: 1,
        equality: true,
    });
    let out = token_cut::solve(&p, Duration::from_secs(5));
    assert_eq!(out.verdict, "reachable", "{}", out.reason);
    p.check_witness(&out.trace).unwrap();
    p.target.clear();
    let out = token_cut::solve(&p, Duration::from_secs(5));
    assert_eq!(out.verdict, "reachable");
    assert!(out.trace.is_empty());
    p.check_witness(&out.trace).unwrap();
}

#[test]
fn separation_rejects_invalid_dimensions_coordinates_and_nonconservation() {
    let p = phase_net();
    let graph = control::build(&p, &[0, 1], 100).unwrap();
    let runs = walks(&p, &graph, 0);
    let values = &runs[0].1;
    for (q, i, point) in [
        (2, 0, values.as_slice()),
        (0, 4, values.as_slice()),
        (0, 0, &values[..1]),
    ] {
        assert!(matches!(
            token_cut::separate_place(&p, &graph, q, i, point, deadline()),
            Separation::Unknown
        ));
    }
    let mut changed = values.clone();
    changed[graph.edges.len() + 2] += Q::from_integer(1.into());
    assert!(matches!(
        token_cut::separate_place(&p, &graph, 0, 2, &changed, deadline()),
        Separation::Unknown
    ));
    changed[0] = Q::from_integer((-1).into());
    assert!(matches!(
        token_cut::separate_place(&p, &graph, 0, 0, &changed, deadline()),
        Separation::Unknown
    ));
    assert!(matches!(
        token_cut::separate_place(&p, &graph, 0, 0, values, Instant::now()),
        Separation::Unknown
    ));
}
