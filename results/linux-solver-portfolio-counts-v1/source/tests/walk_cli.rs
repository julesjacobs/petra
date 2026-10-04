use serde_json::{Value, json};
use std::{
    fs,
    path::PathBuf,
    process::Command,
    sync::atomic::{AtomicUsize, Ordering},
};

struct Fixture(PathBuf);

impl Fixture {
    fn new() -> Self {
        static NEXT: AtomicUsize = AtomicUsize::new(0);
        let directory = std::env::temp_dir().join(format!(
            "pvass-walk-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&directory).unwrap();
        fs::write(
            directory.join("problem.json"),
            serde_json::to_vec(&json!({
                "places":["p"], "initial":[0],
                "target":[{"coefficients":[1],"bound":3,"equality":true}],
                "transitions":[{"name":"produce","pre":[],"post":[[0,1]]}]
            }))
            .unwrap(),
        )
        .unwrap();
        Self(directory)
    }

    fn command(&self) -> Command {
        self.command_for("walk")
    }

    fn command_for(&self, method: &str) -> Command {
        let mut command = Command::new(env!("CARGO_BIN_EXE_vass-reach"));
        command
            .arg("--json")
            .arg(self.0.join("problem.json"))
            .args(["--method", method, "--seconds", "3"]);
        command
    }

    fn solve(&self, extra: &[&str]) -> Value {
        let output = self.command().args(extra).output().unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        serde_json::from_slice(&output.stdout).unwrap()
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        fs::remove_dir_all(&self.0).unwrap();
    }
}

#[test]
fn walk_cli_records_seed_and_restart_policy_and_emits_replayable_trace() {
    let fixture = Fixture::new();
    let answer = fixture.solve(&[
        "--walk-seed",
        "19",
        "--walk-restart-steps",
        "4",
        "--max-states",
        "3",
    ]);
    assert_eq!(answer["verdict"], "reachable");
    assert_eq!(answer["method"], "walk");
    assert_eq!(answer["trace"], json!([0, 0, 0]));
    assert!(
        answer["reason"]
            .as_str()
            .unwrap()
            .contains("seed=19; restart_steps=4")
    );
    let p: vass_reach::model::Problem =
        serde_json::from_slice(&fs::read(fixture.0.join("problem.json")).unwrap()).unwrap();
    assert_eq!(p.check_witness(&[0, 0, 0]).unwrap(), vec![3]);
}

#[test]
fn walk_cli_step_budget_covers_all_restarts() {
    let fixture = Fixture::new();
    let answer = fixture.solve(&["--walk-restart-steps", "2", "--max-states", "7"]);
    assert_eq!(answer["verdict"], "unknown");
    assert_eq!(answer["states"], 7);
    assert!(answer["reason"].as_str().unwrap().contains("restarts=3"));
}

#[test]
fn walk_cli_rejects_zero_restart_steps() {
    let fixture = Fixture::new();
    let output = fixture
        .command()
        .args(["--walk-restart-steps", "0"])
        .output()
        .unwrap();
    assert!(!output.status.success());
    assert!(
        String::from_utf8_lossy(&output.stderr).contains("--walk-restart-steps must be positive")
    );
}

#[test]
fn portfolio_walk_uses_a_replayed_positive_warmup() {
    for method in ["portfolio-walk", "portfolio-walk-counts"] {
        let fixture = Fixture::new();
        let output = fixture.command_for(method).output().unwrap();
        assert!(output.status.success());
        let answer: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(answer["verdict"], "reachable");
        assert_eq!(answer["method"], "walk");
        assert_eq!(answer["trace"], json!([0, 0, 0]));
    }
}

#[test]
fn portfolio_walk_counts_realizes_a_trace_beyond_walk_restarts_and_fixed_count_cap() {
    let fixture = Fixture::new();
    let path = fixture.0.join("problem.json");
    let mut problem: Value = serde_json::from_slice(&fs::read(&path).unwrap()).unwrap();
    problem["target"][0]["bound"] = json!(9000);
    fs::write(&path, serde_json::to_vec(&problem).unwrap()).unwrap();
    let output = fixture
        .command_for("portfolio-walk-counts")
        .args(["--walk-restart-steps", "2", "--max-states", "10000"])
        .output()
        .unwrap();
    assert!(output.status.success());
    let answer: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(answer["verdict"], "reachable");
    assert_eq!(answer["method"], "sparse-count-plan");
    let trace: Vec<usize> = serde_json::from_value(answer["trace"].clone()).unwrap();
    assert_eq!(trace.len(), 9000);
    let problem: vass_reach::model::Problem = serde_json::from_value(problem).unwrap();
    assert_eq!(problem.check_witness(&trace).unwrap(), vec![9000]);
}

#[test]
fn portfolio_walk_falls_back_to_a_checkable_negative_proof() {
    for method in ["portfolio-walk", "portfolio-walk-counts"] {
        let fixture = Fixture::new();
        let path = fixture.0.join("problem.json");
        let mut problem: Value = serde_json::from_slice(&fs::read(&path).unwrap()).unwrap();
        problem["target"][0]["coefficients"] = json!([-1]);
        fs::write(&path, serde_json::to_vec(&problem).unwrap()).unwrap();
        let output = fixture.command_for(method).output().unwrap();
        assert!(output.status.success());
        let answer: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(answer["verdict"], "unreachable");
        let proof = fixture.0.join("answer.json");
        fs::write(&proof, output.stdout).unwrap();
        let checked = fixture
            .command_for(method)
            .arg("--verify")
            .arg(proof)
            .output()
            .unwrap();
        assert!(
            checked.status.success(),
            "{}",
            String::from_utf8_lossy(&checked.stderr)
        );
        assert_eq!(
            serde_json::from_slice::<Value>(&checked.stdout).unwrap()["verified"],
            true
        );
    }
}

#[test]
fn portfolio_walk_rejects_zero_restart_steps() {
    for method in ["portfolio-walk", "portfolio-walk-counts"] {
        let fixture = Fixture::new();
        let output = fixture
            .command_for(method)
            .args(["--walk-restart-steps", "0"])
            .output()
            .unwrap();
        assert!(!output.status.success());
        assert!(
            String::from_utf8_lossy(&output.stderr)
                .contains("--walk-restart-steps must be positive")
        );
    }
}

#[test]
fn guided_and_incremental_cli_emit_replayable_witnesses_and_validate_restarts() {
    let fixture = Fixture::new();
    for method in ["walk-guided", "walk-incremental"] {
        let result = fixture.command_for(method).output().unwrap();
        assert!(result.status.success());
        let answer: Value = serde_json::from_slice(&result.stdout).unwrap();
        assert_eq!(answer["method"], method);
        assert_eq!(answer["verdict"], "reachable");
        assert_eq!(answer["trace"], json!([0, 0, 0]));
        let rejected = fixture
            .command_for(method)
            .args(["--walk-restart-steps", "0"])
            .output()
            .unwrap();
        assert!(!rejected.status.success());
    }
}
