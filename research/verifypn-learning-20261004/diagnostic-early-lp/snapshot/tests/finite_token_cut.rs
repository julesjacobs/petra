use num_bigint::BigInt;
use num_rational::BigRational as Q;
use num_traits::Zero;
use std::{
    collections::{BTreeSet, HashMap, VecDeque},
    time::{Duration, Instant},
};
use vass_reach::{
    control,
    finite_control::{self, Graph},
    model::{Constraint, Problem, Transition},
    place_bounds,
    token_cut::{self, Cut, Separation},
};

fn deadline() -> Instant {
    Instant::now() + Duration::from_secs(10)
}

fn weighted_cycle() -> Problem {
    Problem {
        places: vec!["x".into(), "y".into()],
        initial: vec![2, 0],
        transitions: vec![
            Transition {
                name: "forward".into(),
                pre: vec![(0, 2)],
                post: vec![(1, 2)],
            },
            Transition {
                name: "back".into(),
                pre: vec![(1, 2)],
                post: vec![(0, 2)],
            },
            Transition {
                name: "read".into(),
                pre: vec![(0, 2)],
                post: vec![(0, 2)],
            },
        ],
        target: vec![Constraint {
            coefficients: vec![1, 0],
            bound: 1,
            equality: true,
        }],
    }
}

fn potential(groups: &[&[usize]]) -> place_bounds::Certificate {
    place_bounds::Certificate {
        potentials: groups
            .iter()
            .map(|g| place_bounds::Potential {
                weights: g.iter().map(|&i| (i, "1".into())).collect(),
            })
            .collect(),
        ..Default::default()
    }
}

type ProjectedGraph = (Vec<Vec<u64>>, Vec<(usize, usize, usize)>);

fn projected_reference(
    p: &Problem,
    controls: &[usize],
    bounds: &[Option<BigInt>],
) -> ProjectedGraph {
    let initial: Vec<_> = controls.iter().map(|&i| p.initial[i]).collect();
    let mut modes = vec![initial.clone()];
    let mut indices = HashMap::from([(initial, 0)]);
    let mut pending = VecDeque::from([0]);
    let mut edges = vec![];
    while let Some(source) = pending.pop_front() {
        for (t, tr) in p.transitions.iter().enumerate() {
            let mut next = vec![];
            for (&i, &value) in controls.iter().zip(&modes[source]) {
                let pre = tr.pre.iter().find(|&&(j, _)| j == i).map_or(0, |&(_, w)| w);
                let post = tr
                    .post
                    .iter()
                    .find(|&&(j, _)| j == i)
                    .map_or(0, |&(_, w)| w);
                if value < pre {
                    break;
                }
                let result = BigInt::from(value) - pre + post;
                if result > *bounds[i].as_ref().unwrap() {
                    break;
                }
                next.push(result.try_into().unwrap());
            }
            if next.len() != controls.len() {
                continue;
            }
            let target = if let Some(&q) = indices.get(&next) {
                q
            } else {
                let q = modes.len();
                indices.insert(next.clone(), q);
                modes.push(next);
                pending.push_back(q);
                q
            };
            edges.push((source, target, t));
        }
    }
    (modes, edges)
}

fn multi_counter() -> Problem {
    Problem {
        places: (0..4).map(|i| i.to_string()).collect(),
        initial: vec![2, 0, 3, 0],
        transitions: vec![
            Transition {
                name: "a".into(),
                pre: vec![(0, 1)],
                post: vec![(1, 1)],
            },
            Transition {
                name: "b".into(),
                pre: vec![(1, 1)],
                post: vec![(0, 1)],
            },
            Transition {
                name: "c".into(),
                pre: vec![(2, 1)],
                post: vec![(3, 1)],
            },
            Transition {
                name: "d".into(),
                pre: vec![(3, 1)],
                post: vec![(2, 1)],
            },
            Transition {
                name: "read".into(),
                pre: vec![(0, 2), (2, 2)],
                post: vec![(0, 2), (2, 2)],
            },
            Transition {
                name: "disabled".into(),
                pre: vec![(0, 3)],
                post: vec![(0, 3)],
            },
            Transition {
                name: "stutter".into(),
                pre: vec![],
                post: vec![],
            },
        ],
        target: vec![],
    }
}

