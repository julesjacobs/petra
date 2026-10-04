use serde_json::{Value, json};
use std::{fs, path::PathBuf, process::Command};

struct Fixture(PathBuf);
impl Fixture {
    fn new(name: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "pvass-target-path-potential-{}-{name}",
            std::process::id()
        ));
        fs::create_dir(&path).unwrap();
        Self(path)
    }
    fn solve(&self, problem: &Value, method: &str, trap: bool) -> (Value, Vec<Value>) {
        fs::write(self.0.join("query.json"), problem.to_string()).unwrap();
        let mut command = Command::new(env!("CARGO_BIN_EXE_vass-reach"));
        command
            .arg("--json")
            .arg(self.0.join("query.json"))
            .args([
                "--method",
                method,
                "--target-path-potential",
                "--seconds",
                "3",
            ])
            .env("VASS_PORTFOLIO_PROFILE", "1");
        if trap {
            command.arg("--target-zero-trap");
        }
        let output = command.output().unwrap();
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
fn problem(initial: u64, step: u64, goal: u64) -> Value {
    json!({"places":["p"],"initial":[initial],
        "transitions":[{"name":"grow","pre":[],"post":[[0,step]]}],
        "target":[{"coefficients":[1],"bound":goal,"equality":true}]})
}
fn trap_problem(step: u64) -> Value {
    json!({"places":["p","trap"],"initial":[0,0],
        "transitions":[{"name":"poison","pre":[],"post":[[0,1],[1,1]]},
                       {"name":"grow","pre":[],"post":[[0,step]]}],
        "target":[{"coefficients":[1,0],"bound":1,"equality":true},
                  {"coefficients":[0,1],"bound":0,"equality":true}]})
}
#[test]
fn positive_boundary_trace_has_original_marking_and_ids() {
    let fixture = Fixture::new("positive");
    let (answer, events) = fixture.solve(&problem(0, 1, 3), "bfs", false);
    assert_eq!(events[0]["event"], "target-path-potential");
    assert_eq!(events[0]["detail"]["slack"], 3);
    assert_eq!(answer["verdict"], "reachable");
    assert_eq!(answer["trace"], json!([0, 0, 0]));
    assert_eq!(answer["marking"], json!([3]));
    assert!(fixture.verify(&answer));
    let mut bad = answer.clone();
    bad["trace"] = json!([0, 0, 0, 0]);
    assert!(!fixture.verify(&bad));
}
#[test]
fn both_negative_proof_forms_check_original_input() {
    for impossible in [false, true] {
        let fixture = Fixture::new(if impossible { "infeasible" } else { "inner" });
        let (answer, _) = fixture.solve(
            &problem(if impossible { 2 } else { 0 }, 2, 1),
            "portfolio-focused",
            false,
        );
        assert_eq!(answer["verdict"], "unreachable");
        assert_eq!(
            answer["proof"]["kind"],
            if impossible {
                "target-path-potential-infeasible-v1"
            } else {
                "target-path-potential-v1"
            }
        );
        assert!(fixture.verify(&answer));
        let mut bad = answer.clone();
        bad["proof"]["bound"] = json!(0);
        assert!(!fixture.verify(&bad));
        if !impossible {
            bad = answer.clone();
            bad["proof"]["inner"] = json!({"kind":"target-path-potential-infeasible-v1"});
            assert!(!fixture.verify(&bad));
        }
    }
}
#[test]
fn trap_then_potential_lifts_original_ids_and_nested_negative() {
    for positive in [false, true] {
        let fixture = Fixture::new(if positive {
            "composed-positive"
        } else {
            "composed-negative"
        });
        let (answer, events) = fixture.solve(
            &trap_problem(if positive { 1 } else { 2 }),
            "portfolio-focused",
            true,
        );
        assert_eq!(events[0]["event"], "target-zero-trap");
        assert_eq!(events[0]["detail"]["trap_places"], 1);
        assert_eq!(events[1]["event"], "target-path-potential");
        assert_eq!(events[1]["detail"]["slack"], 1);
        if positive {
            assert_eq!(answer["verdict"], "reachable");
            assert_eq!(answer["trace"], json!([1]));
            assert_eq!(answer["marking"], json!([1, 0]));
        } else {
            assert_eq!(answer["verdict"], "unreachable");
            assert_eq!(answer["proof"]["kind"], "target-zero-trap-v1");
            assert_eq!(answer["proof"]["inner"]["kind"], "target-path-potential-v1");
        }
        assert!(fixture.verify(&answer));
    }
}
#[test]
fn decreasing_total_falls_back_and_remains_reachable() {
    let fixture = Fixture::new("decreasing");
    let p = json!({"places":["p"],"initial":[3],
        "transitions":[{"name":"decrease","pre":[[0,1]],"post":[]}],
        "target":[{"coefficients":[1],"bound":2,"equality":true}]});
    let (answer, events) = fixture.solve(&p, "bfs", false);
    assert_eq!(events[0]["detail"]["applicable"], false);
    assert_eq!(answer["verdict"], "reachable");
    assert_eq!(answer["trace"], json!([0]));
    assert!(fixture.verify(&answer));
    assert!(!fixture.verify(&json!({"verdict":"unreachable", "proof":{
        "kind":"target-path-potential-infeasible-v1"}})));
}
#[test]
fn uncertified_augmented_exhaustion_stays_unknown() {
    let fixture = Fixture::new("unproved");
    let (answer, _) = fixture.solve(&problem(0, 2, 1), "bfs", false);
    assert_eq!(answer["verdict"], "unknown");
    assert!(
        answer["reason"]
            .as_str()
            .unwrap()
            .contains("missing reduced proof")
    );
}
#[test]
fn original_input_preserves_ef_and_ag_polarity() {
    let fixture = Fixture::new("pnml");
    fs::write(fixture.0.join("model.pnml"), "<pnml><net id='n' type='x/ptnet'><page id='pg'><place id='p'><initialMarking><text>3</text></initialMarking></place><transition id='t'/><arc id='a' source='t' target='p'/></page></net></pnml>").unwrap();
    for invariant in [false, true] {
        let bound = "<integer-le><tokens-count><place>p</place></tokens-count><integer-constant>2</integer-constant></integer-le>";
        let formula = if invariant {
            format!("<all-paths><globally><negation>{bound}</negation></globally></all-paths>")
        } else {
            format!("<exists-path><finally>{bound}</finally></exists-path>")
        };
        fs::write(fixture.0.join("property.xml"), format!("<property-set><property><id>q</id><formula>{formula}</formula></property></property-set>")).unwrap();
        let output = Command::new(env!("CARGO_BIN_EXE_vass-reach"))
            .arg("--pnml")
            .arg(fixture.0.join("model.pnml"))
            .arg("--xml")
            .arg(fixture.0.join("property.xml"))
            .args([
                "--property-id",
                "q",
                "--method",
                "portfolio-focused",
                "--no-capacity-preprocessing",
                "--target-path-potential",
                "--seconds",
                "3",
            ])
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        let answer: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(answer["verdict"], "unreachable");
        assert_eq!(answer["property_truth"], invariant);
        assert_eq!(
            answer["attempts"][0]["outcome"]["proof"]["kind"],
            "target-path-potential-infeasible-v1"
        );
    }
}
