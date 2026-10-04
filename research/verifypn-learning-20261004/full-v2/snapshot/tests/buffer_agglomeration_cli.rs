use serde_json::{Value, json};
use std::{
    fs,
    path::PathBuf,
    process::Command,
    sync::atomic::{AtomicUsize, Ordering},
};

static NEXT_FIXTURE: AtomicUsize = AtomicUsize::new(0);

struct Fixture(PathBuf);
impl Fixture {
    fn new(name: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "pvass-buffer-agglomeration-{}-{}-{name}",
            std::process::id(),
            NEXT_FIXTURE.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&path).unwrap();
        Self(path)
    }
    fn set_problem(&self, problem: &Value) {
        fs::write(self.0.join("query.json"), problem.to_string()).unwrap();
    }
    fn solve(&self, problem: &Value, method: &str, extra: &[&str]) -> (Value, Vec<Value>) {
        self.set_problem(problem);
        let output = Command::new(env!("CARGO_BIN_EXE_vass-reach"))
            .arg("--json")
            .arg(self.0.join("query.json"))
            .args([
                "--method",
                method,
                "--buffer-agglomeration",
                "--seconds",
                "3",
            ])
            .args(extra)
            .env("VASS_PORTFOLIO_PROFILE", "1")
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        let events = String::from_utf8(output.stderr)
            .unwrap()
            .lines()
            .map(|line| serde_json::from_str(line).unwrap())
            .collect();
        (serde_json::from_slice(&output.stdout).unwrap(), events)
    }
    fn verify(&self, answer: &Value) -> bool {
        fs::write(self.0.join("answer.json"), answer.to_string()).unwrap();
        Command::new(env!("CARGO_BIN_EXE_vass-reach"))
            .arg("--json")
            .arg(self.0.join("query.json"))
            .arg("--verify")
            .arg(self.0.join("answer.json"))
            .args(["--seconds", "3"])
            .output()
            .unwrap()
            .status
            .success()
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        fs::remove_dir_all(&self.0).unwrap();
    }
}

fn buffer_event(events: &[Value]) -> &Value {
    events
        .iter()
        .find(|e| e["event"] == "buffer-agglomeration")
        .unwrap()
}
fn eager() -> Value {
    json!({"places":["fuel","buffer","helper","goal"],"initial":[1,0,0,0],
        "transitions":[
            {"name":"produce","pre":[[0,1]],"post":[[1,2],[3,1]]},
            {"name":"consume","pre":[[1,2]],"post":[[2,1]]}],
        "target":[{"coefficients":[0,0,0,1],"bound":1,"equality":true},
                  {"coefficients":[1,0,0,0],"bound":0,"equality":true}]})
}
fn delayed() -> Value {
    json!({"places":["fuel","buffer","permit","goal"],"initial":[2,0,1,0],
        "transitions":[
            {"name":"produce","pre":[[0,2]],"post":[[1,2]]},
            {"name":"consume","pre":[[1,2],[2,1]],"post":[[2,1],[3,1]]}],
        "target":[{"coefficients":[0,0,0,1],"bound":1,"equality":true},
                  {"coefficients":[0,0,-2,0],"bound":-2,"equality":true}]})
}
fn chain(goal: u64) -> Value {
    json!({"places":["first","second","fuel","goal"],"initial":[0,0,1,0],
        "transitions":[
            {"name":"produce","pre":[[2,1]],"post":[[0,1]]},
            {"name":"forward","pre":[[0,1]],"post":[[1,1]]},
            {"name":"finish","pre":[[1,1]],"post":[[3,2]]}],
        "target":[{"coefficients":[0,0,0,1],"bound":goal,"equality":true}]})
}

#[test]
fn eager_and_delayed_expand_weighted_original_witnesses() {
    for (name, problem, final_marking) in [
        ("eager", eager(), json!([0, 0, 1, 1])),
        ("delayed", delayed(), json!([0, 0, 1, 1])),
    ] {
        let fixture = Fixture::new(name);
        let (answer, events) = fixture.solve(&problem, "bfs", &[]);
        assert_eq!(buffer_event(&events)["detail"]["steps"], 1);
        assert_eq!(answer["verdict"], "reachable");
        assert_eq!(answer["trace"], json!([0, 1]));
        assert_eq!(answer["marking"], final_marking);
        assert!(fixture.verify(&answer));
        let mut bad = answer.clone();
        bad["trace"] = json!([1, 0]);
        assert!(!fixture.verify(&bad));
        if name == "delayed" {
            bad["trace"] = json!([0]);
            assert!(!fixture.verify(&bad));
        }
    }
}

