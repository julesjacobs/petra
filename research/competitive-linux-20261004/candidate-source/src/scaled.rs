//! Positive search from a common divisor of the initial marking.
use crate::{model::Problem, search::Outcome};
use std::time::{Duration, Instant};

const MAX_TRACE: usize = 1_000_000;

fn gcd(mut a: u64, mut b: u64) -> u64 {
    while b != 0 {
        (a, b) = (b, a % b);
    }
    a
}

pub fn prepare(problem: &Problem) -> Option<(Problem, u64)> {
    problem.validate().ok()?;
    let mut factor = problem.initial.iter().copied().fold(0, gcd);
    for row in &problem.target {
        if row.equality {
            factor = gcd(factor, row.bound.unsigned_abs());
        }
    }
    if factor <= 1 {
        return None;
    }
    let mut reduced = problem.clone();
    for value in &mut reduced.initial {
        *value /= factor;
    }
    for row in &mut reduced.target {
        let value = i128::from(row.bound);
        let divisor = i128::from(factor);
        row.bound =
            i64::try_from(value.div_euclid(divisor) + i128::from(value.rem_euclid(divisor) != 0))
                .ok()?;
    }
    Some((reduced, factor))
}

fn lift(problem: &Problem, factor: u64, answer: Outcome, deadline: Instant) -> Outcome {
    let unknown = |reason: &str| Outcome::unknown("scaled-relaxed", reason, answer.states);
    if answer.verdict != "reachable" {
        return unknown("scaled search found no witness");
    }
    let Some(length) = u128::try_from(answer.trace.len())
        .ok()
        .and_then(|n| n.checked_mul(u128::from(factor)))
    else {
        return unknown("scaled witness length overflow");
    };
    if length > MAX_TRACE as u128 || Instant::now() >= deadline {
        return unknown("scaled witness resource limit");
    }
    let mut trace = Vec::with_capacity(length as usize);
    if !answer.trace.is_empty() {
        for _ in 0..factor {
            if Instant::now() >= deadline {
                return unknown("scaled witness deadline");
            }
            trace.extend_from_slice(&answer.trace);
        }
    }
    let Ok(marking) = problem.check_witness(&trace) else {
        return unknown("scaled original witness replay failed");
    };
    if Instant::now() >= deadline {
        return unknown("scaled original replay deadline");
    }
    let mut out = unknown("repeated scaled witness replayed on original net");
    out.verdict = "reachable";
    out.marking = Some(marking);
    out.trace = trace;
    out
}

pub fn solve(problem: &Problem, timeout: Duration, max_states: usize) -> Outcome {
    solve_with(problem, timeout, |reduced, budget| {
        crate::relaxed::solve_batched(reduced, budget, max_states)
    })
}

pub fn solve_guided(
    problem: &Problem,
    timeout: Duration,
    max_states: usize,
    options: crate::walk::Options,
) -> Outcome {
    let mut answer = solve_with(problem, timeout, |reduced, budget| {
        crate::walk::solve_guided(reduced, budget, max_states, options)
    });
    answer.method = "scaled-walk".into();
    answer
}

fn solve_with(
    problem: &Problem,
    timeout: Duration,
    search: impl FnOnce(&Problem, Duration) -> Outcome,
) -> Outcome {
    let deadline = Instant::now() + timeout;
    let Some((reduced, factor)) = prepare(problem) else {
        return Outcome::unknown("scaled-relaxed", "no common initial divisor", 0);
    };
    let remaining = deadline.saturating_duration_since(Instant::now());
    let answer = search(&reduced, remaining * 9 / 10);
    lift(problem, factor, answer, deadline)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        model::{Constraint, Transition},
        search,
    };

    fn sample(initial: Vec<u64>, coefficients: Vec<i64>, bound: i64, equality: bool) -> Problem {
        Problem {
            places: vec!["a".into(), "b".into()],
            initial,
            transitions: vec![Transition {
                name: "move".into(),
                pre: vec![(0, 1)],
                post: vec![(1, 1)],
            }],
            target: vec![Constraint {
                coefficients,
                bound,
                equality,
            }],
        }
    }

    #[test]
    fn rounds_signed_bounds_and_respects_equalities() {
        for bound in [-9, -8, -1, 0, 1, 8, 9, i64::MIN, i64::MAX] {
            let p = sample(vec![8, 0], vec![1, -1], bound, false);
            let (q, factor) = prepare(&p).unwrap();
            assert_eq!(factor, 8);
            for value in -100i128..=100 {
                assert_eq!(
                    value * 8 >= i128::from(bound),
                    value >= i128::from(q.target[0].bound)
                );
            }
        }
        let p = sample(vec![12, 0], vec![0, 1], 8, true);
        let (q, factor) = prepare(&p).unwrap();
        assert_eq!(factor, 4);
        assert_eq!(q.initial, vec![3, 0]);
        assert_eq!(q.target[0].bound, 2);
        assert!(prepare(&sample(vec![5, 0], vec![0, 1], 2, true)).is_none());
    }

    #[test]
    fn repeated_witness_matches_direct_replay_for_signed_targets() {
        for factor in 2..=9 {
            for bound in -4..=9 {
                let p = sample(vec![factor, 0], vec![-1, 1], bound, false);
                let (q, divisor) = prepare(&p).unwrap();
                let answer = search::solve(&q, false, Duration::from_secs(1), 100);
                let reached = answer.verdict == "reachable";
                let lifted = lift(&p, divisor, answer, Instant::now() + Duration::from_secs(1));
                assert_eq!(lifted.verdict == "reachable", reached);
                if reached {
                    assert_eq!(
                        p.check_witness(&lifted.trace).unwrap(),
                        lifted.marking.unwrap()
                    );
                }
            }
        }
    }

    #[test]
    fn read_guards_and_nondivisible_arcs_are_preserved() {
        let mut p = sample(vec![8, 0], vec![0, 1], 8, false);
        p.transitions[0].pre = vec![(0, 2)];
        p.transitions[0].post = vec![(0, 1), (1, 1)];
        let answer = solve(&p, Duration::from_secs(1), 100);
        assert_eq!(answer.verdict, "unknown");
        p.transitions[0].pre = vec![(0, 1)];
        let answer = solve(&p, Duration::from_secs(1), 100);
        assert_eq!(answer.verdict, "reachable");
        assert_eq!(answer.trace.len(), 8);
        p.check_witness(&answer.trace).unwrap();
    }

    #[test]
    fn a_scaled_refutation_never_refutes_the_original() {
        let mut p = sample(vec![2, 0], vec![0, 1], 1, false);
        p.transitions[0].pre = vec![(0, 2)];
        assert_eq!(
            search::solve(&p, false, Duration::from_secs(1), 100).verdict,
            "reachable"
        );
        assert_eq!(solve(&p, Duration::from_secs(1), 100).verdict, "unknown");
    }

    #[test]
    fn guided_scaling_replays_the_expanded_word() {
        let p = sample(vec![9, 0], vec![0, 1], 9, true);
        let answer = solve_guided(
            &p,
            Duration::from_secs(1),
            100,
            crate::walk::Options::default(),
        );
        assert_eq!(answer.verdict, "reachable");
        assert_eq!(answer.method, "scaled-walk");
        assert_eq!(answer.trace, vec![0; 9]);
        assert_eq!(p.check_witness(&answer.trace).unwrap(), vec![0, 9]);
    }
}
