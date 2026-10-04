use serde_json::{Value, json};
use std::{
    fs,
    path::PathBuf,
    process::{Command, Output},
    sync::atomic::{AtomicUsize, Ordering},
};

struct Fixture(PathBuf);

impl Fixture {
    fn new(problem: &Value) -> Self {
        static NEXT: AtomicUsize = AtomicUsize::new(0);
        let directory = std::env::temp_dir().join(format!(
            "pvass-prechecked-walk-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&directory).unwrap();
        fs::write(directory.join("query.json"), problem.to_string()).unwrap();
        Self(directory)
    }

    fn command(&self) -> Command {
        let mut command = Command::new(env!("CARGO_BIN_EXE_vass-reach"));
        command
            .arg("--json")
            .arg(self.0.join("query.json"))
            .args(["--method", "portfolio-prechecked-walk", "--seconds", "3"])
            .env("VASS_PORTFOLIO_PROFILE", "1");
        command
    }

    fn verify(&self, answer: &Value) {
        let answer_path = self.0.join("answer.json");
        fs::write(&answer_path, answer.to_string()).unwrap();
        let output = self
            .command()
            .arg("--verify")
            .arg(answer_path)
            .output()
            .unwrap();
        assert!(output.status.success(), "{:?}", output);
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        fs::remove_dir_all(&self.0).unwrap();
    }
}

fn read(output: Output) -> (Value, Vec<String>) {
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let answer = serde_json::from_slice(&output.stdout).unwrap();
    let phases = String::from_utf8_lossy(&output.stderr)
        .lines()
        .filter_map(|line| serde_json::from_str::<Value>(line).ok())
        .filter(|event| event["event"] == "phase-start")
        .map(|event| event["name"].as_str().unwrap().to_owned())
        .collect();
    (answer, phases)
}

fn reduced_query(reachable: bool) -> Value {
    let mut transitions = vec![json!({"name":"irrelevant","pre":[],"post":[[1,1]]})];
    if reachable {
        transitions.push(json!({"name":"goal","pre":[],"post":[[0,1]]}));
    }
    json!({"places":["goal","junk"],"initial":[0,4],"transitions":transitions,
        "target":[{"coefficients":[1,0],"bound":1,"equality":false}]})
}

#[test]
fn easy_negative_is_checked_before_walk_and_lifted_to_original_problem() {
    let fixture = Fixture::new(&reduced_query(false));
    let (answer, phases) = read(fixture.command().output().unwrap());
    assert_eq!(answer["verdict"], "unreachable");
    assert_eq!(phases, ["precheck::sparse-state-equation"]);
    assert_eq!(answer["proof"]["kind"], "relevance-v1");
    assert_eq!(answer["proof"]["inner"]["kind"], "sparse-farkas-v1");
    fixture.verify(&answer);
}

#[test]
fn feasible_arithmetic_passes_to_walk_and_lifts_original_transition_indices() {
    let fixture = Fixture::new(&reduced_query(true));
    let (answer, phases) = read(fixture.command().output().unwrap());
    assert_eq!(answer["verdict"], "reachable");
    assert_eq!(answer["trace"], json!([1]));
    assert_eq!(answer["marking"], json!([1, 4]));
    assert_eq!(
        phases,
        ["precheck::sparse-state-equation", "vass_reach::walk::solve"]
    );
    fixture.verify(&answer);
}

#[test]
fn exhausted_walk_retains_the_causal_fallback() {
    let fixture = Fixture::new(&json!({
        "places":["p"],"initial":[0],
        "transitions":[{"name":"produce","pre":[],"post":[[0,1]]}],
        "target":[{"coefficients":[1],"bound":3,"equality":true}]
    }));
    let (answer, phases) = read(
        fixture
            .command()
            .args(["--walk-restart-steps", "1", "--max-states", "100"])
            .output()
            .unwrap(),
    );
    assert_eq!(answer["verdict"], "reachable");
    assert_eq!(answer["trace"], json!([0, 0, 0]));
    assert_eq!(
        phases[..3],
        [
            "precheck::sparse-state-equation",
            "vass_reach::walk::solve",
            "vass_reach::causal::solve"
        ]
    );
    fixture.verify(&answer);
}

#[test]
fn small_work_budget_skips_arithmetic_precheck_without_losing_the_fallback() {
    let fixture = Fixture::new(&json!({
        "places":["a","b","c","d"],"initial":[0,0,0,0],"transitions":[],
        "target":[{"coefficients":[1,1,1,1],"bound":1,"equality":false}]
    }));
    let (answer, phases) = read(
        fixture
            .command()
            .args(["--max-states", "1"])
            .output()
            .unwrap(),
    );
    assert_eq!(answer["verdict"], "unreachable");
    assert_eq!(
        phases[..2],
        ["vass_reach::walk::solve", "vass_reach::causal::solve"]
    );
    fixture.verify(&answer);
}

#[test]
fn prechecked_walk_rejects_zero_restart_steps() {
    let fixture = Fixture::new(&reduced_query(true));
    let output = fixture
        .command()
        .args(["--walk-restart-steps", "0"])
        .output()
        .unwrap();
    assert!(!output.status.success());
    assert!(String::from_utf8_lossy(&output.stderr).contains("must be positive"));
}