#[test]
fn projected_graph_matches_independent_reference_with_multiple_weighted_counters() {
    let p = multi_counter();
    let finite = place_bounds::check(&p, &potential(&[&[0, 1], &[2, 3]])).unwrap();
    for mask in 0..16 {
        let controls: Vec<_> = (0..4).filter(|i| mask & (1 << i) != 0).collect();
        let graph = finite_control::build(&p, &controls, &finite, Some(deadline())).unwrap();
        let (modes, edges) = projected_reference(&p, &controls, &finite);
        assert_eq!(graph.modes, modes);
        assert_eq!(
            graph
                .edges
                .iter()
                .map(|e| (e.source, e.target, e.transition))
                .collect::<Vec<_>>(),
            edges
        );
        for q in 0..graph.mode_count() {
            for (i, &place) in controls.iter().enumerate() {
                assert_eq!(graph.value(q, place), Some(graph.modes[q][i]));
            }
        }
    }
    let graph = finite_control::build(&p, &[0, 2], &finite, None).unwrap();
    assert_eq!(graph.modes.len(), 12);
    assert!(graph.modes.contains(&vec![2, 3]));
}

#[test]
fn full_projection_matches_original_bfs_and_every_small_target() {
    let mut p = multi_counter();
    let finite = place_bounds::check(&p, &potential(&[&[0, 1], &[2, 3]])).unwrap();
    let graph = finite_control::build(&p, &[0, 1, 2, 3], &finite, None).unwrap();
    let mut seen = BTreeSet::from([p.initial.clone()]);
    let mut pending = vec![p.initial.clone()];
    while let Some(m) = pending.pop() {
        for t in 0..p.transitions.len() {
            if let Some(next) = p.fire(&m, t).unwrap()
                && seen.insert(next.clone())
            {
                pending.push(next);
            }
        }
    }
    assert_eq!(seen, graph.modes.iter().cloned().collect());
    assert_eq!(seen.len(), 12);
    for x in 0..=3 {
        for y in 0..=3 {
            p.target = vec![
                Constraint {
                    coefficients: vec![1, 0, 0, 0],
                    bound: x,
                    equality: true,
                },
                Constraint {
                    coefficients: vec![0, 1, 0, 0],
                    bound: y,
                    equality: true,
                },
            ];
            let original = seen.iter().any(|m| p.accepts(m).unwrap());
            let mut feasible = false;
            for q in 0..graph.mode_count() {
                let system = token_cut::master(&p, &graph, q).unwrap();
                if p.accepts(&graph.modes[q]).unwrap() {
                    feasible = true;
                } else {
                    system.check(&system.refute(deadline()).unwrap()).unwrap();
                }
            }
            assert_eq!(original, feasible);
        }
    }
}

#[test]
fn finite_method_solves_parity_without_a_onehot_controller_and_replays_positives() {
    let mut p = weighted_cycle();
    assert!(control::discover(&p, deadline(), 8192).is_none());
    let out = token_cut::solve_finite(&p, Duration::from_secs(5));
    assert_eq!(out.verdict, "unreachable", "{}", out.reason);
    let proof = out.proof.unwrap();
    assert_eq!(proof["kind"], "finite-token-cut-v1");
    assert!(!proof["controls"].as_array().unwrap().is_empty());
    token_cut::verify_finite_certificate(&p, &proof).unwrap();
    p.target[0].bound = 0;
    let out = token_cut::solve_finite(&p, Duration::from_secs(5));
    assert_eq!(out.verdict, "reachable", "{}", out.reason);
    assert!(!out.trace.is_empty());
    p.check_witness(&out.trace).unwrap();
}

