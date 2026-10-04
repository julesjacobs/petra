use super::*;
use crate::model::{Constraint, Transition};

fn transition(pre: &[(usize, u64)], post: &[(usize, u64)]) -> Transition {
    Transition {
        name: "t".into(),
        pre: pre.to_vec(),
        post: post.to_vec(),
    }
}

fn problem(initial: Vec<u64>, transitions: Vec<Transition>) -> Problem {
    Problem {
        places: (0..initial.len()).map(|i| format!("p{i}")).collect(),
        target: vec![Constraint {
            coefficients: vec![0; initial.len()],
            bound: 1,
            equality: false,
        }],
        initial,
        transitions,
    }
}

fn check_enabled(p: &Problem, state: &State) {
    let expected: Vec<_> = p
        .transitions
        .iter()
        .enumerate()
        .filter_map(|(t, tr)| {
            tr.pre
                .iter()
                .all(|&(place, weight)| state.marking[place] >= weight)
                .then_some(t)
        })
        .collect();
    let mut actual = state.enabled.clone();
    actual.sort_unstable();
    assert_eq!(actual, expected);
    for (t, tr) in p.transitions.iter().enumerate() {
        assert_eq!(
            state.missing[t],
            tr.pre
                .iter()
                .filter(|&&(place, weight)| state.marking[place] < weight)
                .count()
        );
        if let Some(position) = state.enabled.iter().position(|&id| id == t) {
            assert_eq!(state.position[t], position);
        } else {
            assert_eq!(state.position[t], usize::MAX);
        }
    }
}

fn fire_all_users(p: &Problem, index: &Index, state: &mut State, t: usize) {
    let next = p.fire(&state.marking, t).unwrap().unwrap();
    state.changes = state
        .marking
        .iter()
        .zip(&next)
        .enumerate()
        .filter_map(|(place, (&before, &after))| (before != after).then_some((place, after)))
        .collect();
    for i in 0..state.changes.len() {
        let (place, next) = state.changes[i];
        let previous = state.marking[place];
        state.marking[place] = next;
        for &(user, weight) in &index.users[place] {
            let before = previous < weight;
            let after = next < weight;
            if before == after {
                continue;
            }
            if after {
                if state.missing[user] == 0 {
                    state.disable(user);
                }
                state.missing[user] += 1;
            } else {
                state.missing[user] -= 1;
                if state.missing[user] == 0 {
                    state.enable(user);
                }
            }
        }
    }
}

fn assert_same_state(actual: &State, expected: &State) {
    assert_eq!(actual.marking, expected.marking);
    assert_eq!(actual.missing, expected.missing);
    assert_eq!(actual.enabled, expected.enabled);
    assert_eq!(actual.position, expected.position);
    assert_eq!(actual.changes, expected.changes);
}

#[test]
fn incremental_weighted_enabledness_matches_full_scans() {
    let deadline = Instant::now() + Duration::from_secs(30);
    for seed in 0..32 {
        let mut random = Random(seed);
        let initial = (0..5).map(|_| random.next() % 7).collect();
        let transitions = (0..12)
            .map(|_| {
                let mut pre = Vec::new();
                let mut post = Vec::new();
                for place in 0..5 {
                    let input = random.next() % 5;
                    let output = random.next() % 5;
                    if input != 0 {
                        pre.push((place, input));
                    }
                    if output != 0 {
                        post.push((place, output));
                    }
                }
                transition(&pre, &post)
            })
            .chain([transition(&[], &[(0, 1)]), transition(&[(0, 1)], &[])])
            .collect();
        let p = problem(initial, transitions);
        let index = Index::new(&p, deadline).unwrap();
        let mut state = State::new(&p, &index, deadline).unwrap();
        let mut reference = State::new(&p, &index, deadline).unwrap();
        for step in 0..200 {
            check_enabled(&p, &state);
            assert_same_state(&state, &reference);
            if state.enabled.is_empty() || step % 37 == 36 {
                state.reset(&p, &index, deadline).unwrap();
                reference.reset(&p, &index, deadline).unwrap();
                check_enabled(&p, &state);
                assert_same_state(&state, &reference);
            }
            let t = state.enabled[random.index(state.enabled.len())];
            let expected = p.fire(&state.marking, t).unwrap().unwrap();
            state.fire(&index, t, deadline).unwrap();
            fire_all_users(&p, &index, &mut reference, t);
            assert_eq!(state.marking, expected);
            assert_same_state(&state, &reference);
            check_enabled(&p, &state);
        }
    }
}

