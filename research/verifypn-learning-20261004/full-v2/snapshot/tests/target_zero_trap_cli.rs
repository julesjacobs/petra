use serde_json::{Value, json};
use std::{fs, path::PathBuf, process::Command};

struct Fixture(PathBuf);
impl Fixture {
    fn new(name: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "pvass-target-zero-trap-{}-{name}",
            std::process::id()
        ));
        fs::create_dir(&path).unwrap();
        Self(path)
    }
    fn solve(&self, problem: &Value, method: &str) -> Value {
        fs::write(self.0.join("query.json"), problem.to_string()).unwrap();
        let result = Command::new(env!("CARGO_BIN_EXE_vass-reach"))
            .arg("--json")
            .arg(self.0.join("query.json"))
            .args(["--method", method, "--target-zero-trap", "--seconds", "3"])
            .env("VASS_PORTFOLIO_PROFILE", "1")
            .output()
            .unwrap();
        assert!(
            result.status.success(),
            "{}",
            String::from_utf8_lossy(&result.stderr)
        );
        let profile: Vec<Value> = String::from_utf8(result.stderr)
            .unwrap()
            .lines()
            .map(|line| serde_json::from_str(line).unwrap())
            .collect();
        assert_eq!(profile[0]["event"], "target-zero-trap");
        serde_json::from_slice(&result.stdout).unwrap()
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
fn problem(initial_trap: u64, positive: bool) -> Value {
    let mut transitions = vec![json!({"name":"bad","pre":[],"post":[[0,1],[1,1]]})];
    if positive {
        transitions.push(json!({"name":"good","pre":[],"post":[[0,1]]}));
    }
    json!({"places":["goal","trap"],"initial":[0,initial_trap],"transitions":transitions,
        "target":[{"coefficients":[1,0],"bound":1,"equality":false},
                  {"coefficients":[0,-1],"bound":0,"equality":false}]})
}
#[test]
fn positive_trace_uses_original_transition_indices() {
    let fixture = Fixture::new("positive");
    let answer = fixture.solve(&problem(0, true), "portfolio-focused");
    assert_eq!(answer["verdict"], "reachable");
    assert_eq!(answer["trace"], json!([1]));
    assert_eq!(answer["marking"], json!([1, 0]));
    assert!(fixture.verify(&answer));
}
#[test]
fn both_negative_proof_forms_are_checked_against_original_net() {
    for initially_marked in [false, true] {
        let fixture = Fixture::new(if initially_marked {
            "marked"
        } else {
            "reduced"
        });
        let answer = fixture.solve(
            &problem(u64::from(initially_marked), false),
            "portfolio-focused",
        );
        assert_eq!(answer["verdict"], "unreachable");
        assert_eq!(
            answer["proof"]["kind"],
            if initially_marked {
                "target-zero-trap-marked-v1"
            } else {
                "target-zero-trap-v1"
            }
        );
        assert!(fixture.verify(&answer));
        let mut bad = answer.clone();
        bad["proof"]["trap"] = json!([0]);
        assert!(!fixture.verify(&bad));
    }
}
#[test]
fn unproved_reduced_exhaustion_returns_unknown() {
    let fixture = Fixture::new("no-proof");
    let answer = fixture.solve(&problem(0, false), "bfs");
    assert_eq!(answer["verdict"], "unknown");
    assert!(
        answer["reason"]
            .as_str()
            .unwrap()
            .contains("missing reduced proof")
    );
}
#[test]
fn original_input_preserves_target_polarity() {
    let fixture = Fixture::new("pnml");
    fs::write(fixture.0.join("model.pnml"), "<pnml><net id='n' type='x/ptnet'><page id='pg'><place id='p'><initialMarking><text>1</text></initialMarking></place><transition id='t'/><arc id='a' source='p' target='t'/><arc id='b' source='t' target='p'/></page></net></pnml>").unwrap();
    for invariant in [false, true] {
        let zero = "<integer-le><tokens-count><place>p</place></tokens-count><integer-constant>0</integer-constant></integer-le>";
        let formula = if invariant {
            format!("<all-paths><globally><negation>{zero}</negation></globally></all-paths>")
        } else {
            format!("<exists-path><finally>{zero}</finally></exists-path>")
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
                "--target-zero-trap",
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
            "target-zero-trap-marked-v1"
        );
    }
}