#[test]
fn finite_cuts_and_separation_preserve_original_walks() {
    let mut p = weighted_cycle();
    p.target.clear();
    let finite = place_bounds::check(&p, &potential(&[&[0, 1]])).unwrap();
    let graph = finite_control::build(&p, &[0], &finite, None).unwrap();
    let mut pending = vec![(0, p.initial.clone(), vec![Q::zero(); graph.edges.len()], 0)];
    let mut checked = 0;
    while let Some((q, marking, counts, depth)) = pending.pop() {
        checked += 1;
        let values: Vec<_> = counts
            .iter()
            .cloned()
            .chain(marking.iter().map(|&n| Q::from_integer(n.into())))
            .collect();
        let system = token_cut::master(&p, &graph, q).unwrap();
        for row in &system.rows {
            assert!(
                row.coefficients
                    .iter()
                    .map(|(i, a)| &values[*i] * a)
                    .sum::<Q>()
                    >= Q::from_integer(row.bound.clone())
            );
        }
        for place in 0..p.places.len() {
            assert_eq!(
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
            );
            for mask in 0..(1 << graph.mode_count()) {
                let cut = Cut {
                    place,
                    modes: (0..graph.mode_count())
                        .filter(|i| mask & (1 << i) != 0)
                        .collect(),
                };
                let row = token_cut::bounded_cut_row(&p, &graph, q, &cut, &finite).unwrap();
                assert!(
                    row.coefficients
                        .iter()
                        .map(|(i, a)| &values[*i] * a)
                        .sum::<Q>()
                        >= Q::from_integer(row.bound)
                );
            }
        }
        if depth == 5 {
            continue;
        }
        for (e, edge) in graph
            .edges
            .iter()
            .enumerate()
            .filter(|(_, e)| e.source == q)
        {
            if let Some(next) = p.fire(&marking, edge.transition).unwrap() {
                let mut counts = counts.clone();
                counts[e] += Q::from_integer(1.into());
                pending.push((edge.target, next, counts, depth + 1));
            }
        }
    }
    assert!(checked > 10);
}

#[test]
fn limits_deadlines_invalid_coordinates_and_overflow_never_return_partial_graphs() {
    let p = weighted_cycle();
    let finite = place_bounds::check(&p, &potential(&[&[0, 1]])).unwrap();
    assert!(finite_control::build_with_limits(&p, &[0], &finite, 1, 8192, None).is_err());
    assert!(finite_control::build_with_limits(&p, &[0], &finite, 4096, 2, None).is_err());
    assert!(finite_control::build_with_limits(&p, &[0], &finite, 0, 8192, None).is_err());
    assert!(finite_control::build(&p, &[0], &finite, Some(Instant::now())).is_err());
    for controls in [vec![0, 0], vec![1, 0], vec![2]] {
        assert!(finite_control::build(&p, &controls, &finite, None).is_err());
    }
    assert!(finite_control::build(&p, &[0], &[], None).is_err());
    assert!(finite_control::build(&p, &[0], &[Some(1.into())], None).is_err());
    assert!(finite_control::build(&p, &[0], &[Some(BigInt::from(u64::MAX) + 1)], None).is_err());
    assert_eq!(
        token_cut::solve_finite(&p, Duration::ZERO).verdict,
        "unknown"
    );
    let mut invalid = p.clone();
    invalid.initial.pop();
    assert_eq!(
        token_cut::solve_finite(&invalid, Duration::from_secs(1)).verdict,
        "unknown"
    );
    let huge = Problem {
        places: vec!["x".into(), "y".into()],
        initial: vec![u64::MAX, 0],
        transitions: vec![
            Transition {
                name: "read".into(),
                pre: vec![(0, u64::MAX)],
                post: vec![(0, u64::MAX)],
            },
            Transition {
                name: "transfer".into(),
                pre: vec![(1, 1)],
                post: vec![(0, 1)],
            },
        ],
        target: vec![],
    };
    let finite = place_bounds::check(&huge, &potential(&[&[0, 1]])).unwrap();
    let graph = finite_control::build(&huge, &[0], &finite, None).unwrap();
    assert_eq!(graph.modes, vec![vec![u64::MAX]]);
    assert_eq!(graph.edges.len(), 1);
    assert_eq!(graph.edges[0].transition, 0);
}

