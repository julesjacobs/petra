use serde_json::{Value, json};
use std::{
    fs,
    path::PathBuf,
    process::{Command, Output},
    sync::atomic::{AtomicUsize, Ordering},
};

struct Fixture(PathBuf);
impl Fixture {
    fn new(predicate: &str, invariant: bool) -> Self {
        static NEXT: AtomicUsize = AtomicUsize::new(0);
        let directory = std::env::temp_dir().join(format!(
            "pvass-original-schedule-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&directory).unwrap();
        fs::write(directory.join("net.pnml"),
            "<pnml><net id='n' type='x/ptnet'><page id='pg'><place id='p'><initialMarking><text>1</text></initialMarking></place></page></net></pnml>").unwrap();
        let (quantifier, temporal) = if invariant {
            ("all-paths", "globally")
        } else {
            ("exists-path", "finally")
        };
        let predicate = if invariant {
            format!("<negation>{predicate}</negation>")
        } else {
            predicate.into()
        };
        fs::write(directory.join("property.xml"), format!(
            "<property-set><property><id>unused</id><formula><unsupported/></formula></property><property><id>selected</id><formula><{quantifier}><{temporal}>{predicate}</{temporal}></{quantifier}></formula></property></property-set>"
        )).unwrap();
        Self(directory)
    }
    fn command(&self, method: &str) -> Command {
        let mut command = Command::new(env!("CARGO_BIN_EXE_vass-reach"));
        command
            .arg("--pnml")
            .arg(self.0.join("net.pnml"))
            .arg("--xml")
            .arg(self.0.join("property.xml"))
            .args([
                "--property-id",
                "selected",
                "--method",
                method,
                "--seconds",
                "3",
            ]);
        command
    }
    fn solve(&self, method: &str, geometric: bool, extra: &[&str]) -> Value {
        let before = [
            fs::read(self.0.join("net.pnml")).unwrap(),
            fs::read(self.0.join("property.xml")).unwrap(),
        ];
        let mut command = self.command(method);
        if geometric {
            command.arg("--geometric-branches");
        }
        let output = command.args(extra).output().unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        assert_eq!(before[0], fs::read(self.0.join("net.pnml")).unwrap());
        assert_eq!(before[1], fs::read(self.0.join("property.xml")).unwrap());
        serde_json::from_slice(&output.stdout).unwrap()
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        fs::remove_dir_all(&self.0).unwrap();
    }
}
fn bound(value: usize) -> String {
    format!(
        "<integer-le><integer-constant>{value}</integer-constant><tokens-count><place>p</place></tokens-count></integer-le>"
    )
}
fn branches(values: &[usize]) -> String {
    format!(
        "<disjunction>{}</disjunction>",
        values.iter().map(|&n| bound(n)).collect::<String>()
    )
}
fn stable_summary(mut answer: Value) -> Value {
    answer.as_object_mut().unwrap().remove("parse_seconds");
    answer.as_object_mut().unwrap().remove("solve_seconds");
    answer
}
fn prefix(answer: &Value, expected: usize) {
    let attempts = answer["attempts"].as_array().unwrap();
    assert_eq!(attempts.len(), expected);
    for (index, attempt) in attempts.iter().enumerate() {
        assert_eq!(attempt["branch"], index);
    }
    assert_eq!(answer["kind"], "original-property-v1");
    assert_eq!(answer["property_id"], "selected");
    assert_eq!(answer["deadline_exceeded"], false);
}

#[test]
fn geometric_preserves_ef_ag_negative_coverage_and_checked_certificates() {
    for invariant in [false, true] {
        let fixture = Fixture::new(&branches(&[2, 3, 4]), invariant);
        let baseline = fixture.solve("state-equation", false, &[]);
        let geometric = fixture.solve("state-equation", true, &[]);
        prefix(&geometric, 3);
        assert_eq!(geometric["branch_count"], 3);
        assert_eq!(geometric["verdict"], "unreachable");
        assert_eq!(
            geometric["property_kind"],
            if invariant { "AG" } else { "EF" }
        );
        assert_eq!(geometric["property_truth"], invariant);
        for attempt in geometric["attempts"].as_array().unwrap() {
            assert_eq!(attempt["outcome"]["verdict"], "unreachable");
            assert!(attempt["outcome"]["certificate"].is_array());
        }
        assert_eq!(stable_summary(baseline), stable_summary(geometric));
    }
}

#[test]
fn winning_branch_keeps_only_its_contiguous_prefix_and_polarity() {
    for invariant in [false, true] {
        let fixture = Fixture::new(&branches(&[2, 1, 3]), invariant);
        let answer = fixture.solve("bfs", true, &[]);
        prefix(&answer, 2);
        assert_eq!(answer["branch_count"], 3);
        assert_eq!(answer["verdict"], "reachable");
        assert_eq!(answer["property_truth"], !invariant);
        assert_eq!(answer["attempts"][1]["outcome"]["trace"], json!([]));
        assert_eq!(answer["attempts"][1]["outcome"]["marking"], json!([1]));
    }
}

#[test]
fn empty_and_single_branch_keep_existing_semantics() {
    for (predicate, method, verdict, count) in [
        ("<false/>".to_string(), "state-equation", "unreachable", 0),
        ("<true/>".to_string(), "bfs", "reachable", 1),
        (bound(2), "state-equation", "unreachable", 1),
    ] {
        let fixture = Fixture::new(&predicate, false);
        let baseline = fixture.solve(method, false, &[]);
        let geometric = fixture.solve(method, true, &[]);
        prefix(&geometric, count);
        assert_eq!(geometric["branch_count"], count);
        assert_eq!(geometric["verdict"], verdict);
        assert_eq!(stable_summary(baseline), stable_summary(geometric));
    }
}

#[test]
fn schedule_composes_with_all_opt_in_reduction_flags() {
    let fixture = Fixture::new(&branches(&[2, 3]), false);
    let answer = fixture.solve(
        "state-equation",
        true,
        &[
            "--target-zero-trap",
            "--target-path-potential",
            "--buffer-agglomeration",
            "--no-capacity-preprocessing",
        ],
    );
    prefix(&answer, 2);
    assert_eq!(answer["verdict"], "unreachable");
    assert_eq!(answer["property_truth"], false);
}

fn rejected(output: Output, required: &str) {
    assert!(!output.status.success());
    assert!(output.stdout.is_empty());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains(required), "{stderr}");
}
#[test]
fn flag_requires_original_pnml_and_rejects_raw_and_unlimited() {
    rejected(
        Command::new(env!("CARGO_BIN_EXE_vass-reach"))
            .args(["--geometric-branches"])
            .output()
            .unwrap(),
        "--pnml",
    );
    let fixture = Fixture::new("<true/>", false);
    for flag in ["--json", "--net"] {
        rejected(
            Command::new(env!("CARGO_BIN_EXE_vass-reach"))
                .args(["--geometric-branches", flag, "missing-input"])
                .output()
                .unwrap(),
            "--pnml",
        );
    }
    rejected(
        Command::new(env!("CARGO_BIN_EXE_vass-reach"))
            .args(["--geometric-branches", "--raw", "missing-input"])
            .output()
            .unwrap(),
        "--geometric-branches",
    );
    rejected(
        fixture
            .command("kosaraju")
            .args(["--geometric-branches", "--unlimited"])
            .output()
            .unwrap(),
        "--unlimited",
    );
}
