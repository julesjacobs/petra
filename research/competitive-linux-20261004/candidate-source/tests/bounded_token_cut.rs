use num_bigint::BigInt;
use num_rational::BigRational as Q;
use num_traits::{Signed, Zero};
use std::time::{Duration, Instant};
use vass_reach::{
    control::{self, Control},
    linear::{Row, System},
    model::{Constraint, Problem, Transition},
    place_bounds,
    token_cut::{self, Cut, Separation},
    token_flow,
};

fn deadline() -> Instant {
    Instant::now() + Duration::from_secs(5)
}

fn cyclic_net() -> Problem {
    Problem {
        places: ["a", "b", "x", "y"].map(String::from).to_vec(),
        initial: vec![1, 0, 2, 0],
        transitions: vec![
            Transition {
                name: "advance".into(),
                pre: vec![(0, 1), (3, 2)],
                post: vec![(1, 1), (3, 2)],
            },
            Transition {
                name: "return".into(),
                pre: vec![(1, 1), (2, 1)],
                post: vec![(0, 1), (3, 1)],
            },
        ],
        target: vec![],
    }
}

fn unreachable_query() -> Problem {
    let mut p = cyclic_net();
    p.target = vec![
        Constraint {
            coefficients: vec![0, 1, 0, 0],
            bound: 1,
            equality: true,
        },
        Constraint {
            coefficients: vec![0, 0, 0, 1],
            bound: 1,
            equality: true,
        },
    ];
    p
}

fn holds(row: &Row, values: &[Q]) -> bool {
    let lhs: Q = row.coefficients.iter().map(|(i, a)| &values[*i] * a).sum();
    lhs >= Q::from_integer(row.bound.clone())
}

