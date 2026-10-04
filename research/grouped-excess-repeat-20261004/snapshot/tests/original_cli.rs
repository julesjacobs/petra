use serde_json::Value;
use std::{
    fs,
    path::PathBuf,
    process::{Command, Output},
    sync::atomic::{AtomicUsize, Ordering},
};

struct Fixture {
    directory: PathBuf,
}
impl Fixture {
    fn new(predicate: &str, invariant: bool) -> Self {
        static NEXT: AtomicUsize = AtomicUsize::new(0);
        let directory = std::env::temp_dir().join(format!(
            "pvass-original-cli-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&directory).unwrap();
        fs::write(
            directory.join("net.pnml"),
            "<pnml><net id='n' type='x/ptnet'><page id='page'><place id='p'/></page></net></pnml>",
        )
        .unwrap();
        let (q, t) = if invariant {
            ("all-paths", "globally")
        } else {
            ("exists-path", "finally")
        };
        fs::write(directory.join("property.xml"), format!("<property-set><property><id>other</id><formula><unsupported/></formula></property><property><id>wanted</id><formula><{q}><{t}>{predicate}</{t}></{q}></formula></property></property-set>")).unwrap();
        Self { directory }
    }
    fn command(&self) -> Command {
        let mut command = Command::new(env!("CARGO_BIN_EXE_vass-reach"));
        command
            .arg("--pnml")
            .arg(self.directory.join("net.pnml"))
            .arg("--xml")
            .arg(self.directory.join("property.xml"))
            .args([
                "--property-id",
                "wanted",
                "--method",
                "state-equation",
                "--seconds",
                "2",
            ]);
        command
    }
    fn result(&self) -> Value {
        let output = self.command().output().unwrap();
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
        fs::remove_dir_all(&self.directory).unwrap();
    }
}
fn bound(n: usize) -> String {
    format!(
        "<integer-le><integer-constant>{n}</integer-constant><tokens-count><place>p</place></tokens-count></integer-le>"
    )
}
fn rejected(output: Output) {
    assert!(!output.status.success());
    assert!(output.stdout.is_empty());
}

#[test]
fn native_input_preserves_polarity_and_negative_certificates() {
    for invariant in [false, true] {
        let predicate = if invariant {
            format!("<negation>{}</negation>", bound(1))
        } else {
            bound(1)
        };
        let result = Fixture::new(&predicate, invariant).result();
        assert_eq!(result["kind"], "original-property-v1");
        assert_eq!(result["property_id"], "wanted");
        assert_eq!(result["property_kind"], if invariant { "AG" } else { "EF" });
        assert_eq!(result["verdict"], "unreachable");
        assert_eq!(result["property_truth"], invariant);
        assert_eq!(result["branch_count"], 1);
        assert!(!result["attempts"][0]["outcome"]["certificate"].is_null());
        assert!(result.get("net").is_none());
        assert!(result.get("targets").is_none());
    }
}

#[test]
fn multiple_branches_and_empty_targets_have_distinct_results() {
    let predicate = format!("<disjunction>{}{}</disjunction>", bound(1), bound(2));
    let result = Fixture::new(&predicate, false).result();
    assert_eq!(result["branch_count"], 2);
    assert_eq!(result["attempts"].as_array().unwrap().len(), 2);
    assert_eq!(result["verdict"], "unreachable");
    let result = Fixture::new("<false/>", false).result();
    assert_eq!(result["branch_count"], 0);
    assert_eq!(result["attempts"], serde_json::json!([]));
    assert_eq!(result["verdict"], "unreachable");
    let fixture = Fixture::new("<true/>", false);
    let output = Command::new(env!("CARGO_BIN_EXE_vass-reach"))
        .arg("--pnml")
        .arg(fixture.directory.join("net.pnml"))
        .arg("--xml")
        .arg(fixture.directory.join("property.xml"))
        .args([
            "--property-id",
            "wanted",
            "--method",
            "bfs",
            "--seconds",
            "2",
        ])
        .output()
        .unwrap();
    assert!(output.status.success());
    let reachable: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(reachable["branch_count"], 1);
    assert_eq!(reachable["verdict"], "reachable");
    assert_eq!(
        reachable["attempts"][0]["outcome"]["trace"],
        serde_json::json!([])
    );
}

#[test]
fn incompatible_flags_and_missing_property_are_errors() {
    let fixture = Fixture::new("<true/>", false);
    for flag in ["--json", "--net", "--raw", "--verify", "--export-json"] {
        rejected(fixture.command().args([flag, "unused"]).output().unwrap());
    }
    rejected(fixture.command().arg("--unlimited").output().unwrap());
    let xml = fs::read_to_string(fixture.directory.join("property.xml")).unwrap();
    fs::write(
        fixture.directory.join("property.xml"),
        xml.replace("wanted", "absent"),
    )
    .unwrap();
    rejected(fixture.command().output().unwrap());
    rejected(
        Command::new(env!("CARGO_BIN_EXE_vass-reach"))
            .args(["--pnml", "unused"])
            .output()
            .unwrap(),
    );
    rejected(
        Command::new(env!("CARGO_BIN_EXE_vass-reach"))
            .args(["--property-id", "wanted"])
            .output()
            .unwrap(),
    );
}

#[test]
fn existing_json_output_keeps_its_single_problem_shape() {
    let fixture = Fixture::new("<true/>", false);
    let path = fixture.directory.join("problem.json");
    fs::write(
        &path,
        r#"{"places":["p"],"initial":[0],"transitions":[],"target":[]}"#,
    )
    .unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_vass-reach"))
        .arg("--json")
        .arg(path)
        .args(["--method", "bfs"])
        .output()
        .unwrap();
    assert!(output.status.success());
    let result: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(result["verdict"], "reachable");
    assert!(result.get("attempts").is_none());
    assert!(result.get("parse_seconds").is_some());
    assert_eq!(result["places"], 1);
}
