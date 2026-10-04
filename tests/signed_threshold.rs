use serde_json::{Value, json};
use std::{
    io::Write,
    process::{Command, Stdio},
    time::{Duration, Instant},
};
use vass_reach::{model::Problem, signed_threshold};

fn problem() -> Value {
    json!({"places":["x","y","z"],"initial":[2,0,0],"transitions":[
        {"name":"forward","pre":[[0,1]],"post":[[1,1]]},
        {"name":"back","pre":[[1,1]],"post":[[0,1]]},
        {"name":"weighted","pre":[[0,2]],"post":[[1,2]]},
        {"name":"source","pre":[],"post":[[2,1]]},
        {"name":"read","pre":[[0,1],[1,1]],"post":[[0,1],[1,1]]}],
        "target":[{"coefficients":[1,0,0],"bound":2,"equality":false},
                  {"coefficients":[0,1,0],"bound":1,"equality":false}]})
}
fn lit(form: usize, threshold: &str, negated: bool) -> Value {
    json!({"form":form,"threshold":threshold,"negated":negated})
}
fn proof() -> Value {
    json!({"kind":"signed-threshold-invariant-v1","forms":[[[0,"1"]],[[1,"1"]]],
        "clauses":[[lit(0,"3",true)], [lit(0,"2",true),lit(1,"1",true)],
                   [lit(0,"1",true),lit(1,"2",true)], [lit(1,"3",true)]]})
}
fn rust_accepts(p: &Value, c: &Value) -> bool {
    let Ok(problem) = serde_json::from_value::<Problem>(p.clone()) else {
        return false;
    };
    let Ok(certificate) = serde_json::from_value(c.clone()) else {
        return false;
    };
    signed_threshold::verify(
        &problem,
        &certificate,
        Instant::now() + Duration::from_secs(5),
    )
    .is_ok()
}
fn python_accepts(p: &Value, c: &Value) -> bool {
    let mut child = Command::new("python3")
        .args(["-c", "import json,sys;sys.path.insert(0,'scripts');from signed_threshold_checker import verify_signed_threshold;p,c=json.load(sys.stdin);verify_signed_threshold(p,c)"])
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        .stdin(Stdio::piped()).stdout(Stdio::null()).stderr(Stdio::null())
        .spawn().unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(&serde_json::to_vec(&(p, c)).unwrap())
        .unwrap();
    child.wait().unwrap().success()
}
fn agree(p: &Value, c: &Value, expected: bool) {
    assert_eq!(rust_accepts(p, c), expected, "Rust: {p} {c}");
    assert_eq!(python_accepts(p, c), expected, "Python: {p} {c}");
}
#[test]
fn weighted_unbounded_relation_and_lower_bound_are_independently_checked() {
    let mut p = problem();
    let mut c = proof();
    agree(&p, &c, true);
    p["target"] = json!([
        {"coefficients":[1,0,0],"bound":0,"equality":true},
        {"coefficients":[0,1,0],"bound":0,"equality":true}]);
    c["clauses"] = json!([
        [lit(0, "1", false), lit(1, "2", false)],
        [lit(0, "2", false), lit(1, "1", false)]
    ]);
    agree(&p, &c, true);
    p["transitions"]
        .as_array_mut()
        .unwrap()
        .push(json!({"name":"leak","pre":[[0,2]],"post":[]}));
    agree(&p, &c, false);
}
#[test]
fn proof_cannot_hide_reachable_target_or_breaking_transition() {
    let mut p = problem();
    let c = proof();
    p["target"][0]["bound"] = json!(1);
    agree(&p, &c, false);
    p = problem();
    p["transitions"]
        .as_array_mut()
        .unwrap()
        .push(json!({"name":"break","pre":[],"post":[[0,1]]}));
    agree(&p, &c, false);
    p = problem();
    p["initial"] = json!([2, 1, 0]);
    agree(&p, &c, false);
    let mut c = proof();
    c["clauses"].as_array_mut().unwrap().remove(2);
    agree(&problem(), &c, false);
}
#[test]
fn signed_affine_forms_and_extreme_thresholds_use_exact_arithmetic() {
    let mut p = problem();
    p["target"] = json!([{"coefficients":[-1,-1,0],"bound":-3,"equality":true}]);
    let c = json!({"kind":"signed-threshold-invariant-v1","forms":[[[0,"-1"],[1,"-1"]]],
        "clauses":[[lit(0,"-2",false)],[lit(0,"-1",true)]]});
    agree(&p, &c, true);
    let mut p = problem();
    p["target"] = json!([{"coefficients":[0,0,0],"bound":9223372036854775807_i64,"equality":true}]);
    agree(
        &p,
        &json!({"kind":"signed-threshold-invariant-v1","forms":[],"clauses":[]}),
        true,
    );
    let mut c = proof();
    c["forms"]
        .as_array_mut()
        .unwrap()
        .push(json!([[2, "-184467440737095516170000000000000000"]]));
    c["clauses"].as_array_mut().unwrap().push(json!([lit(
        2,
        "184467440737095516170000000000000001",
        true
    )]));
    agree(&problem(), &c, true);
}
#[test]
fn malformed_unreferenced_rows_and_certificate_fields_are_rejected() {
    let p = problem();
    let c = proof();
    for bad_row in [
        json!({"coefficients":[],"bound":0,"equality":false}),
        json!({"coefficients":[0,0,0],"bound":true,"equality":false}),
        json!({"coefficients":[0,0,0],"bound":0,"equality":0}),
    ] {
        let mut changed = p.clone();
        changed["target"].as_array_mut().unwrap().push(bad_row);
        agree(&changed, &c, false);
    }
    let mut changed = c.clone();
    changed["trusted"] = json!(true);
    agree(&p, &changed, false);
    let mut changed = c.clone();
    changed["forms"][0] = json!([[0, "1"], [0, "1"]]);
    agree(&p, &changed, false);
    let mut changed = c;
    changed["clauses"][0][0]["threshold"] = json!(3);
    agree(&p, &changed, false);
}
#[test]
fn cli_checks_supplied_invariant_and_rejects_mutation() {
    let dir = std::env::temp_dir().join(format!("pvass-signed-threshold-{}", std::process::id()));
    std::fs::create_dir(&dir).unwrap();
    let input = dir.join("input.json");
    let answer = dir.join("answer.json");
    std::fs::write(&input, serde_json::to_vec(&problem()).unwrap()).unwrap();
    let mut result = json!({"verdict":"unreachable","proof":proof()});
    for expected in [true, false] {
        if !expected {
            result["proof"]["clauses"].as_array_mut().unwrap().remove(2);
        }
        std::fs::write(&answer, serde_json::to_vec(&result).unwrap()).unwrap();
        let output = Command::new(env!("CARGO_BIN_EXE_vass-reach"))
            .arg("--json")
            .arg(&input)
            .arg("--verify")
            .arg(&answer)
            .output()
            .unwrap();
        assert_eq!(
            output.status.success(),
            expected,
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
    }
    std::fs::remove_dir_all(dir).unwrap();
}