#[test]
fn skipped_guard_scans_preserve_guided_choices_and_restarts() {
    let mut p = problem(
        vec![4, 0, 1, 0],
        vec![
            transition(&[], &[(0, 1)]),
            transition(&[(0, 1)], &[]),
            transition(&[(0, 1)], &[(1, 1)]),
            transition(&[(1, 4)], &[(0, 4)]),
            transition(&[(1, 6)], &[(0, 2)]),
            transition(&[(0, 1), (2, 1)], &[(1, 1), (2, 1)]),
            transition(&[(0, 1), (1, 4)], &[(0, 2), (1, 3)]),
            transition(&[], &[(3, 1)]),
            transition(&[], &[]),
        ],
    );
    p.target = vec![
        Constraint {
            coefficients: vec![-2, 3, 0, 1],
            bound: 8,
            equality: false,
        },
        Constraint {
            coefficients: vec![1, -1, 2, 0],
            bound: 3,
            equality: true,
        },
    ];
    let deadline = Instant::now() + Duration::from_secs(30);
    let index = Index::new(&p, deadline).unwrap();
    let mut state = State::new(&p, &index, deadline).unwrap();
    let mut reference = State::new(&p, &index, deadline).unwrap();
    for t in [2, 2, 5, 2, 3, 2, 2, 2, 2, 0, 6, 2, 2, 0, 2, 4, 7, 8] {
        state.fire(&index, t, deadline).unwrap();
        fire_all_users(&p, &index, &mut reference, t);
        assert_same_state(&state, &reference);
        check_enabled(&p, &state);
    }
    for seed in 0..16 {
        state.reset(&p, &index, deadline).unwrap();
        reference.reset(&p, &index, deadline).unwrap();
        let mut guidance = Guidance::new(&index, &p.initial, deadline).unwrap();
        let mut reference_guidance = Guidance::new(&index, &p.initial, deadline).unwrap();
        let mut random = Random(seed);
        let mut reference_random = Random(seed);
        for step in 0..200 {
            if step % 37 == 36 {
                state.reset(&p, &index, deadline).unwrap();
                reference.reset(&p, &index, deadline).unwrap();
                guidance.reset(&index, &p.initial, deadline).unwrap();
                reference_guidance
                    .reset(&index, &p.initial, deadline)
                    .unwrap();
            }
            assert_same_state(&state, &reference);
            let t = guidance
                .select(&index, &state.enabled, &mut random, deadline)
                .unwrap();
            let reference_t = reference_guidance
                .select(&index, &reference.enabled, &mut reference_random, deadline)
                .unwrap();
            assert_eq!(t, reference_t);
            assert_eq!(random.0, reference_random.0);
            state.fire(&index, t, deadline).unwrap();
            fire_all_users(&p, &index, &mut reference, reference_t);
            guidance.fired(&index, t, deadline).unwrap();
            reference_guidance
                .fired(&index, reference_t, deadline)
                .unwrap();
            assert_same_state(&state, &reference);
            check_enabled(&p, &state);
        }
    }
}

#[test]
fn selfloops_sources_and_multiguard_swaps_preserve_the_enabled_set() {
    let p = problem(
        vec![4, 0],
        vec![
            transition(&[(0, 4)], &[(0, 4)]),
            transition(&[], &[(1, 2)]),
            transition(&[(0, 3), (1, 2)], &[(0, 1), (1, 1)]),
            transition(&[(0, 2), (1, 1)], &[(0, 4)]),
            transition(&[], &[]),
        ],
    );
    let deadline = Instant::now() + Duration::from_secs(10);
    let index = Index::new(&p, deadline).unwrap();
    let mut state = State::new(&p, &index, deadline).unwrap();
    for t in [0, 4, 1, 2, 3, 0] {
        state.fire(&index, t, deadline).unwrap();
        check_enabled(&p, &state);
    }
    assert_eq!(state.marking, p.initial);
}