#[test]
fn cyclic_producer_consumer_dependencies_preserve_exact_conjunctions() {
    for delayed_orientation in [false, true] {
        let fixture = Fixture::new(if delayed_orientation {
            "delayed-cycle"
        } else {
            "eager-cycle"
        });
        let problem = if delayed_orientation {
            json!({"places":["fuel","buffer","permit","goal"],"initial":[1,0,1,0],
                "transitions":[
                    {"name":"produce","pre":[[0,1]],"post":[[1,2]]},
                    {"name":"consume","pre":[[1,2],[2,1]],"post":[[0,1],[2,1],[3,1]]}],
                "target":[{"coefficients":[0,0,0,1],"bound":2,"equality":true},
                          {"coefficients":[0,0,-1,0],"bound":-1,"equality":true}]})
        } else {
            json!({"places":["fuel","buffer","goal"],"initial":[1,0,0],
                "transitions":[
                    {"name":"produce","pre":[[0,1]],"post":[[1,2],[2,1]]},
                    {"name":"consume","pre":[[1,2]],"post":[[0,1]]}],
                "target":[{"coefficients":[0,0,1],"bound":2,"equality":true},
                          {"coefficients":[0,0,-1],"bound":-2,"equality":false}]})
        };
        let (answer, events) = fixture.solve(&problem, "bfs", &[]);
        assert_eq!(buffer_event(&events)["detail"]["steps"], 1);
        assert_eq!(answer["verdict"], "reachable");
        assert_eq!(answer["trace"], json!([0, 1, 0, 1]));
        assert!(fixture.verify(&answer));
    }
}

#[test]
fn repeated_steps_expand_nested_macro_recipes() {
    let fixture = Fixture::new("chain");
    let (answer, events) = fixture.solve(&chain(2), "bfs", &[]);
    assert_eq!(buffer_event(&events)["detail"]["steps"], 2);
    assert_eq!(answer["verdict"], "reachable");
    assert_eq!(answer["trace"], json!([0, 1, 2]));
    assert_eq!(answer["marking"], json!([0, 0, 0, 2]));
    assert!(fixture.verify(&answer));
}

#[test]
fn target_support_blocks_both_orientations_and_signed_buffer_constraints() {
    let mut eager_observed = eager();
    eager_observed["target"]
        .as_array_mut()
        .unwrap()
        .push(json!({"coefficients":[0,0,1,0],"bound":0,"equality":true}));
    let mut delayed_observed = delayed();
    delayed_observed["target"][0]["bound"] = json!(0);
    delayed_observed["target"]
        .as_array_mut()
        .unwrap()
        .push(json!({"coefficients":[1,0,0,0],"bound":0,"equality":true}));
    let mut buffer_observed = eager();
    buffer_observed["target"]
        .as_array_mut()
        .unwrap()
        .push(json!({"coefficients":[0,1,0,-2],"bound":0,"equality":true}));
    for (name, problem) in [
        ("eager-observed", eager_observed),
        ("delayed-observed", delayed_observed),
        ("buffer-observed", buffer_observed),
    ] {
        let fixture = Fixture::new(name);
        let (answer, events) = fixture.solve(&problem, "bfs", &[]);
        assert_eq!(buffer_event(&events)["detail"]["applicable"], false);
        assert_eq!(answer["verdict"], "reachable");
        assert_eq!(answer["trace"], json!([0]));
        assert!(fixture.verify(&answer));
    }
}

#[test]
fn nonuniform_packets_initial_tokens_and_buffer_self_loops_fall_back() {
    let cases = [
        (
            "nonuniform",
            json!({"places":["fuel","buffer","goal"],"initial":[1,0,0],
            "transitions":[{"name":"produce","pre":[[0,1]],"post":[[1,2]]},
                           {"name":"consume","pre":[[1,1]],"post":[[2,1]]}],
            "target":[{"coefficients":[0,0,1],"bound":2,"equality":true}]}),
            json!([0, 1, 1]),
        ),
        (
            "initial-buffer",
            json!({"places":["fuel","buffer","goal"],"initial":[0,1,0],
            "transitions":[{"name":"produce","pre":[[0,1]],"post":[[1,1]]},
                           {"name":"consume","pre":[[1,1]],"post":[[2,1]]}],
            "target":[{"coefficients":[0,0,1],"bound":1,"equality":true}]}),
            json!([1]),
        ),
        (
            "self-loop",
            json!({"places":["buffer","goal"],"initial":[0,0],
            "transitions":[{"name":"produce","pre":[],"post":[[0,1]]},
                           {"name":"consume-and-produce","pre":[[0,1]],"post":[[0,1],[1,1]]}],
            "target":[{"coefficients":[0,1],"bound":1,"equality":true}]}),
            json!([0, 1]),
        ),
    ];
    for (name, problem, trace) in cases {
        let fixture = Fixture::new(name);
        let (answer, events) = fixture.solve(&problem, "bfs", &[]);
        assert_eq!(buffer_event(&events)["detail"]["applicable"], false);
        assert_eq!(answer["verdict"], "reachable");
        assert_eq!(answer["trace"], trace);
        assert!(fixture.verify(&answer));
    }
}

