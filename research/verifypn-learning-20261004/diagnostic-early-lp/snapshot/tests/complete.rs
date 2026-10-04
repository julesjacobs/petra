use num_bigint::BigInt;
use std::time::{Duration, Instant};
use vass_reach::{
    complete::{self, Component, Decision, Limits, Sequence},
    complete_cover::Arc,
    model::{Constraint, Problem, Transition},
};
fn sequence(
    initial: &[i64],
    final_marking: &[i64],
    states: usize,
    entry: usize,
    exit: usize,
    edges: &[(usize, usize, Vec<i64>)],
) -> Sequence {
    Sequence {
        components: vec![Component {
            states,
            entry,
            exit,
            initial: initial.iter().map(|&x| Some(x.into())).collect(),
            final_marking: final_marking.iter().map(|&x| Some(x.into())).collect(),
            rigid: vec![None; initial.len()],
            arcs: edges
                .iter()
                .map(|(s, t, e)| Arc {
                    source: *s,
                    target: *t,
                    effect: e.iter().map(|&x| x.into()).collect(),
                })
                .collect(),
        }],
        bridges: vec![],
    }
}
fn decide(s: Sequence) -> (Decision, complete::Statistics) {
    complete::decide(
        s,
        Limits {
            deadline: Some(Instant::now() + Duration::from_secs(10)),
            max_nodes: Some(100000),
            max_rows: Some(20000),
        },
    )
}
#[test]
fn pure_vass_control_state_counterexample() {
    let (d, stats) = decide(sequence(
        &[1, 0],
        &[1, 1],
        2,
        0,
        0,
        &[(0, 1, vec![-1, 0]), (1, 0, vec![1, 1])],
    ));
    assert_eq!(d, Decision::Reachable, "{stats:?}");
    assert!(stats.transition_refinements > 0);
}
#[test]
fn parity_integer_infeasibility() {
    assert_eq!(
        decide(sequence(&[0], &[1], 1, 0, 0, &[(0, 0, vec![2])])).0,
        Decision::Unreachable
    );
}
#[test]
fn pumping_without_finite_exhaustion() {
    let (d, s) = decide(sequence(
        &[1],
        &[7],
        1,
        0,
        0,
        &[(0, 0, vec![1]), (0, 0, vec![-1])],
    ));
    assert_eq!(d, Decision::Reachable);
    assert!(s.perfect_sequences > 0);
}
#[test]
fn characteristic_solution_is_not_enabled_run() {
    let (d, s) = decide(sequence(
        &[0, 0],
        &[0, 0],
        2,
        0,
        1,
        &[(0, 1, vec![-1, 1]), (1, 0, vec![1, -1]), (1, 1, vec![0, 0])],
    ));
    assert_eq!(d, Decision::Unreachable, "{s:?}");
}
#[test]
fn theta_two_unfolds_bounded_counter() {
    let (d, s) = decide(sequence(
        &[1, 0],
        &[0, 1],
        1,
        0,
        0,
        &[(0, 0, vec![-1, 1]), (0, 0, vec![1, -1])],
    ));
    assert_eq!(d, Decision::Reachable, "{s:?}");
    assert!(s.counter_refinements > 0);
}
#[test]
fn rigid_values_links_and_free_edgeless_component() {
    let mut s = sequence(&[0], &[0], 1, 0, 0, &[]);
    s.components[0].initial = vec![None];
    s.components[0].final_marking = vec![None];
    let second = sequence(&[5], &[5], 1, 0, 0, &[]).components.remove(0);
    s.components.push(second);
    s.bridges.push(vec![BigInt::from(0)]);
    assert_eq!(decide(s).0, Decision::Reachable);
}
fn problem(
    initial: Vec<u64>,
    pre: Vec<(usize, u64)>,
    post: Vec<(usize, u64)>,
    goal: Vec<i64>,
) -> Problem {
    Problem {
        places: (0..initial.len()).map(|i| format!("p{i}")).collect(),
        initial,
        transitions: vec![Transition {
            name: "t".into(),
            pre,
            post,
        }],
        target: goal
            .iter()
            .enumerate()
            .map(|(j, &b)| Constraint {
                coefficients: (0..goal.len()).map(|i| i64::from(i == j)).collect(),
                bound: b,
                equality: true,
            })
            .collect(),
    }
}
#[test]
fn read_arcs_survive_pure_effect_reduction() {
    for initial in [0, 1] {
        let p = problem(
            vec![initial, 0],
            vec![(0, 1)],
            vec![(0, 1), (1, 1)],
            vec![initial as i64, 1],
        );
        let out = complete::solve(&p, Some(Duration::from_secs(10)), Some(100000), Some(20000));
        assert_eq!(
            out.verdict,
            if initial == 0 {
                "unreachable"
            } else {
                "reachable"
            },
            "{}",
            out.reason
        );
        if initial == 1 {
            complete::check_witness(&p, &out.trace).unwrap();
        }
    }
}
#[test]
fn zero_resource_limit_never_refutes() {
    let p = problem(vec![0], vec![], vec![(0, 1)], vec![1]);
    assert_eq!(
        complete::solve(&p, Some(Duration::ZERO), Some(100), Some(100)).verdict,
        "unknown"
    );
}