#[test]
fn overflowing_firing_is_atomic_and_returns_unknown() {
    let p = problem(vec![1, u64::MAX], vec![transition(&[(0, 1)], &[(1, 1)])]);
    let deadline = Instant::now() + Duration::from_secs(10);
    let index = Index::new(&p, deadline).unwrap();
    let mut state = State::new(&p, &index, deadline).unwrap();
    assert_eq!(state.fire(&index, 0, deadline), Err("counter overflow"));
    assert_eq!(state.marking, p.initial);
    check_enabled(&p, &state);
    state.reset(&p, &index, deadline).unwrap();
    check_enabled(&p, &state);
    let outcome = solve(&p, Duration::from_secs(1), 10, Options::default());
    assert_eq!(outcome.verdict, "unknown");
    assert!(outcome.reason.starts_with("counter overflow"));
    assert_eq!(outcome.states, 1);
}

#[test]
fn restart_budget_is_total_and_deterministic() {
    let p = problem(vec![1], vec![transition(&[(0, 1)], &[])]);
    let options = Options {
        seed: 7,
        restart_steps: 3,
    };
    let first = solve(&p, Duration::from_secs(3), 23, options);
    let second = solve(&p, Duration::from_secs(3), 23, options);
    assert_eq!(first.verdict, "unknown");
    assert_eq!(first.states, 23);
    assert_eq!(first.reason, second.reason);
    assert!(first.reason.contains("seed=7; restart_steps=3"));
    assert!(first.reason.contains("restarts=22"));
    let no_progress = problem(vec![0], vec![transition(&[], &[])]);
    let bounded = solve(&no_progress, Duration::from_secs(3), 23, options);
    assert_eq!(bounded.states, 23);
    assert!(bounded.reason.contains("restarts=7"));
}

#[test]
fn seeded_walk_replays_witness_and_restarts_discard_old_prefixes() {
    let mut p = problem(
        vec![1, 0, 0],
        vec![
            transition(&[(0, 1)], &[(1, 1)]),
            transition(&[(0, 1)], &[(2, 1)]),
        ],
    );
    p.target[0].coefficients[2] = 1;
    let seed = (0..100)
        .find(|&seed| {
            let mut random = Random(seed);
            random.index(2) == 0 && random.index(2) == 1
        })
        .unwrap();
    let options = Options {
        seed,
        restart_steps: 4,
    };
    let first = solve(&p, Duration::from_secs(3), 100, options);
    let second = solve(&p, Duration::from_secs(3), 100, options);
    assert_eq!(first.verdict, "reachable");
    assert_eq!(first.trace, vec![1]);
    assert_eq!(first.states, 2);
    assert!(first.reason.contains("restarts=1"));
    assert_eq!(
        first.marking.unwrap(),
        p.check_witness(&first.trace).unwrap()
    );
    assert_eq!(first.trace, second.trace);
    assert_eq!(first.reason, second.reason);
    assert_eq!(first.states, second.states);
}

#[test]
fn limits_deadlocks_and_bad_inputs_never_refute() {
    let p = problem(vec![0], vec![transition(&[(0, 1)], &[])]);
    let answer = solve(&p, Duration::from_secs(1), 100, Options::default());
    assert_eq!(answer.verdict, "unknown");
    assert!(answer.reason.starts_with("initial deadlock"));
    assert_eq!(answer.states, 0);
    for (timeout, steps, options) in [
        (Duration::ZERO, 100, Options::default()),
        (Duration::from_secs(1), 0, Options::default()),
        (
            Duration::from_secs(1),
            10,
            Options {
                seed: 0,
                restart_steps: 0,
            },
        ),
    ] {
        assert_eq!(solve(&p, timeout, steps, options).verdict, "unknown");
    }
    let mut malformed = p.clone();
    malformed.transitions[0].pre.push((0, 1));
    assert_eq!(
        solve(&malformed, Duration::from_secs(1), 10, Options::default()).verdict,
        "unknown"
    );
}

