use std::time::Duration;
use vass_reach::{
    model::{Constraint, Problem, Transition},
    relaxed, search,
};

type Arcs = Vec<(Vec<(usize, u64)>, Vec<(usize, u64)>)>;
fn net(initial: Vec<u64>, arcs: Arcs, target: Vec<Constraint>) -> Problem {
    Problem {
        places: (0..initial.len()).map(|i| format!("p{i}")).collect(),
        initial,
        transitions: arcs
            .into_iter()
            .enumerate()
            .map(|(i, (pre, post))| Transition {
                name: format!("t{i}"),
                pre,
                post,
            })
            .collect(),
        target,
    }
}
fn goal(coefficients: Vec<i64>, bound: i64, equality: bool) -> Constraint {
    Constraint {
        coefficients,
        bound,
        equality,
    }
}
fn variants(p: &Problem, timeout: Duration, max_states: usize) -> [search::Outcome; 4] {
    [
        relaxed::solve(p, timeout, max_states),
        relaxed::solve_focused(p, timeout, max_states),
        relaxed::solve_stubborn(p, timeout, max_states),
        relaxed::solve_target_stubborn(p, timeout, max_states),
    ]
}
fn reachable(p: &Problem) {
    for result in variants(p, Duration::from_secs(2), 20_000) {
        assert_eq!(
            result.verdict, "reachable",
            "{}: {}",
            result.method, result.reason
        );
        assert_eq!(
            p.check_witness(&result.trace).unwrap(),
            result.marking.unwrap()
        );
    }
}
fn unknown(p: &Problem, timeout: Duration, max_states: usize) {
    for result in variants(p, timeout, max_states) {
        assert_eq!(
            result.verdict, "unknown",
            "{}: {}",
            result.method, result.reason
        );
    }
}

#[test]
fn weighted_prerequisites_and_read_arcs() {
    reachable(&net(
        vec![1, 0, 0],
        vec![
            (vec![(0, 1)], vec![(0, 1), (1, 2)]),
            (vec![(0, 1), (1, 7)], vec![(0, 1), (2, 1)]),
        ],
        vec![goal(vec![0, 0, 1], 1, false)],
    ));
    let blocked = net(
        vec![1, 0],
        vec![(vec![(0, 2)], vec![(0, 2), (1, 1)])],
        vec![goal(vec![0, 1], 1, false)],
    );
    unknown(&blocked, Duration::from_secs(1), 100);
}

#[test]
fn regression_through_guard_chain_avoids_target_plateau() {
    let chain = 20;
    let distractions = 8;
    let mut initial = vec![0; chain + distractions + 1];
    initial[0] = 1;
    let mut arcs: Arcs = (0..distractions)
        .map(|i| (vec![], vec![(chain + 1 + i, 1)]))
        .collect();
    arcs.extend((0..chain).map(|i| (vec![(i, 1)], vec![(i + 1, 1)])));
    let mut coefficients = vec![0; initial.len()];
    coefficients[chain] = 1;
    let p = net(initial, arcs, vec![goal(coefficients, 1, false)]);
    let result = relaxed::solve(&p, Duration::from_secs(2), 500);
    assert_eq!(
        result.verdict, "reachable",
        "{}: {}",
        result.reason, result.states
    );
    p.check_witness(&result.trace).unwrap();
}

#[test]
fn backward_relevance_avoids_distractions_under_tight_state_budget() {
    let chain = 20;
    let distractions = 128;
    let mut initial = vec![0; chain + distractions + 1];
    initial[0] = 1;
    let mut arcs: Arcs = (0..distractions)
        .map(|i| (vec![], vec![(chain + 1 + i, 1)]))
        .collect();
    arcs.extend((0..chain).map(|i| (vec![(i, 1)], vec![(i + 1, 1)])));
    let mut coefficients = vec![0; initial.len()];
    coefficients[chain] = 1;
    let p = net(initial, arcs, vec![goal(coefficients, 1, true)]);
    let cap = chain + 1;
    let unfocused = relaxed::solve(&p, Duration::from_secs(2), cap);
    assert_eq!(unfocused.verdict, "reachable", "{}", unfocused.reason);
    p.check_witness(&unfocused.trace).unwrap();
    let focused = relaxed::solve_focused(&p, Duration::from_secs(2), cap);
    assert_eq!(focused.verdict, "reachable", "{}", focused.reason);
    assert_eq!(focused.method, "relaxed-focused");
    assert!(focused.states <= cap);
    assert_eq!(
        focused.trace,
        (distractions..distractions + chain).collect::<Vec<_>>()
    );
    assert_eq!(
        p.check_witness(&focused.trace).unwrap(),
        focused.marking.unwrap()
    );
}

