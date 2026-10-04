use std::process::Command;

#[test]
fn cli_relevance_wrapper_replays_witnesses_and_checks_lazy_proofs() {
    let root = std::env::temp_dir().join(format!(
        "lazy-token-cut-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir(&root).unwrap();
    let input = root.join("input.json");
    let answer = root.join("answer.json");
    for (target, verdict) in [(1, "unreachable"), (0, "reachable")] {
        let problem = serde_json::json!({
            "places":["x","y"],"initial":[2,0],
            "transitions":[
                {"name":"forward","pre":[[0,2]],"post":[[1,2]]},
                {"name":"back","pre":[[1,2]],"post":[[0,2]]},
                {"name":"read","pre":[[0,2]],"post":[[0,2]]}],
            "target":[{"coefficients":[1,0],"bound":target,"equality":true}]
        });
        std::fs::write(&input, serde_json::to_vec(&problem).unwrap()).unwrap();
        let run = Command::new(env!("CARGO_BIN_EXE_vass-reach"))
            .args([
                "--method",
                "lazy-finite-token-cut",
                "--seconds",
                "5",
                "--json",
            ])
            .arg(&input)
            .output()
            .unwrap();
        assert!(
            run.status.success(),
            "{}",
            String::from_utf8_lossy(&run.stderr)
        );
        let parsed: serde_json::Value = serde_json::from_slice(&run.stdout).unwrap();
        assert_eq!(parsed["verdict"], verdict, "{parsed}");
        if verdict == "unreachable" {
            assert_eq!(parsed["proof"]["kind"], "relevance-v1");
            assert_eq!(parsed["proof"]["inner"]["kind"], "lazy-finite-token-cut-v1");
        } else {
            assert!(!parsed["trace"].as_array().unwrap().is_empty());
        }
        std::fs::write(&answer, &run.stdout).unwrap();
        let verify = Command::new(env!("CARGO_BIN_EXE_vass-reach"))
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
    }
    std::fs::remove_dir_all(root).unwrap();
}