#[test]
fn trace_cap_is_independent_of_requested_restart_and_total_steps() {
    let p = problem(vec![0], vec![transition(&[], &[])]);
    let answer = solve(
        &p,
        Duration::from_secs(10),
        MAX_TRACE_STEPS + 1,
        Options {
            seed: 0,
            restart_steps: usize::MAX,
        },
    );
    assert_eq!(answer.verdict, "unknown");
    assert_eq!(answer.states, MAX_TRACE_STEPS + 1);
    assert!(answer.reason.contains("restarts=1"));
}

#[test]
fn initial_witness_and_mixed_sign_goal_are_replayed() {
    let mut p = problem(
        vec![u64::MAX - 2, u64::MAX],
        vec![transition(&[], &[(0, 1)])],
    );
    p.target[0] = Constraint {
        coefficients: vec![1, -1],
        bound: 0,
        equality: true,
    };
    let answer = solve(&p, Duration::from_secs(1), 2, Options::default());
    assert_eq!(answer.verdict, "reachable");
    assert_eq!(answer.trace, vec![0, 0]);
    assert_eq!(
        answer.marking.unwrap(),
        p.check_witness(&answer.trace).unwrap()
    );
    p.initial[0] = u64::MAX;
    let answer = solve(&p, Duration::from_secs(1), 0, Options::default());
    assert_eq!(answer.verdict, "reachable");
    assert!(answer.trace.is_empty());
}

#[test]
fn target_overflow_and_expired_replay_never_report_a_witness() {
    let mut p = problem(vec![u64::MAX; 3], Vec::new());
    p.target[0].coefficients = vec![i64::MAX; 3];
    let answer = solve(&p, Duration::from_secs(1), 5, Options::default());
    assert_eq!(answer.verdict, "unknown");
    assert!(answer.reason.contains("target arithmetic overflow"));
    p.target.clear();
    let run = Run {
        policy: Policy::Uniform,
        options: Options::default(),
        steps: 0,
        restarts: 0,
    };
    let answer = run.witness(&p, Vec::new(), Instant::now());
    assert_eq!(answer.verdict, "unknown");
    assert!(answer.reason.contains("time limit before witness replay"));
}

#[test]
fn incremental_target_control_preserves_uniform_walk_traces_and_budgets() {
    let mut p = problem(
        vec![0, 0],
        vec![
            transition(&[], &[(0, 2)]),
            transition(&[(0, 1)], &[(1, 1)]),
            transition(&[(1, 2)], &[]),
        ],
    );
    p.target = vec![Constraint {
        coefficients: vec![1, -2],
        bound: 9,
        equality: true,
    }];
    for seed in 0..16 {
        let options = Options {
            seed,
            restart_steps: 17,
        };
        let uniform = solve(&p, Duration::from_secs(3), 100, options);
        let incremental = solve_incremental(&p, Duration::from_secs(3), 100, options);
        assert_eq!(uniform.verdict, incremental.verdict);
        assert_eq!(uniform.trace, incremental.trace);
        assert_eq!(uniform.marking, incremental.marking);
        assert_eq!(uniform.states, incremental.states);
    }
}

#[test]
fn guided_walk_never_turns_search_limits_or_overflow_into_refutations() {
    for p in [
        problem(vec![0], vec![transition(&[(0, 1)], &[])]),
        problem(vec![0], vec![transition(&[], &[])]),
        problem(vec![u64::MAX], vec![transition(&[], &[(0, 1)])]),
    ] {
        let out = solve_guided(
            &p,
            Duration::from_secs(2),
            31,
            Options {
                seed: 5,
                restart_steps: 7,
            },
        );
        assert_eq!(out.verdict, "unknown");
        assert!(out.states <= 31);
    }
    let p = problem(vec![0], vec![transition(&[], &[(0, 1)])]);
    assert_eq!(
        solve_guided(&p, Duration::ZERO, 100, Options::default()).verdict,
        "unknown"
    );
}