#[test]
fn focused_search_falls_back_after_greedy_resource_conflict() {
    let p = net(
        vec![1, 0, 0, 0],
        vec![
            (vec![(0, 1)], vec![(1, 1)]),
            (vec![(0, 1)], vec![(2, 1)]),
            (vec![(0, 1)], vec![(3, 1)]),
            (vec![(3, 1)], vec![(1, 1), (2, 1)]),
        ],
        vec![
            goal(vec![0, 1, 0, 0], 1, true),
            goal(vec![0, 0, 1, 0], 1, true),
        ],
    );
    for result in variants(&p, Duration::from_secs(2), 100) {
        assert_eq!(
            result.verdict, "reachable",
            "{}: {}",
            result.method, result.reason
        );
        assert_eq!(result.trace, vec![2, 3]);
        assert_eq!(
            p.check_witness(&result.trace).unwrap(),
            result.marking.unwrap()
        );
    }
}

#[test]
fn mixed_sign_and_cleanup_goals() {
    reachable(&net(
        vec![1, 0, 0],
        vec![(vec![(0, 1)], vec![(1, 7)]), (vec![(1, 7)], vec![(2, 1)])],
        vec![goal(vec![1, 1, 0], 0, true), goal(vec![0, 0, 1], 1, true)],
    ));
    reachable(&net(
        vec![2, 0],
        vec![(vec![(0, 2)], vec![(0, 2), (1, 1)])],
        vec![goal(vec![1, -1], -3, true)],
    ));
}

#[test]
fn relaxed_resource_reuse_does_not_report_a_false_witness() {
    let p = net(
        vec![1, 0, 0],
        vec![(vec![(0, 1)], vec![(1, 1)]), (vec![(0, 1)], vec![(2, 1)])],
        vec![goal(vec![0, 1, 0], 1, false), goal(vec![0, 0, 1], 1, false)],
    );
    unknown(&p, Duration::from_secs(1), 100);
}

#[test]
fn exact_sparse_markings_preserve_large_counters_and_zero_removal() {
    let mut initial = vec![0; 4096];
    initial[2] = u64::MAX;
    let mut coefficients = vec![0; 4096];
    coefficients[4095] = 1;
    reachable(&net(
        initial,
        vec![(vec![(2, u64::MAX)], vec![(4095, 1)])],
        vec![goal(coefficients, 1, true)],
    ));
}

#[test]
fn limits_overflows_invalid_models_and_empty_witness() {
    let p = net(
        vec![0],
        vec![(vec![], vec![(0, 2)])],
        vec![goal(vec![1], 3, true)],
    );
    unknown(&p, Duration::ZERO, 100);
    unknown(&p, Duration::from_secs(1), 4);
    let p = net(
        vec![u64::MAX],
        vec![(vec![], vec![(0, 1)])],
        vec![goal(vec![1], 1, true)],
    );
    unknown(&p, Duration::from_secs(1), 100);
    let p = net(
        vec![0],
        vec![(vec![(3, 1)], vec![])],
        vec![goal(vec![1], 1, false)],
    );
    unknown(&p, Duration::from_secs(1), 100);
    reachable(&net(vec![0], vec![], vec![goal(vec![0], 0, true)]));
}

#[test]
fn bounded_differential_against_exhaustive_search() {
    let mut seed = 671u64;
    for _ in 0..80 {
        let mut next = || {
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            seed >> 32
        };
        let arcs = (0..8)
            .map(|_| {
                let source = next() as usize % 4;
                let destination = next() as usize % 4;
                let weight = next() % 3 + 1;
                (vec![(source, weight)], vec![(destination, weight)])
            })
            .collect();
        let p = net(
            vec![6, 0, 0, 0],
            arcs,
            vec![
                goal(vec![1, -1, 0, 0], next() as i64 % 13 - 6, true),
                goal(vec![0, 0, 1, 0], (next() % 7) as i64, true),
            ],
        );
        let baseline = search::solve(&p, false, Duration::from_secs(1), 10_000);
        assert_ne!(baseline.verdict, "unknown");
        for result in variants(&p, Duration::from_secs(1), 10_000) {
            if baseline.verdict == "reachable" {
                assert_eq!(
                    result.verdict, "reachable",
                    "{}: {}",
                    result.method, result.reason
                );
                assert_eq!(
                    p.check_witness(&result.trace).unwrap(),
                    result.marking.unwrap()
                );
            } else {
                assert_eq!(
                    result.verdict, "unknown",
                    "{}: {}",
                    result.method, result.reason
                );
            }
        }
    }
}