#[test]
fn finite_checker_rejects_missing_modes_forged_bounds_and_cuts() {
    let p = weighted_cycle();
    let proof = token_cut::solve_finite(&p, Duration::from_secs(5))
        .proof
        .unwrap();
    for mutation in 0..7 {
        let mut bad = proof.clone();
        match mutation {
            0 => {
                bad["terminals"].as_array_mut().unwrap().pop();
            }
            1 => bad["bounds"]["potentials"] = serde_json::json!([]),
            2 => bad["controls"] = serde_json::json!([0, 0]),
            3 => bad["terminals"][0]["cuts"] = serde_json::json!([{"place":0,"modes":[999]}]),
            4 => bad["bounds"]["potentials"][0]["weights"][0][1] = serde_json::json!("-1"),
            5 => bad["terminals"][0]["multipliers"] = serde_json::json!([]),
            6 => bad["kind"] = serde_json::json!("bounded-token-cut-v1"),
            _ => unreachable!(),
        }
        assert!(
            token_cut::verify_finite_certificate(&p, &bad).is_err(),
            "mutation {mutation}"
        );
    }
    let mut changed = p;
    changed.transitions.push(Transition {
        name: "source".into(),
        pre: vec![],
        post: vec![(0, 1)],
    });
    assert!(token_cut::verify_finite_certificate(&changed, &proof).is_err());
}

#[test]
fn empty_projection_retains_state_equation_fallback() {
    let p = Problem {
        places: vec!["unbounded".into()],
        initial: vec![0],
        transitions: vec![Transition {
            name: "source".into(),
            pre: vec![],
            post: vec![(0, 1)],
        }],
        target: vec![Constraint {
            coefficients: vec![-1],
            bound: 1,
            equality: false,
        }],
    };
    let graph = finite_control::build(&p, &[], &[], None).unwrap();
    assert_eq!(graph.modes, vec![Vec::<u64>::new()]);
    assert_eq!(graph.edges.len(), 1);
    let out = token_cut::solve_finite(&p, Duration::from_secs(5));
    assert_eq!(out.verdict, "unreachable", "{}", out.reason);
    let proof = out.proof.unwrap();
    assert_eq!(proof["controls"], serde_json::json!([]));
    token_cut::verify_finite_certificate(&p, &proof).unwrap();
}

