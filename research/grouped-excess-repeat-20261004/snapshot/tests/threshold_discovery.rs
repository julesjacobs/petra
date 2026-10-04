use serde_json::Value;
use std::{
    collections::{HashSet, VecDeque},
    io::Write,
    process::{Command, Stdio},
    time::{Duration, Instant},
};
use vass_reach::{
    model::{Constraint, Problem, Transition},
    search::Outcome,
    signed_threshold,
};

fn solve(p: &Problem, arity: usize) -> Outcome {
    signed_threshold::solve(p, Duration::from_secs(5), 1_000_000, arity)
}

fn check_rust(p: &Problem, certificate: &Value) {
    let certificate = serde_json::from_value(certificate.clone()).unwrap();
    signed_threshold::verify(p, &certificate, Instant::now() + Duration::from_secs(5)).unwrap();
}

fn check_python(cases: &[(Problem, Value)]) {
    let mut child = Command::new("python3")
        .args([
            "-c",
            "import json,sys;sys.path.insert(0,'scripts');from signed_threshold_checker import verify_signed_threshold\nfor p,c in json.load(sys.stdin):\n assert verify_signed_threshold(p,c)=='python-signed-threshold-invariant'",
        ])
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .stdin(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(&serde_json::to_vec(cases).unwrap())
        .unwrap();
    assert!(child.wait().unwrap().success());
}

fn transfer() -> Problem {
    Problem {
        places: vec!["x".into(), "y".into(), "unbounded".into()],
        initial: vec![2, 0, 0],
        transitions: vec![
            Transition {
                name: "move".into(),
                pre: vec![(0, 1)],
                post: vec![(1, 1)],
            },
            Transition {
                name: "return".into(),
                pre: vec![(1, 1)],
                post: vec![(0, 1)],
            },
            Transition {
                name: "weighted".into(),
                pre: vec![(0, 2)],
                post: vec![(1, 2)],
            },
            Transition {
                name: "source".into(),
                pre: vec![],
                post: vec![(2, 3)],
            },
            Transition {
                name: "read".into(),
                pre: vec![(0, 1), (1, 1)],
                post: vec![(0, 1), (1, 1)],
            },
        ],
        target: vec![
            Constraint {
                coefficients: vec![1, 0, 0],
                bound: 2,
                equality: false,
            },
            Constraint {
                coefficients: vec![0, 1, 0],
                bound: 1,
                equality: false,
            },
        ],
    }
}

#[test]
fn automatically_discovers_upper_and_lower_relations_on_weighted_unbounded_net() {
    let mut p = transfer();
    let mut cases = Vec::new();
    for lower in [false, true] {
        if lower {
            for row in &mut p.target {
                row.bound = 0;
                row.equality = true;
            }
        }
        let outcome = solve(&p, 2);
        assert_eq!(outcome.verdict, "unreachable", "{}", outcome.reason);
        let certificate = outcome.proof.unwrap();
        check_rust(&p, &certificate);
        cases.push((p.clone(), certificate));
    }
    check_python(&cases);
}

#[test]
fn unary_ablation_does_not_claim_a_relational_refutation() {
    let p = transfer();
    let binary = solve(&p, 2);
    assert_eq!(binary.verdict, "unreachable", "{}", binary.reason);
    let unary = solve(&p, 1);
    assert_eq!(unary.verdict, "unknown", "{}", unary.reason);
    let certificate = binary.proof.unwrap();
    check_rust(&p, &certificate);
    check_python(&[(p, certificate)]);
}

#[test]
fn reachable_targets_and_new_induction_breaking_transitions_are_not_refuted() {
    let mut cases = Vec::new();
    let mut p = transfer();
    p.target[0].bound = 1;
    assert!(p.check_witness(&[0]).is_ok());
    cases.push(p);
    let mut p = transfer();
    p.transitions.push(Transition {
        name: "increase".into(),
        pre: vec![],
        post: vec![(0, 1)],
    });
    assert!(p.check_witness(&[0, 5]).is_ok());
    cases.push(p);
    let mut p = transfer();
    for row in &mut p.target {
        row.bound = 0;
        row.equality = true;
    }
    p.transitions.push(Transition {
        name: "leak".into(),
        pre: vec![(0, 2)],
        post: vec![],
    });
    assert!(p.check_witness(&[5]).is_ok());
    cases.push(p);
    for p in cases {
        assert_ne!(solve(&p, 2).verdict, "unreachable");
    }
}

fn reachable_markings(p: &Problem) -> HashSet<Vec<u64>> {
    let mut seen = HashSet::from([p.initial.clone()]);
    let mut queue = VecDeque::from([p.initial.clone()]);
    while let Some(marking) = queue.pop_front() {
        for transition in &p.transitions {
            let mut pre = vec![0; p.places.len()];
            let mut post = pre.clone();
            for &(place, weight) in &transition.pre {
                pre[place] += weight;
            }
            for &(place, weight) in &transition.post {
                post[place] += weight;
            }
            if marking.iter().zip(&pre).any(|(m, required)| m < required) {
                continue;
            }
            let next: Vec<_> = marking
                .iter()
                .zip(pre.iter().zip(&post))
                .map(|(m, (consumed, produced))| m - consumed + produced)
                .collect();
            if seen.insert(next.clone()) {
                queue.push_back(next);
            }
        }
    }
    seen
}

fn accepts(p: &Problem, marking: &[u64]) -> bool {
    p.target.iter().all(|row| {
        let value: i128 = row
            .coefficients
            .iter()
            .zip(marking)
            .map(|(&coefficient, &tokens)| i128::from(coefficient) * i128::from(tokens))
            .sum();
        if row.equality {
            value == i128::from(row.bound)
        } else {
            value >= i128::from(row.bound)
        }
    })
}

#[test]
fn every_discovered_proof_is_sound_on_exhaustive_small_conservative_nets() {
    let markings: Vec<Vec<u64>> = (0..=2).map(|x| vec![x, 2 - x]).collect();
    let arcs = |x, y| {
        [(0, x), (1, y)]
            .into_iter()
            .filter(|(_, weight)| *weight > 0)
            .collect()
    };
    let mut checked = Vec::new();
    for weight in 0..=2 {
        for consumed_x in 0..=weight {
            for produced_x in 0..=weight {
                for initial in &markings {
                    let mut p = Problem {
                        places: vec!["x".into(), "y".into()],
                        initial: initial.clone(),
                        transitions: vec![Transition {
                            name: "step".into(),
                            pre: arcs(consumed_x, weight - consumed_x),
                            post: arcs(produced_x, weight - produced_x),
                        }],
                        target: vec![],
                    };
                    let reachable = reachable_markings(&p);
                    for place in 0..2 {
                        for bound in 0..=3 {
                            p.target = vec![Constraint {
                                coefficients: (0..2).map(|i| i64::from(i == place)).collect(),
                                bound,
                                equality: false,
                            }];
                            let outcome = solve(&p, 2);
                            if outcome.verdict != "unreachable" {
                                continue;
                            }
                            assert!(reachable.iter().all(|marking| !accepts(&p, marking)));
                            let certificate = outcome.proof.unwrap();
                            check_rust(&p, &certificate);
                            checked.push((p.clone(), certificate));
                        }
                    }
                }
            }
        }
    }
    assert!(!checked.is_empty());
    check_python(&checked);
}

#[test]
fn resource_exhaustion_does_not_emit_a_proof() {
    let p = transfer();
    for (timeout, work) in [(Duration::ZERO, 1_000_000), (Duration::from_secs(5), 0)] {
        let outcome = signed_threshold::solve(&p, timeout, work, 2);
        assert_eq!(outcome.verdict, "unknown");
        assert!(outcome.proof.is_none());
    }
}

#[test]
fn cli_discovers_and_rechecks_binary_proof() {
    let directory =
        std::env::temp_dir().join(format!("pvass-threshold-discovery-{}", std::process::id()));
    std::fs::create_dir(&directory).unwrap();
    let input = directory.join("input.json");
    let answer = directory.join("answer.json");
    let problem = transfer();
    std::fs::write(&input, serde_json::to_vec(&problem).unwrap()).unwrap();
    let exe = env!("CARGO_BIN_EXE_vass-reach");
    for (method, expected) in [
        ("signed-threshold", "unreachable"),
        ("signed-threshold-unary", "unknown"),
    ] {
        let result = Command::new(exe)
            .arg("--json")
            .arg(&input)
            .args([
                "--method",
                method,
                "--seconds",
                "5",
                "--max-states",
                "1000000",
            ])
            .output()
            .unwrap();
        assert!(
            result.status.success(),
            "{}",
            String::from_utf8_lossy(&result.stderr)
        );
        let decoded: Value = serde_json::from_slice(&result.stdout).unwrap();
        assert_eq!(decoded["verdict"], expected);
        if expected == "unreachable" {
            std::fs::write(&answer, &result.stdout).unwrap();
            assert!(
                Command::new(exe)
                    .arg("--json")
                    .arg(&input)
                    .arg("--verify")
                    .arg(&answer)
                    .output()
                    .unwrap()
                    .status
                    .success()
            );
            check_python(&[(problem.clone(), decoded["proof"].clone())]);
        }
    }
    std::fs::remove_dir_all(directory).unwrap();
}