#[test]
fn relevance_retains_weighted_read_guard_producers_and_cleanup() {
    let p = net(
        vec![0, 1, 0, 0, 0],
        vec![
            (vec![], vec![(4, 1)]),
            (vec![(1, 1)], vec![(1, 1), (2, 2)]),
            (vec![(2, 5)], vec![(2, 5), (3, 1)]),
            (vec![(3, 1)], vec![(0, 1)]),
            (vec![(1, 1)], vec![]),
        ],
        vec![goal(vec![1, -1, 0, 0, 0], 2, true)],
    );
    for result in variants(&p, Duration::from_secs(2), 10000) {
        assert_eq!(result.verdict, "reachable", "{}", result.reason);
        assert!(result.trace.iter().all(|&t| t != 0));
        assert!(result.trace.contains(&1));
        assert!(result.trace.contains(&2));
        assert!(result.trace.contains(&3));
        p.check_witness(&result.trace).unwrap();
    }
}

#[test]
fn relevance_preserves_enabledness_when_discarding_guard_consumers() {
    let p = net(
        vec![2, 0, 0],
        vec![
            (vec![(0, 1)], vec![(2, 1)]),
            (vec![(0, 2)], vec![(0, 2), (1, 1)]),
        ],
        vec![goal(vec![0, 1, 0], 2, true)],
    );
    for result in variants(&p, Duration::from_secs(1), 3) {
        assert_eq!(result.verdict, "reachable", "{}", result.reason);
        assert_eq!(result.trace, vec![1, 1]);
        p.check_witness(&result.trace).unwrap();
    }
}

#[test]
fn projected_search_replays_outputs_and_initial_tokens_outside_the_slice() {
    let p = net(
        vec![0, 1, 0, 123],
        vec![(vec![(1, 1)], vec![(0, 1), (1, 1), (2, 7)])],
        vec![goal(vec![1, 0, 0, 0], 2, true)],
    );
    for result in variants(&p, Duration::from_secs(1), 3) {
        assert_eq!(result.verdict, "reachable", "{}", result.reason);
        assert_eq!(result.trace, vec![0, 0]);
        assert_eq!(result.marking, Some(vec![2, 1, 14, 123]));
        assert_eq!(
            p.check_witness(&result.trace).unwrap(),
            result.marking.unwrap()
        );
    }
}

#[test]
fn profiling_emits_one_record_per_attempt_even_when_unknown() {
    let path =
        std::env::temp_dir().join(format!("pvass-relaxed-profile-{}.json", std::process::id()));
    let p = net(
        vec![1, 0, 0],
        vec![(vec![(0, 1)], vec![(1, 1)]), (vec![(0, 1)], vec![(2, 1)])],
        vec![goal(vec![0, 1, 0], 1, false), goal(vec![0, 0, 1], 1, false)],
    );
    std::fs::write(&path, serde_json::to_vec(&p).unwrap()).unwrap();
    for method in [
        "relaxed-focused",
        "relaxed-stubborn",
        "relaxed-target-stubborn",
    ] {
        let output = std::process::Command::new(env!("CARGO_BIN_EXE_vass-reach"))
            .arg("--json")
            .arg(&path)
            .args(["--method", method, "--seconds", "1", "--max-states", "100"])
            .env_remove("VASS_PORTFOLIO_PROFILE")
            .env("VASS_RELAXED_PROFILE", "1")
            .output()
            .unwrap();
        assert!(output.status.success());
        let answer: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(answer["verdict"], "unknown");
        let stderr = String::from_utf8(output.stderr).unwrap();
        let events: Vec<serde_json::Value> = stderr
            .lines()
            .map(|line| serde_json::from_str(line).unwrap())
            .collect();
        assert_eq!(events.len(), 2);
        for (attempt, event) in events.iter().enumerate() {
            assert_eq!(event["event"], "relaxed-search");
            let stats = &event["stats"];
            assert_eq!(stats["focused"], attempt == 0);
            assert_eq!(
                stats["stubborn"],
                attempt == 1 && method != "relaxed-focused"
            );
            assert_eq!(
                stats["target_directed"],
                attempt == 1 && method == "relaxed-target-stubborn"
            );
            assert_eq!(stats["expanded"], 3);
            assert_eq!(stats["generated"], 2);
            assert_eq!(stats["chosen"], 2);
            assert_eq!(stats["enabled_considered"], 2);
            let target_attempt = attempt == 1 && method == "relaxed-target-stubborn";
            let limit_total: u64 = [
                "target_limit_evaluation",
                "target_limit_directions",
                "target_limit_seeds",
                "target_limit_closure",
            ]
            .iter()
            .map(|key| stats[key].as_u64().unwrap())
            .sum();
            assert_eq!(limit_total, 0);
            assert_eq!(
                stats["target_early_all_enabled"],
                if target_attempt { 3 } else { 0 }
            );
            assert_eq!(stats["target_repeated_lists_avoided"], 0);
        }
    }
    std::fs::remove_file(path).unwrap();
}