#[test]
fn negative_step_sequence_and_inner_proof_are_both_checked() {
    let fixture = Fixture::new("negative");
    let (answer, events) = fixture.solve(&chain(3), "state-equation", &[]);
    assert_eq!(buffer_event(&events)["detail"]["steps"], 2);
    assert_eq!(answer["verdict"], "unreachable");
    assert_eq!(answer["proof"]["kind"], "buffer-agglomeration-v1");
    assert_eq!(answer["proof"]["steps"].as_array().unwrap().len(), 2);
    assert!(fixture.verify(&answer));
    for replacement in [
        json!([]),
        json!([{"place":3,"orientation":"eager"}]),
        json!([{"place":0,"orientation":"other"}]),
    ] {
        let mut bad = answer.clone();
        bad["proof"]["steps"] = replacement;
        assert!(!fixture.verify(&bad));
    }
    let mut bad = answer.clone();
    bad["proof"]["inner"] = json!({"kind":"unsupported-inner-proof"});
    assert!(!fixture.verify(&bad));
    bad = answer.clone();
    bad["proof"]["places"] = json!([]);
    assert!(!fixture.verify(&bad));
    fixture.set_problem(&chain(2));
    assert!(!fixture.verify(&answer));
}

#[test]
fn uncertified_reduced_exhaustion_stays_unknown() {
    let fixture = Fixture::new("unproved");
    let (answer, events) = fixture.solve(&chain(3), "bfs", &[]);
    assert_eq!(buffer_event(&events)["detail"]["steps"], 2);
    assert_eq!(answer["verdict"], "unknown");
    assert!(
        answer["reason"]
            .as_str()
            .unwrap()
            .contains("missing reduced proof")
    );
}

#[test]
fn trap_composition_preserves_original_ids_and_negative_nesting() {
    for positive in [false, true] {
        let fixture = Fixture::new(if positive {
            "composed-positive"
        } else {
            "composed-negative"
        });
        let mut problem = chain(if positive { 2 } else { 3 });
        problem["places"]
            .as_array_mut()
            .unwrap()
            .push(json!("trap"));
        problem["initial"].as_array_mut().unwrap().push(json!(0));
        problem["target"][0]["coefficients"]
            .as_array_mut()
            .unwrap()
            .push(json!(0));
        problem["target"]
            .as_array_mut()
            .unwrap()
            .push(json!({"coefficients":[0,0,0,0,1],"bound":0,"equality":true}));
        problem["transitions"]
            .as_array_mut()
            .unwrap()
            .insert(0, json!({"name":"poison","pre":[],"post":[[4,1]]}));
        let (answer, events) = fixture.solve(
            &problem,
            if positive { "bfs" } else { "state-equation" },
            &["--target-zero-trap", "--target-path-potential"],
        );
        assert_eq!(events[0]["event"], "target-zero-trap");
        assert_eq!(events[0]["detail"]["trap_places"], 1);
        assert_eq!(events[1]["event"], "target-path-potential");
        assert_eq!(events[1]["detail"]["applicable"], false);
        assert_eq!(buffer_event(&events)["detail"]["steps"], 2);
        if positive {
            assert_eq!(answer["verdict"], "reachable");
            assert_eq!(answer["trace"], json!([1, 2, 3]));
            assert_eq!(answer["marking"], json!([0, 0, 0, 2, 0]));
        } else {
            assert_eq!(answer["verdict"], "unreachable");
            assert_eq!(answer["proof"]["kind"], "target-zero-trap-v1");
            assert_eq!(answer["proof"]["inner"]["kind"], "buffer-agglomeration-v1");
        }
        assert!(fixture.verify(&answer));
    }
}

#[test]
fn flag_conflicts_are_rejected_before_input_is_read() {
    for (flag, tail) in [
        ("--raw", vec!["missing-query.json"]),
        ("--unlimited", vec![]),
    ] {
        let output = Command::new(env!("CARGO_BIN_EXE_vass-reach"))
            .args(["--buffer-agglomeration", "--method", "kosaraju"])
            .arg(flag)
            .args(tail)
            .output()
            .unwrap();
        assert!(!output.status.success());
        let error = String::from_utf8_lossy(&output.stderr);
        assert!(
            error.contains("--buffer-agglomeration") && error.contains(flag),
            "{error}"
        );
        assert!(error.contains("cannot be used"), "{error}");
    }
}