fn system_holds(system: &System, values: &[Q]) -> bool {
    values.len() == system.variables
        && values.iter().all(|v| !v.is_negative())
        && system.rows.iter().all(|row| holds(row, values))
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

fn bounded_reference(p: &Problem, graph: &Control, q: usize, finite: &[Option<BigInt>]) -> System {
    let mut system = token_flow::relaxation(p, graph, q).unwrap();
    for (e, edge) in graph.edges.iter().enumerate() {
        for (i, upper) in finite.iter().enumerate() {
            if graph.places.contains(&i) {
                continue;
            }
            if let Some(upper) = upper {
                let pre = p.transitions[edge.transition]
                    .pre
                    .iter()
                    .find(|&&(place, _)| place == i)
                    .map_or(0, |&(_, weight)| weight);
                let upper = upper.clone().max(pre.into());
                let moment = graph.edges.len() + p.places.len() + e * p.places.len() + i;
                system.rows.push(Row {
                    coefficients: vec![(e, upper), (moment, (-1).into())],
                    bound: BigInt::zero(),
                });
            }
        }
    }
    system
}

fn candidate(p: &Problem, graph: &Control, counts: &[Q]) -> Vec<Q> {
    let mut marking: Vec<_> = p
        .initial
        .iter()
        .map(|&n| Q::from_integer(n.into()))
        .collect();
    for (edge, count) in graph.edges.iter().zip(counts) {
        for &(i, weight) in &p.transitions[edge.transition].pre {
            marking[i] -= count * BigInt::from(weight);
        }
        for &(i, weight) in &p.transitions[edge.transition].post {
            marking[i] += count * BigInt::from(weight);
        }
    }
    counts.iter().cloned().chain(marking).collect()
}

#[test]
fn certified_bounds_refute_a_strongly_connected_unbounded_moment_model() {
    let p = unreachable_query();
    let graph = control::build(&p, &[0, 1], 100).unwrap();
    assert_eq!(graph.edges.len(), 2);
    assert!(
        graph
            .edges
            .iter()
            .any(|edge| edge.source == 0 && edge.target == 1)
    );
    assert!(
        graph
            .edges
            .iter()
            .any(|edge| edge.source == 1 && edge.target == 0)
    );
    let counts: Vec<_> = graph
        .edges
        .iter()
        .map(|edge| Q::from_integer((2 - edge.transition).into()))
        .collect();
    let values = candidate(&p, &graph, &counts);
    let mut unbounded = token_flow::relaxation(&p, &graph, 1).unwrap();
    fix_prefix(&mut unbounded, &values);
    let model = unbounded.rational_model(deadline()).unwrap();
    assert!(system_holds(&unbounded, &model));
    let finite = place_bounds::check(&p, &place_bounds::discover(&p, deadline())).unwrap();
    assert_eq!(finite[3], Some(2.into()));
    let Separation::Cut(cut) =
        token_cut::separate_bounded_place(&p, &graph, 1, 3, &values, &finite, deadline())
    else {
        panic!("bounded data place did not separate the spurious moment model");
    };
    assert!(!holds(
        &token_cut::bounded_cut_row(&p, &graph, 1, &cut, &finite).unwrap(),
        &values
    ));
    assert!(token_cut::cut_row(&p, &graph, 1, &cut).is_err());
    let bounded = bounded_reference(&p, &graph, 1, &finite);
    bounded.check(&bounded.refute(deadline()).unwrap()).unwrap();
    let out = token_cut::solve_bounded(&p, Duration::from_secs(5));
    assert_eq!(out.verdict, "unreachable", "{}", out.reason);
    token_cut::verify_bounded_certificate(&p, out.proof.as_ref().unwrap()).unwrap();
}

#[test]
fn capacities_separate_a_live_cycle_with_all_transitions_reachable() {
    let p: Problem = serde_json::from_value(serde_json::json!({
        "places":["A","B","C","x","y"], "initial":[1,0,0,1,0],
        "transitions":[
            {"name":"convert-at-A","pre":[[0,1],[3,1]],"post":[[0,1],[4,1]]},
            {"name":"advance-to-B","pre":[[0,1],[4,1]],"post":[[1,1],[4,1]]},
            {"name":"advance-to-C","pre":[[1,1],[4,1]],"post":[[2,1],[4,1]]},
            {"name":"convert-at-C","pre":[[2,1],[4,1]],"post":[[2,1],[3,1]]},
            {"name":"return-to-A","pre":[[2,1],[3,1]],"post":[[0,1],[3,1]]}],
        "target":[
            {"coefficients":[0,1,0,0,0],"bound":1,"equality":false},
            {"coefficients":[0,0,0,1,0],"bound":1,"equality":false}]
    }))
    .unwrap();
    let mut reachable = std::collections::BTreeSet::from([p.initial.clone()]);
    let mut pending = vec![p.initial.clone()];
    let mut fired = std::collections::BTreeSet::new();
    while let Some(marking) = pending.pop() {
        assert!(!p.accepts(&marking).unwrap());
        for transition in 0..p.transitions.len() {
            if let Some(next) = p.fire(&marking, transition).unwrap() {
                fired.insert(transition);
                if reachable.insert(next.clone()) {
                    assert!(reachable.len() <= 5);
                    pending.push(next);
                }
            }
        }
    }
    assert_eq!(
        reachable,
        std::collections::BTreeSet::from([
            vec![1, 0, 0, 1, 0],
            vec![1, 0, 0, 0, 1],
            vec![0, 1, 0, 0, 1],
            vec![0, 0, 1, 0, 1],
            vec![0, 0, 1, 1, 0],
        ])
    );
    assert_eq!(fired, (0..5).collect());

    let graph = control::build(&p, &[0, 1, 2], 100).unwrap();
    assert_eq!(graph.edges.len(), 5);
    let terminal = graph.modes.iter().position(|&place| place == 1).unwrap();
    let firing_counts = [1u64, 2, 1, 1, 1];
    let counts: Vec<_> = graph
        .edges
        .iter()
        .map(|edge| Q::from_integer(firing_counts[edge.transition].into()))
        .collect();
    let values = candidate(&p, &graph, &counts);
    assert_eq!(
        &values[graph.edges.len()..],
        [0, 1, 0, 1, 0].map(|n| Q::from_integer(n.into()))
    );
    assert!(system_holds(
        &token_cut::master(&p, &graph, terminal).unwrap(),
        &values
    ));
    let mut moments = values.clone();
    let x_moments = [1u64, 1, 0, 0, 1];
    let y_moments = [0u64, 2, 2, 1, 1];
    for (index, edge) in graph.edges.iter().enumerate() {
        for place in 0..3 {
            moments.push(if graph.modes[edge.source] == place {
                counts[index].clone()
            } else {
                Q::zero()
            });
        }
        moments.push(Q::from_integer(x_moments[edge.transition].into()));
        moments.push(Q::from_integer(y_moments[edge.transition].into()));
    }
    assert!(system_holds(
        &token_flow::relaxation(&p, &graph, terminal).unwrap(),
        &moments
    ));
    for place in 0..p.places.len() {
        assert!(matches!(
            token_cut::separate_place(&p, &graph, terminal, place, &values, deadline()),
            Separation::Feasible
        ));
    }

    let bounds = place_bounds::Certificate {
        kind: "place-bounds-v1".into(),
        potentials: vec![place_bounds::Potential {
            weights: vec![(3, "1".into()), (4, "1".into())],
        }],
    };
    let finite = place_bounds::check(&p, &bounds).unwrap();
    assert_eq!(finite, [None, None, None, Some(1.into()), Some(1.into())]);
    let Separation::Cut(cut) =
        token_cut::separate_bounded_place(&p, &graph, terminal, 4, &values, &finite, deadline())
    else {
        panic!("certified y capacity did not separate the spurious model");
    };
    assert!(!holds(
        &token_cut::bounded_cut_row(&p, &graph, terminal, &cut, &finite).unwrap(),
        &values
    ));
    assert!(token_cut::cut_row(&p, &graph, terminal, &cut).is_err());
    for terminal in 0..graph.modes.len() {
        let bounded = bounded_reference(&p, &graph, terminal, &finite);
        bounded.check(&bounded.refute(deadline()).unwrap()).unwrap();
    }
}

#[test]
fn rational_bounded_separation_matches_fixed_count_reference() {
    let p = cyclic_net();
    let graph = control::build(&p, &[0, 1], 100).unwrap();
    let finite = place_bounds::check(&p, &place_bounds::discover(&p, deadline())).unwrap();
    let (mut feasible, mut refuted) = (0, 0);
    for q in 0..2 {
        for half_returns in 0..5 {
            let counts: Vec<_> = graph
                .edges
                .iter()
                .map(|edge| {
                    Q::new(half_returns.into(), 2.into())
                        + Q::from_integer(if edge.transition == 0 {
                            q.into()
                        } else {
                            0.into()
                        })
                })
                .collect();
            let values = candidate(&p, &graph, &counts);
            assert!(system_holds(
                &token_cut::master(&p, &graph, q).unwrap(),
                &values
            ));
            let mut separated = false;
            for place in 0..p.places.len() {
                match token_cut::separate_bounded_place(
                    &p,
                    &graph,
                    q,
                    place,
                    &values,
                    &finite,
                    deadline(),
                ) {
                    Separation::Feasible => {}
                    Separation::Cut(cut) => {
                        assert!(!holds(
                            &token_cut::bounded_cut_row(&p, &graph, q, &cut, &finite).unwrap(),
                            &values
                        ));
                        separated = true;
                    }
                    Separation::Unknown => panic!("unexpected separation failure"),
                }
            }
            let mut reference = bounded_reference(&p, &graph, q, &finite);
            fix_prefix(&mut reference, &values);
            if separated {
                reference
                    .check(&reference.refute(deadline()).unwrap())
                    .unwrap();
                refuted += 1;
            } else {
                assert!(system_holds(
                    &reference,
                    &reference.rational_model(deadline()).unwrap()
                ));
                feasible += 1;
            }
        }
    }
    assert_eq!((feasible, refuted), (6, 4));
}

#[test]
fn bounded_cuts_preserve_concrete_walks_with_reads_and_unguarded_edges() {
    let mut p = cyclic_net();
    p.initial = vec![1, 0, 0, 2];
    p.transitions.push(Transition {
        name: "convert".into(),
        pre: vec![(3, 1)],
        post: vec![(2, 1)],
    });
    let graph = control::build(&p, &[0, 1], 100).unwrap();
    let finite = place_bounds::check(&p, &place_bounds::discover(&p, deadline())).unwrap();
    assert_eq!(finite[2..], [Some(2.into()), Some(2.into())]);
    let mut pending = vec![(
        graph.initial,
        p.initial.clone(),
        vec![Q::zero(); graph.edges.len()],
        0,
    )];
    let mut visited = 0;
    while let Some((q, marking, counts, depth)) = pending.pop() {
        visited += 1;
        let values: Vec<_> = counts
            .iter()
            .cloned()
            .chain(marking.iter().map(|&m| Q::from_integer(m.into())))
            .collect();
        for place in 0..p.places.len() {
            assert!(matches!(
                token_cut::separate_bounded_place(
                    &p,
                    &graph,
                    q,
                    place,
                    &values,
                    &finite,
                    deadline()
                ),
                Separation::Feasible
            ));
            for mask in 0..4 {
                let cut = Cut {
                    place,
                    modes: (0..2).filter(|mode| mask & (1 << mode) != 0).collect(),
                };
                assert!(holds(
                    &token_cut::bounded_cut_row(&p, &graph, q, &cut, &finite).unwrap(),
                    &values
                ));
            }
        }
        if depth == 6 {
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
                pending.push((edge.target, next, next_counts, depth + 1));
            }
        }
    }
    assert!(visited > 10);
    p.target = vec![Constraint {
        coefficients: vec![0, 1, 0, 0],
        bound: 1,
        equality: true,
    }];
    let out = token_cut::solve_bounded(&p, Duration::from_secs(5));
    assert_eq!(out.verdict, "reachable", "{}", out.reason);
    assert!(!out.trace.is_empty());
    p.check_witness(&out.trace).unwrap();
}

