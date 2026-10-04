use std::time::Duration;
use vass_reach::{
    guided,
    model::{Constraint, Problem, Transition},
    search,
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
fn eq(coefficients: Vec<i64>, bound: i64) -> Constraint {
    Constraint {
        coefficients,
        bound,
        equality: true,
    }
}
fn check(p: &Problem, expected: &str) {
    let out = guided::solve(p, Duration::from_secs(1), 100_000);
    assert_eq!(out.verdict, expected, "{}", out.reason);
    if expected == "reachable" {
        assert_eq!(p.check_witness(&out.trace).unwrap(), out.marking.unwrap())
    }
}
#[test]
fn read_arcs_and_signed_targets() {
    let p = net(
        vec![1, 0],
        vec![(vec![(0, 2)], vec![(0, 2), (1, 1)])],
        vec![eq(vec![0, 1], 1)],
    );
    check(&p, "unreachable");
    let p = net(
        vec![2, 0],
        p.transitions.into_iter().map(|t| (t.pre, t.post)).collect(),
        vec![eq(vec![1, -1], -3)],
    );
    check(&p, "reachable");
}
#[test]
fn cleanup_requires_temporary_regression() {
    let p = net(
        vec![1, 0, 0],
        vec![(vec![(0, 1)], vec![(1, 7)]), (vec![(1, 7)], vec![(2, 1)])],
        vec![eq(vec![1, 1, 0], 0), eq(vec![0, 0, 1], 1)],
    );
    check(&p, "reachable");
}
#[test]
fn resource_limits_and_overflow_are_unknown() {
    let p = net(vec![0], vec![(vec![], vec![(0, 2)])], vec![eq(vec![1], 3)]);
    assert_eq!(
        guided::solve(&p, Duration::from_secs(1), 5).verdict,
        "unknown"
    );
    assert_eq!(guided::solve(&p, Duration::ZERO, 100).verdict, "unknown");
    let p = net(
        vec![u64::MAX],
        vec![(vec![], vec![(0, 1)])],
        vec![eq(vec![1], 1)],
    );
    assert_eq!(
        guided::solve(&p, Duration::from_secs(1), 100).verdict,
        "unknown"
    );
}
#[test]
fn constant_false_target_and_empty_trace() {
    check(&net(vec![0], vec![], vec![eq(vec![0], 1)]), "unreachable");
    check(&net(vec![0], vec![], vec![eq(vec![0], 0)]), "reachable");
}
#[test]
fn bounded_differential() {
    let mut seed = 331u64;
    for _ in 0..120 {
        let mut next = || {
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            seed >> 32
        };
        let n = 4;
        let mut arcs = vec![];
        for _ in 0..8 {
            let a = next() as usize % n;
            let b = next() as usize % n;
            let w = next() % 3 + 1;
            arcs.push((vec![(a, w)], vec![(b, w)]))
        }
        let target = vec![
            eq(vec![1, -1, 0, 0], next() as i64 % 13 - 6),
            eq(vec![0, 0, 1, 0], (next() % 7) as i64),
        ];
        let p = net(vec![6, 0, 0, 0], arcs, target);
        let bfs = search::solve(&p, false, Duration::from_secs(1), 100_000);
        let out = guided::solve(&p, Duration::from_secs(1), 100_000);
        assert_eq!(out.verdict, bfs.verdict);
        assert_ne!(out.verdict, "unknown");
        if out.verdict == "reachable" {
            p.check_witness(&out.trace).unwrap();
        }
    }
}

#[test]
fn quotient_and_caps_only_return_replayed_positives() {
    let p = net(
        vec![1, 0, 0],
        vec![
            (vec![(0, 1)], vec![(0, 1), (1, 1)]),
            (vec![(0, 1)], vec![(0, 1), (2, 1)]),
        ],
        vec![eq(vec![0, 1, -1], 2)],
    );
    for out in [
        guided::solve_quotient(&p, Duration::from_secs(1), 1000),
        guided::solve_bounded(&p, Duration::from_secs(1), 1000),
    ] {
        assert_eq!(out.verdict, "reachable");
        p.check_witness(&out.trace).unwrap();
    }
    let blocked = net(vec![1, 0], vec![], vec![eq(vec![0, 1], 1)]);
    assert_eq!(
        guided::solve_bounded(&blocked, Duration::from_secs(1), 1000).verdict,
        "unknown"
    );
    assert_eq!(
        guided::solve_quotient(&blocked, Duration::from_secs(1), 1000).verdict,
        "unknown"
    );
}
