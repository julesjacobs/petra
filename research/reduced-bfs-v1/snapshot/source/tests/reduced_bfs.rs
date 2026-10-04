use serde_json::json;
use std::{fs, process::Command, time::Duration};
use vass_reach::{
    model::{Constraint, Problem, Transition},
    reduced_bfs, search,
};

#[test]
fn conservative_weighted_nets_match_direct_search() {
    let mut transitions = Vec::new();
    for weight in 0..=2 {
        for left_pre in 0..=weight {
            for left_post in 0..=weight {
                let arcs = |left| {
                    [(0, left), (1, weight - left)]
                        .into_iter()
                        .filter(|&(_, w)| w > 0)
                        .collect()
                };
                transitions.push(Transition {
                    name: "t".into(),
                    pre: arcs(left_pre),
                    post: arcs(left_post),
                });
            }
        }
    }
    for a in &transitions {
        for b in &transitions {
            for left in 0..=2 {
                for equality in [false, true] {
                    let p = Problem {
                        places: vec!["a".into(), "b".into()],
                        initial: vec![left, 2 - left],
                        transitions: vec![a.clone(), b.clone()],
                        target: vec![Constraint {
                            coefficients: vec![1, 0],
                            bound: 1,
                            equality,
                        }],
                    };
                    let expected = search::solve(&p, false, Duration::from_secs(1), 32);
                    let actual = reduced_bfs::solve(&p, Duration::from_secs(1), 32);
                    assert_eq!(actual.verdict, expected.verdict, "{p:?}");
                    assert_ne!(actual.verdict, "unknown");
                    if actual.verdict == "reachable" {
                        assert_eq!(
                            p.check_witness(&actual.trace).unwrap(),
                            actual.marking.unwrap()
                        );
                    }
                }
            }
        }
    }
}

#[test]
fn cli_lifts_witnesses_and_checks_nested_closure_proofs() {
    let folder = std::env::temp_dir().join(format!("pvass-reduced-bfs-{}", std::process::id()));
    fs::create_dir(&folder).unwrap();
    let path = folder.join("problem.json");
    let answer_path = folder.join("answer.json");
    let binary = env!("CARGO_BIN_EXE_vass-reach");
    let mut p = json!({"places":["start","buffer","end"],"initial":[2,0,0],"transitions":[{"name":"enter","pre":[[0,2]],"post":[[1,2]]},{"name":"exit","pre":[[1,2]],"post":[[2,2]]}],"target":[{"coefficients":[0,0,1],"bound":2,"equality":true}]});
    for bound in [2, 3] {
        p["target"][0]["bound"] = json!(bound);
        fs::write(&path, serde_json::to_vec(&p).unwrap()).unwrap();
        let out = Command::new(binary)
            .args([
                "--json",
                path.to_str().unwrap(),
                "--method",
                "reduced-bfs",
                "--seconds",
                "2",
            ])
            .output()
            .unwrap();
        assert!(
            out.status.success(),
            "{}",
            String::from_utf8_lossy(&out.stderr)
        );
        let answer: serde_json::Value = serde_json::from_slice(&out.stdout).unwrap();
        assert_eq!(
            answer["verdict"],
            if bound == 2 {
                "reachable"
            } else {
                "unreachable"
            }
        );
        fs::write(&answer_path, &out.stdout).unwrap();
        let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
        let checked = Command::new(root.join("vendor/venv/bin/python"))
            .arg(root.join("scripts/check_backend_answer.py"))
            .arg(&path)
            .arg(&answer_path)
            .output()
            .unwrap();
        assert!(
            checked.status.success(),
            "{}",
            String::from_utf8_lossy(&checked.stderr)
        );
        if bound == 3 {
            assert_eq!(answer["proof"]["kind"], "buffer-agglomeration-v1");
            let checked = Command::new(binary)
                .arg("--json")
                .arg(&path)
                .arg("--verify")
                .arg(&answer_path)
                .output()
                .unwrap();
            assert!(
                checked.status.success(),
                "{}",
                String::from_utf8_lossy(&checked.stderr)
            );
            for states in [0, 1, 200001] {
                let bad = json!({"verdict":"unreachable","proof":{"kind":"finite-closure-v1","states":states}});
                fs::write(&answer_path, serde_json::to_vec(&bad).unwrap()).unwrap();
                assert!(
                    !Command::new(binary)
                        .arg("--json")
                        .arg(&path)
                        .arg("--verify")
                        .arg(&answer_path)
                        .output()
                        .unwrap()
                        .status
                        .success()
                );
                assert!(
                    !Command::new(root.join("vendor/venv/bin/python"))
                        .arg(root.join("scripts/check_backend_answer.py"))
                        .arg(&path)
                        .arg(&answer_path)
                        .output()
                        .unwrap()
                        .status
                        .success()
                );
            }
        }
    }
    fs::remove_dir_all(folder).unwrap();
}

#[test]
fn exhausted_budget_is_unknown() {
    let p:Problem=serde_json::from_value(json!({"places":["p"],"initial":[0],"transitions":[{"name":"grow","pre":[],"post":[[0,1]]}],"target":[{"coefficients":[1],"bound":20,"equality":true}]})).unwrap();
    assert_eq!(
        reduced_bfs::solve(&p, Duration::ZERO, 10).verdict,
        "unknown"
    );
    assert_eq!(
        reduced_bfs::solve(&p, Duration::from_secs(1), 0).verdict,
        "unknown"
    );
    assert_eq!(
        reduced_bfs::solve(&p, Duration::from_secs(1), 10).verdict,
        "unknown"
    );
}
