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
        let path = std::env::temp_dir().join(format!(
            "pvass-raw-negative-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&path).unwrap();
        let query = json!({
            "format": "ser-raw-v1", "places": ["response"], "initial": [0],
            "transitions": [{"name": "increment", "pre": [], "post": [[0, 1]]}],
            "target": {"kind": "completed-outside-semilinear", "zero_places": [],
                "response_places": [0], "excluded_semilinear": [{"base": [], "periods": [[[0, 1]]]}]}
        });
        fs::write(path.join("query.json"), query.to_string()).unwrap();
        Self(path)
    }
    fn command(&self) -> Command {
        self.command_with_method("raw-negative")
    }
    fn command_with_method(&self, method: &str) -> Command {
        let mut cmd = Command::new(env!("CARGO_BIN_EXE_vass-reach"));
        cmd.arg("--raw").arg(self.0.join("query.json")).args([
            "--method",
            method,
            "--seconds",
            "3",
        ]);
        cmd
    }
    fn solve(&self, extra: &[&str]) -> Value {
        let out = self.command().args(extra).output().unwrap();
        assert!(
            out.status.success(),
            "{}",
            String::from_utf8_lossy(&out.stderr)
        );
        serde_json::from_slice(&out.stdout).unwrap()
    }
    fn verify(&self, answer: &Value) -> bool {
        let path = self.0.join("answer.json");
        fs::write(&path, answer.to_string()).unwrap();
        self.command()
            .arg("--verify")
            .arg(path)
            .output()
            .unwrap()
            .status
            .success()
    }
}

#[test]
fn automatic_raw_method_preserves_potential_search() {
    let fixture = Fixture::new();
    let output = Command::new(env!("CARGO_BIN_EXE_vass-reach"))
        .arg("--raw")
        .arg(fixture.0.join("query.json"))
        .args(["--seconds", "0.1", "--max-states", "10"])
        .output()
        .unwrap();
    assert!(output.status.success(), "{:?}", output.stderr);
    let answer: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(answer["method"], "raw-potential");
}

#[test]
fn adaptive_methods_use_existing_certificate_verification() {
    for method in [
        "raw-adaptive",
        "raw-portfolio-adaptive",
        "raw-adaptive-groups",
        "raw-portfolio-adaptive-groups",
        "raw-portfolio-balanced",
    ] {
        let fixture = Fixture::new();
        let output = fixture.command_with_method(method).output().unwrap();
        assert!(output.status.success(), "{:?}", output.stderr);
        let answer: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(answer["verdict"], "unreachable");
        assert_eq!(answer["method"], method);
        assert!(fixture.verify(&answer));
        let mut forged = answer;
        forged["proof"]["nodes"][0]["edges"] = json!([]);
        assert!(!fixture.verify(&forged));

        let output = fixture
            .command_with_method(method)
            .args(["--max-states", "0"])
            .output()
            .unwrap();
        assert!(output.status.success());
        let answer: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(answer["verdict"], "unknown");
    }
}

#[test]
fn adaptive_automaton_proof_and_portfolio_counterexample() {
    for (negative, portfolio) in [
        ("raw-adaptive", "raw-portfolio-adaptive"),
        ("raw-adaptive-groups", "raw-portfolio-adaptive-groups"),
        ("raw-negative", "raw-portfolio-balanced"),
    ] {
        automaton_proof_and_portfolio_counterexample(negative, portfolio);
    }
}

fn automaton_proof_and_portfolio_counterexample(negative: &str, portfolio: &str) {
    let fixture = Fixture::new();
    let path = fixture.0.join("query.json");
    let mut query: Value = serde_json::from_str(&fs::read_to_string(&path).unwrap()).unwrap();
    query["format"] = json!("ser-raw-v2");
    query["target"]["kind"] = json!("completed-outside-automaton");
    query["target"]
        .as_object_mut()
        .unwrap()
        .remove("excluded_semilinear");
    query["target"]["excluded_automaton"] = json!({
        "states":1,"initial":0,"accepting":[0],
        "edges":[{"source":0,"target":0,"response":0}]
    });
    fs::write(&path, query.to_string()).unwrap();
    let output = fixture.command_with_method(negative).output().unwrap();
    assert!(output.status.success());
    let answer: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(answer["verdict"], "unreachable");
    assert_eq!(answer["proof"]["format"], "raw-automaton-invariant-v1");
    assert!(fixture.verify(&answer));

    query["target"]["excluded_automaton"]["edges"] = json!([]);
    fs::write(&path, query.to_string()).unwrap();
    assert!(!fixture.verify(&answer));
    let output = fixture.command_with_method(portfolio).output().unwrap();
    assert!(output.status.success());
    let answer: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(answer["verdict"], "reachable");
    assert_eq!(answer["method"], portfolio);
    assert!(fixture.verify(&answer));
}
impl Drop for Fixture {
    fn drop(&mut self) {
        fs::remove_dir_all(&self.0).unwrap();
    }
}