#[test]
fn bounded_finite_control_differential() {
    use std::collections::HashSet;
    let mut seed = 907u64;
    let mut random = || {
        seed ^= seed << 13;
        seed ^= seed >> 7;
        seed ^= seed << 17;
        seed as usize
    };
    for case in 0..30 {
        let edges: Vec<_> = (0..4)
            .map(|_| {
                let from = random() % 2;
                let to = random() % 2;
                let place = random() % 2;
                let mut effect = vec![0i64; 2];
                effect[place] -= 1;
                effect[1 - place] += 1;
                (from, to, effect)
            })
            .collect();
        let mut closure = HashSet::from([(0, vec![2i64, 0])]);
        loop {
            let before = closure.len();
            for (q, m) in closure.clone() {
                for (a, b, e) in &edges {
                    if *a == q {
                        let next: Vec<_> = m.iter().zip(e).map(|(x, d)| x + d).collect();
                        if next.iter().all(|&x| x >= 0) {
                            closure.insert((*b, next));
                        }
                    }
                }
            }
            if closure.len() == before {
                break;
            }
        }
        for q in 0..2 {
            for x in 0..=2 {
                let goal = vec![x, 2 - x];
                let expected = closure.contains(&(q, goal.clone()));
                let (actual, stats) = decide(sequence(&[2, 0], &goal, 2, 0, q, &edges));
                assert_eq!(
                    actual,
                    if expected {
                        Decision::Reachable
                    } else {
                        Decision::Unreachable
                    },
                    "case {case} goal {q:?}/{goal:?} edges {edges:?} stats {stats:?}"
                );
            }
        }
    }
}
#[test]
fn signed_linear_target_conjunctions() {
    for a in -1..=1 {
        for b in -1..=1 {
            for bound in -1..=2 {
                let mut p = problem(vec![2, 0], vec![(0, 1)], vec![(1, 1)], vec![0, 0]);
                p.target = vec![
                    Constraint {
                        coefficients: vec![a, b],
                        bound,
                        equality: true,
                    },
                    Constraint {
                        coefficients: vec![0, 1],
                        bound: 1,
                        equality: false,
                    },
                ];
                let expected = (0..=2).any(|x| a * (2 - x) + b * x == bound && x >= 1);
                let (actual, stats) = decide(complete::from_problem(&p));
                assert_eq!(
                    actual,
                    if expected {
                        Decision::Reachable
                    } else {
                        Decision::Unreachable
                    },
                    "{a},{b},{bound}: {stats:?}"
                );
            }
        }
    }
}
#[test]
fn arbitrary_precision_witness_replay() {
    let mut p = problem(vec![u64::MAX, 0], vec![], vec![(0, 1), (1, 1)], vec![0, 1]);
    p.target.remove(0);
    let m = complete::check_witness(&p, &[0]).unwrap();
    assert_eq!(m[0], BigInt::from(u64::MAX) + 1);
}

#[test]
fn backward_pumping_failure_is_checked() {
    let (d, s) = decide(sequence(
        &[2, 2],
        &[0, 0],
        1,
        0,
        0,
        &[
            (0, 0, vec![2, -1]),
            (0, 0, vec![-1, 2]),
            (0, 0, vec![-2, 1]),
            (0, 0, vec![1, -2]),
        ],
    ));
    assert_eq!(d, Decision::Unreachable, "{s:?}");
    assert!(s.counter_refinements > 0);
}
#[test]
fn bounded_counter_adjustment_preserves_following_bridge() {
    let mut first = sequence(
        &[2, 0],
        &[1, 1],
        1,
        0,
        0,
        &[(0, 0, vec![-1, 1]), (0, 0, vec![1, -1])],
    );
    first.components.push(
        sequence(&[0, 2], &[0, 2], 1, 0, 0, &[])
            .components
            .remove(0),
    );
    first.bridges.push(vec![(-1).into(), 1.into()]);
    let (d, s) = decide(first);
    assert_eq!(d, Decision::Reachable, "{s:?}");
    assert!(s.counter_refinements > 0);
}
#[test]
fn unlimited_mode_has_no_iteration_or_counter_cutoff() {
    let p = problem(vec![0], vec![], vec![(0, 2)], vec![3]);
    let out = complete::solve(&p, None, None, None);
    assert_eq!(out.verdict, "unreachable", "{}", out.reason);
    let p = problem(vec![0], vec![], vec![(0, 2)], vec![6]);
    let out = complete::solve(&p, None, None, None);
    assert_eq!(out.verdict, "reachable", "{}", out.reason);
    complete::check_witness(&p, &out.trace).unwrap();
}

#[test]
fn actual_run_can_omit_an_scc_edge() {
    let (d, s) = decide(sequence(&[0], &[0], 1, 0, 0, &[(0, 0, vec![1])]));
    assert_eq!(d, Decision::Reachable);
    assert!(s.transition_refinements > 0);
}
