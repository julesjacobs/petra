use std::time::Duration;
use vass_reach::{
    input,
    model::{Constraint, Problem, Transition},
    search, state_equation,
};
fn problem(initial: Vec<u64>, transitions: Vec<Transition>, goal: Vec<i64>) -> Problem {
    Problem {
        places: (0..initial.len()).map(|i| format!("p{i}")).collect(),
        initial,
        transitions,
        target: goal
            .iter()
            .enumerate()
            .map(|(i, &b)| {
                let mut a = vec![0; goal.len()];
                a[i] = 1;
                Constraint {
                    coefficients: a,
                    bound: b,
                    equality: true,
                }
            })
            .collect(),
    }
}
fn tr(pre: &[(usize, u64)], post: &[(usize, u64)]) -> Transition {
    Transition {
        name: "t".into(),
        pre: pre.to_vec(),
        post: post.to_vec(),
    }
}
#[test]
fn read_arc_is_not_a_zero_delta_transition() {
    let p = problem(vec![0], vec![tr(&[(0, 1)], &[(0, 1)])], vec![1]);
    assert!(p.fire(&[0], 0).unwrap().is_none());
    assert!(p.check_witness(&[0]).is_err());
    assert_eq!(
        search::solve(&p, false, Duration::from_secs(1), 100).verdict,
        "unreachable"
    );
}
#[test]
fn coverability_does_not_establish_reachability() {
    let p = problem(vec![0], vec![tr(&[], &[(0, 2)])], vec![1]);
    assert_eq!(
        search::solve(&p, false, Duration::from_secs(1), 20).verdict,
        "unknown"
    );
    assert_eq!(
        state_equation::solve(&p, Duration::from_secs(1), 100).verdict,
        "unknown"
    );
}
#[test]
fn rational_infeasibility_has_a_checked_certificate() {
    let p = problem(vec![1, 0], vec![tr(&[(0, 1)], &[(1, 1)])], vec![1, 1]);
    let out = state_equation::solve(&p, Duration::from_secs(1), 100);
    assert_eq!(out.verdict, "unreachable");
    state_equation::verify_certificate(&p, out.certificate.as_ref().unwrap()).unwrap();
    let forged = vec!["0".into(); out.certificate.unwrap().len()];
    assert!(state_equation::verify_certificate(&p, &forged).is_err());
}
#[test]
fn equality_and_self_loops_need_enabled_execution() {
    let p = problem(
        vec![0, 0],
        vec![tr(&[(0, 1)], &[(0, 1), (1, 1)])],
        vec![0, 1],
    );
    assert_eq!(
        state_equation::solve(&p, Duration::from_secs(1), 100).verdict,
        "unknown"
    );
    assert_eq!(
        search::solve(&p, false, Duration::from_secs(1), 100).verdict,
        "unreachable"
    );
}
#[test]
fn overflow_is_unknown() {
    let p = problem(vec![u64::MAX, 0], vec![tr(&[], &[(0, 1)])], vec![0, 1]);
    assert_eq!(
        search::solve(&p, false, Duration::from_secs(1), 100).verdict,
        "unknown"
    );
}
#[test]
fn empty_witness_and_weighted_arcs() {
    let p = problem(vec![2, 0], vec![tr(&[(0, 2)], &[(1, 3)])], vec![0, 3]);
    let out = search::solve(&p, true, Duration::from_secs(1), 100);
    assert_eq!(out.verdict, "reachable");
    assert_eq!(out.trace, vec![0]);
    p.check_witness(&out.trace).unwrap();
    let p = problem(vec![0], vec![], vec![0]);
    assert!(
        search::solve(&p, false, Duration::from_secs(1), 100)
            .trace
            .is_empty()
    );
}
#[test]
fn parser_preserves_negative_coefficients_and_rejects_other_logics() {
    let xml = "<property-set><property><formula><exists-path><finally><integer-ge><integer-add><integer-mul><integer-constant>-2</integer-constant><tokens-count><place>a</place></tokens-count></integer-mul><tokens-count><place>b</place></tokens-count></integer-add><integer-constant>1</integer-constant></integer-ge></finally></exists-path></formula></property></property-set>";
    let p = input::parse("net {x}\npl a (1)\ntr t a*2 -> b*3", xml).unwrap();
    assert_eq!(p.target[0].coefficients, vec![-2, 1]);
    assert!(
        input::parse(
            "net {x}\npl a (1)\ntr t a*2 -> b*3",
            &xml.replace("exists-path", "all-paths")
        )
        .is_err()
    );
    assert!(input::parse("net {x}\npl a (1)", xml).is_err());
}
#[test]
fn bounded_random_nets_agree_with_independent_closure() {
    let mut seed = 123456789u64;
    let mut random = || {
        seed ^= seed << 13;
        seed ^= seed >> 7;
        seed ^= seed << 17;
        seed as usize
    };
    for _ in 0..120 {
        let transitions: Vec<_> = (0..4)
            .map(|_| tr(&[(random() % 3, 1)], &[(random() % 3, 1)]))
            .collect();
        let mut goal = vec![0; 3];
        for _ in 0..2 {
            goal[random() % 3] += 1;
        }
        let p = problem(vec![2, 0, 0], transitions, goal.clone());
        let mut reachable = std::collections::HashSet::from([vec![2u64, 0, 0]]);
        loop {
            let before = reachable.len();
            for m in reachable.clone() {
                for t in &p.transitions {
                    let (src, w) = t.pre[0];
                    let (dst, v) = t.post[0];
                    if m[src] >= w {
                        let mut next = m.clone();
                        next[src] -= w;
                        next[dst] += v;
                        reachable.insert(next);
                    }
                }
            }
            if reachable.len() == before {
                break;
            }
        }
        let expected = reachable.contains(&goal.iter().map(|&x| x as u64).collect::<Vec<_>>());
        for best in [false, true] {
            let out = search::solve(&p, best, Duration::from_secs(1), 100);
            assert_eq!(
                out.verdict,
                if expected { "reachable" } else { "unreachable" }
            );
        }
        let accelerated = vass_reach::klmst::solve(&p, Duration::from_secs(1), 1000);
        assert_eq!(
            accelerated.verdict,
            if expected { "reachable" } else { "unreachable" }
        );
        if expected {
            p.check_witness(&accelerated.trace).unwrap();
        }
        let fm = state_equation::solve(&p, Duration::from_millis(100), 1000);
        if fm.verdict == "unreachable" {
            assert!(!expected);
            state_equation::verify_certificate(&p, fm.certificate.as_ref().unwrap()).unwrap();
        }
    }
}