#[test]
fn negative_certificate_round_trip_and_forgery() {
    let fixture = Fixture::new();
    let answer = fixture.solve(&[]);
    assert_eq!(answer["verdict"], "unreachable");
    assert_eq!(answer["proof"]["format"], "raw-component-invariant-v1");
    assert!(fixture.verify(&answer));
    let mut forged = answer.clone();
    forged["proof"]["nodes"][0]["edges"] = json!([]);
    assert!(!fixture.verify(&forged));
    let mut missing = answer;
    missing.as_object_mut().unwrap().remove("proof");
    assert!(!fixture.verify(&missing));
}

#[test]
fn exhausted_discovery_is_unknown_and_not_verifiable() {
    let fixture = Fixture::new();
    let answer = fixture.solve(&["--max-states", "0"]);
    assert_eq!(answer["verdict"], "unknown");
    assert!(!fixture.verify(&answer));
}

#[test]
fn automaton_schema_certificate_round_trip() {
    let fixture = Fixture::new();
    let path = fixture.0.join("query.json");
    let mut query: Value = serde_json::from_str(&fs::read_to_string(&path).unwrap()).unwrap();
    query["format"] = json!("ser-raw-v2");
    query["target"]["kind"] = json!("completed-outside-automaton");
    query["target"]
        .as_object_mut()
        .unwrap()
        .remove("excluded_semilinear");
    query["target"]["excluded_automaton"] = json!({
        "states":1,"initial":0,"accepting":[0],
        "edges":[{"source":0,"target":0,"response":0}]
    });
    fs::write(&path, query.to_string()).unwrap();
    let answer = fixture.solve(&[]);
    assert_eq!(answer["verdict"], "unreachable");
    assert_eq!(answer["proof"]["format"], "raw-automaton-invariant-v1");
    assert!(fixture.verify(&answer));
    query["target"]["excluded_automaton"]["accepting"] = json!([]);
    fs::write(path, query.to_string()).unwrap();
    assert!(!fixture.verify(&answer));
}

#[test]
fn initial_counterexample_cannot_produce_negative_proof() {
    let fixture = Fixture::new();
    let path = fixture.0.join("query.json");
    let mut query: Value = serde_json::from_str(&fs::read_to_string(&path).unwrap()).unwrap();
    query["initial"] = json!([1]);
    query["target"]["excluded_semilinear"][0]["periods"] = json!([[[0, 2]]]);
    fs::write(path, query.to_string()).unwrap();
    assert_eq!(fixture.solve(&[])["verdict"], "unknown");
    assert!(fixture.verify(&json!({"verdict":"reachable", "trace":[]})));
}

#[test]
fn portfolio_handles_both_checked_verdicts() {
    let fixture = Fixture::new();
    for reachable in [false, true] {
        let path = fixture.0.join("query.json");
        if reachable {
            let mut query: Value =
                serde_json::from_str(&fs::read_to_string(&path).unwrap()).unwrap();
            query["target"]["excluded_semilinear"][0]["periods"] = json!([[[0, 2]]]);
            fs::write(&path, query.to_string()).unwrap();
        }
        let out = Command::new(env!("CARGO_BIN_EXE_vass-reach"))
            .arg("--raw")
            .arg(&path)
            .args(["--method", "raw-portfolio", "--seconds", "3"])
            .output()
            .unwrap();
        assert!(
            out.status.success(),
            "{}",
            String::from_utf8_lossy(&out.stderr)
        );
        let answer: Value = serde_json::from_slice(&out.stdout).unwrap();
        assert_eq!(
            answer["verdict"],
            if reachable {
                "reachable"
            } else {
                "unreachable"
            }
        );
        assert_eq!(answer["method"], "raw-portfolio");
        assert!(fixture.verify(&answer));
    }
}