#[test]
fn bounded_certificate_rejects_forged_potentials_and_changed_original_net() {
    let p = unreachable_query();
    let out = token_cut::solve_bounded(&p, Duration::from_secs(5));
    assert_eq!(out.verdict, "unreachable", "{}", out.reason);
    let proof = out.proof.unwrap();
    let mut invalid = proof.clone();
    invalid["bounds"]["potentials"][0]["weights"][0][1] = serde_json::json!("-1");
    assert!(token_cut::verify_bounded_certificate(&p, &invalid).is_err());
    let mut changed = p.clone();
    changed.transitions.push(Transition {
        name: "source".into(),
        pre: vec![],
        post: vec![(3, 1)],
    });
    assert!(token_cut::verify_bounded_certificate(&changed, &proof).is_err());
    let mut changed = p.clone();
    changed.initial[2] = 5;
    assert!(token_cut::verify_bounded_certificate(&changed, &proof).is_err());
    let mut invalid = proof.clone();
    invalid["bounds"]["potentials"] = serde_json::json!([]);
    assert!(token_cut::verify_bounded_certificate(&p, &invalid).is_err());
}

#[test]
fn bounded_cli_emits_a_checkable_certificate() {
    let p = unreachable_query();
    let nonce = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let path = std::env::temp_dir().join(format!(
        "pvass-bounded-cut-{}-{nonce}.json",
        std::process::id()
    ));
    std::fs::write(&path, serde_json::to_vec(&p).unwrap()).unwrap();
    let output = std::process::Command::new(env!("CARGO_BIN_EXE_vass-reach"))
        .args(["--method", "bounded-token-cut", "--seconds", "5", "--json"])
        .arg(&path)
        .output();
    std::fs::remove_file(path).unwrap();
    let output = output.unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let answer: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(answer["verdict"], "unreachable");
    assert_eq!(answer["proof"]["kind"], "bounded-token-cut-v1");
    token_cut::verify_bounded_certificate(&p, &answer["proof"]).unwrap();
}