#[test]
fn cli_emits_and_verifies_finite_proofs() {
    let root = std::env::temp_dir().join(format!(
        "finite-token-cut-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir(&root).unwrap();
    let input = root.join("input.json");
    let answer = root.join("answer.json");
    std::fs::write(&input, serde_json::to_vec(&weighted_cycle()).unwrap()).unwrap();
    let run = std::process::Command::new(env!("CARGO_BIN_EXE_vass-reach"))
        .args(["--method", "finite-token-cut", "--seconds", "5", "--json"])
        .arg(&input)
        .output()
        .unwrap();
    assert!(
        run.status.success(),
        "{}",
        String::from_utf8_lossy(&run.stderr)
    );
    let parsed: serde_json::Value = serde_json::from_slice(&run.stdout).unwrap();
    assert_eq!(parsed["verdict"], "unreachable");
    assert_eq!(parsed["proof"]["kind"], "relevance-v1");
    assert_eq!(parsed["proof"]["inner"]["kind"], "finite-token-cut-v1");
    std::fs::write(&answer, &run.stdout).unwrap();
    let verify = std::process::Command::new(env!("CARGO_BIN_EXE_vass-reach"))
        .arg("--json")
        .arg(&input)
        .arg("--verify")
        .arg(&answer)
        .output()
        .unwrap();
    assert!(
        verify.status.success(),
        "{}",
        String::from_utf8_lossy(&verify.stderr)
    );
    assert_eq!(
        serde_json::from_slice::<serde_json::Value>(&verify.stdout).unwrap()["verified"],
        true
    );
    std::fs::remove_dir_all(root).unwrap();
}

fn live_cycle() -> Problem {
    serde_json::from_value(serde_json::json!({
        "places":["c","d","x","y"],"initial":[2,0,2,0],
        "transitions":[
            {"name":"convert-at-c","pre":[[0,2],[2,2]],"post":[[0,2],[3,2]]},
            {"name":"advance","pre":[[0,2],[3,2]],"post":[[0,1],[1,1],[3,2]]},
            {"name":"advance-again","pre":[[0,1],[1,1],[3,2]],"post":[[1,2],[3,2]]},
            {"name":"convert-at-d","pre":[[1,2],[3,2]],"post":[[1,2],[2,2]]},
            {"name":"return","pre":[[1,2],[2,2]],"post":[[0,2],[2,2]]}],
        "target":[{"coefficients":[1,0,0,0],"bound":1,"equality":false},
            {"coefficients":[0,1,0,0],"bound":1,"equality":false},
            {"coefficients":[0,0,1,0],"bound":2,"equality":false}]
    }))
    .unwrap()
}

fn add_equality(
    system: &mut vass_reach::linear::System,
    terms: Vec<(usize, BigInt)>,
    bound: BigInt,
) {
    let mut coefficients = std::collections::BTreeMap::<usize, BigInt>::new();
    for (i, a) in terms {
        *coefficients.entry(i).or_default() += a;
    }
    let coefficients: Vec<_> = coefficients
        .into_iter()
        .filter(|(_, a)| !a.is_zero())
        .collect();
    system.rows.push(vass_reach::linear::Row {
        coefficients: coefficients.iter().map(|(i, a)| (*i, -a)).collect(),
        bound: -&bound,
    });
    system.rows.push(vass_reach::linear::Row {
        coefficients,
        bound,
    });
}

fn moment_reference(
    p: &Problem,
    graph: &finite_control::FiniteControl,
    terminal: usize,
    finite: &[Option<BigInt>],
) -> vass_reach::linear::System {
    let mut system = token_cut::master(p, graph, terminal).unwrap();
    let moment = |e, i| graph.edges.len() + p.places.len() + e * p.places.len() + i;
    system.variables += graph.edges.len() * p.places.len();
    for q in 0..graph.mode_count() {
        for i in 0..p.places.len() {
            let mut terms = vec![];
            if q == terminal {
                terms.push((graph.edges.len() + i, 1.into()));
            }
            for (e, edge) in graph.edges.iter().enumerate() {
                if edge.source == q {
                    terms.push((moment(e, i), 1.into()));
                }
                if edge.target == q {
                    terms.push((moment(e, i), (-1).into()));
                    let tr = &p.transitions[edge.transition];
                    for &(j, w) in &tr.pre {
                        if i == j {
                            terms.push((e, w.into()));
                        }
                    }
                    for &(j, w) in &tr.post {
                        if i == j {
                            terms.push((e, -BigInt::from(w)));
                        }
                    }
                }
            }
            add_equality(
                &mut system,
                terms,
                if q == 0 {
                    p.initial[i].into()
                } else {
                    0.into()
                },
            );
        }
    }
    for (e, edge) in graph.edges.iter().enumerate() {
        for i in 0..p.places.len() {
            if let Some(value) = graph.value(edge.source, i) {
                add_equality(
                    &mut system,
                    vec![(moment(e, i), 1.into()), (e, -BigInt::from(value))],
                    0.into(),
                );
            } else {
                let pre = p.transitions[edge.transition]
                    .pre
                    .iter()
                    .find(|&&(j, _)| i == j)
                    .map_or(0, |&(_, w)| w);
                system.rows.push(vass_reach::linear::Row {
                    coefficients: vec![(e, -BigInt::from(pre)), (moment(e, i), 1.into())],
                    bound: 0.into(),
                });
                if let Some(upper) = finite.get(i).and_then(Option::as_ref) {
                    system.rows.push(vass_reach::linear::Row {
                        coefficients: vec![
                            (e, upper.clone().max(pre.into())),
                            (moment(e, i), (-1).into()),
                        ],
                        bound: 0.into(),
                    });
                }
            }
        }
    }
    system
}

#[test]
fn bounded_flow_separates_a_live_weighted_cycle_with_two_selected_counters() {
    let p = live_cycle();
    assert!(control::discover(&p, deadline(), 8192).is_none());
    let finite = place_bounds::check(&p, &potential(&[&[0, 1], &[2, 3]])).unwrap();
    let graph = finite_control::build(&p, &[0, 1], &finite, None).unwrap();
    assert_eq!(graph.modes, vec![vec![2, 0], vec![1, 1], vec![0, 2]]);
    assert_eq!(graph.edges.len(), 5);
    let mut seen = BTreeSet::from([p.initial.clone()]);
    let mut pending = vec![p.initial.clone()];
    let mut fired = BTreeSet::new();
    while let Some(m) = pending.pop() {
        assert!(!p.accepts(&m).unwrap());
        for t in 0..p.transitions.len() {
            if let Some(next) = p.fire(&m, t).unwrap() {
                fired.insert(t);
                if seen.insert(next.clone()) {
                    pending.push(next);
                }
            }
        }
    }
    assert_eq!(seen.len(), 5);
    assert_eq!(fired, (0..5).collect());
    let counts = [1, 2, 1, 1, 1];
    let values: Vec<Q> = graph
        .edges
        .iter()
        .map(|e| Q::from_integer(counts[e.transition].into()))
        .chain([1, 1, 2, 0].map(|n| Q::from_integer(n.into())))
        .collect();
    let mut unbounded = moment_reference(&p, &graph, 1, &[]);
    for (i, value) in values.iter().enumerate() {
        add_equality(
            &mut unbounded,
            vec![(i, value.denom().clone())],
            value.numer().clone(),
        );
    }
    assert!(unbounded.rational_model(deadline()).is_some());
    for place in 0..4 {
        assert_eq!(
            token_cut::separate_place(&p, &graph, 1, place, &values, deadline()),
            Separation::Feasible
        );
    }
    let Separation::Cut(cut) =
        token_cut::separate_bounded_place(&p, &graph, 1, 3, &values, &finite, deadline())
    else {
        panic!("expected bounded y cut");
    };
    let row = token_cut::bounded_cut_row(&p, &graph, 1, &cut, &finite).unwrap();
    assert!(
        row.coefficients
            .iter()
            .map(|(i, a)| &values[*i] * a)
            .sum::<Q>()
            < Q::from_integer(row.bound)
    );
    for q in 0..graph.mode_count() {
        let reference = moment_reference(&p, &graph, q, &finite);
        reference
            .check(&reference.refute(deadline()).unwrap())
            .unwrap();
    }
    let out = token_cut::solve_finite(&p, Duration::from_secs(5));
    assert_eq!(out.verdict, "unreachable", "{}", out.reason);
    let proof = out.proof.unwrap();
    assert!(proof["controls"].as_array().unwrap().len() >= 2);
    assert!(
        proof["terminals"]
            .as_array()
            .unwrap()
            .iter()
            .any(|t| !t["cuts"].as_array().unwrap().is_empty())
    );
    token_cut::verify_finite_certificate(&p, &proof).unwrap();
}
