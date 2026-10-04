use serde_json::{Value, json};
use std::{fs, process::Command};

#[test]
fn portfolio_lifts_both_verdicts_and_checks_original_proofs() {
    let directory =
        std::env::temp_dir().join(format!("pvass-relevance-cli-{}", std::process::id()));
    fs::create_dir(&directory).unwrap();
    let path = directory.join("query.json");
    let answer_path = directory.join("answer.json");
    for (method, reachable) in [
        "portfolio-focused",
        "portfolio-stubborn",
        "portfolio-target-stubborn",
        "finite-token-cut",
    ]
    .into_iter()
    .flat_map(|method| [false, true].map(|reachable| (method, reachable)))
    {
        let mut transitions = vec![json!({"name":"irrelevant","pre":[],"post":[[1,1]]})];
        if reachable {
            transitions.push(json!({"name":"goal","pre":[],"post":[[0,1]]}));
        }
        let query = json!({"places":["goal","junk"],"initial":[0,4],"transitions":transitions,
            "target":[{"coefficients":[1,0],"bound":1,"equality":false}]});
        fs::write(&path, query.to_string()).unwrap();
        let output = Command::new(env!("CARGO_BIN_EXE_vass-reach"))
            .arg("--json")
            .arg(&path)
            .args(["--method", method, "--seconds", "3"])
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        let answer: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(
            answer["verdict"],
            if reachable {
                "reachable"
            } else {
                "unreachable"
            }
        );
        if reachable {
            assert_eq!(answer["marking"], json!([1, 4]));
        } else {
            assert_eq!(answer["proof"]["kind"], "relevance-v1");
        }
        fs::write(&answer_path, answer.to_string()).unwrap();
        let verify = || {
            Command::new(env!("CARGO_BIN_EXE_vass-reach"))
                .arg("--json")
                .arg(&path)
                .arg("--verify")
                .arg(&answer_path)
                .args(["--seconds", "3"])
                .output()
                .unwrap()
                .status
                .success()
        };
        assert!(verify());
        if !reachable {
            let mut forged = answer;
            forged["proof"]["places"] = json!([1]);
            fs::write(&answer_path, forged.to_string()).unwrap();
            assert!(!verify());
        }
    }
    fs::remove_dir_all(directory).unwrap();
}
