use serde_json::{Value, json};
use std::{fs, process::Command};

#[test]
fn original_input_portfolio_emits_a_verifiable_excess_proof() {
    let folder = std::env::temp_dir().join(format!("pvass-excess-cli-{}", std::process::id()));
    fs::create_dir(&folder).unwrap();
    fs::write(folder.join("model.pnml"), "<pnml><net id='n' type='x/ptnet'><page id='page'>
        <place id='a'><initialMarking><text>2</text></initialMarking></place>
        <place id='b'><initialMarking><text>1</text></initialMarking></place>
        <transition id='t'/><arc source='a' target='t'><inscription><text>2</text></inscription></arc>
        <arc source='b' target='t'/><arc source='t' target='b'><inscription><text>2</text></inscription></arc>
        </page></net></pnml>").unwrap();
    fs::write(folder.join("property.xml"), "<property-set><property><id>q</id><formula><exists-path><finally>
        <integer-le><integer-constant>3</integer-constant><tokens-count><place>b</place></tokens-count></integer-le>
        </finally></exists-path></formula></property></property-set>").unwrap();
    let problem = json!({"places":["a","b"],"initial":[2,1],"transitions":[
        {"name":"t","pre":[[0,2],[1,1]],"post":[[1,2]]}],
        "target":[{"coefficients":[0,1],"bound":3,"equality":false}]});
    fs::write(folder.join("problem.json"), problem.to_string()).unwrap();
    for method in ["grouped-excess", "portfolio-excess", "auto"] {
        let result = Command::new(env!("CARGO_BIN_EXE_vass-reach"))
            .arg("--pnml")
            .arg(folder.join("model.pnml"))
            .arg("--xml")
            .arg(folder.join("property.xml"))
            .args(["--property-id", "q", "--method", method, "--seconds", "2"])
            .output()
            .unwrap();
        assert!(
            result.status.success(),
            "{}",
            String::from_utf8_lossy(&result.stderr)
        );
        let answer: Value = serde_json::from_slice(&result.stdout).unwrap();
        assert_eq!(answer["verdict"], "unreachable");
        assert_eq!(answer["property_truth"], false);
        let outcome = &answer["attempts"][0]["outcome"];
        assert_eq!(outcome["proof"]["kind"], "grouped-excess-v1");
        fs::write(folder.join("answer.json"), outcome.to_string()).unwrap();
        let checked = Command::new(env!("CARGO_BIN_EXE_vass-reach"))
            .arg("--json")
            .arg(folder.join("problem.json"))
            .arg("--verify")
            .arg(folder.join("answer.json"))
            .output()
            .unwrap();
        assert!(
            checked.status.success(),
            "{}",
            String::from_utf8_lossy(&checked.stderr)
        );
    }
    let positive = json!({"places":["a"],"initial":[0],"transitions":[
        {"name":"produce","pre":[],"post":[[0,1]]}],
        "target":[{"coefficients":[1],"bound":2,"equality":true}]});
    fs::write(folder.join("positive.json"), positive.to_string()).unwrap();
    let result = Command::new(env!("CARGO_BIN_EXE_vass-reach"))
        .arg("--json")
        .arg(folder.join("positive.json"))
        .args(["--method", "portfolio-excess", "--seconds", "2"])
        .output()
        .unwrap();
    assert!(result.status.success());
    let answer: Value = serde_json::from_slice(&result.stdout).unwrap();
    assert_eq!(answer["verdict"], "reachable");
    assert_eq!(answer["marking"], json!([2]));
    let mut initial = positive;
    initial["initial"] = json!([2]);
    fs::write(folder.join("positive.json"), initial.to_string()).unwrap();
    let result = Command::new(env!("CARGO_BIN_EXE_vass-reach"))
        .arg("--json")
        .arg(folder.join("positive.json"))
        .args(["--method", "portfolio-excess", "--seconds", "2"])
        .output()
        .unwrap();
    assert!(result.status.success());
    let answer: Value = serde_json::from_slice(&result.stdout).unwrap();
    assert_eq!(answer["verdict"], "reachable");
    assert_eq!(answer["method"], "initial-marking");
    assert_eq!(answer["trace"], json!([]));
    assert_eq!(answer["marking"], json!([2]));
    fs::remove_dir_all(folder).unwrap();
}
