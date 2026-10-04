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
            "pvass-raw-phase-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&path).unwrap();
        fs::write(path.join("query.json"),json!({
            "format":"ser-raw-v2","places":["r"],"initial":[0],
            "transitions":[{"name":"inc","pre":[],"post":[[0,1]]}],
            "target":{"kind":"completed-outside-automaton","zero_places":[],"response_places":[0],
                "excluded_automaton":{"states":1,"initial":0,"accepting":[0],"edges":[{"source":0,"target":0,"response":0}]}}
        }).to_string()).unwrap();
        Self(path)
    }
    fn run(&self, enabled: bool, work: &str) -> (Value, Vec<Value>) {
        let mut command = Command::new(env!("CARGO_BIN_EXE_vass-reach"));
        command.arg("--raw").arg(self.0.join("query.json")).args([
            "--method",
            "raw-negative",
            "--seconds",
            "5",
            "--max-states",
            work,
        ]);
        command
            .env_remove("VASS_RAW_NEGATIVE_DIAGNOSTICS")
            .env_remove("VASS_RAW_PHASE_DIAGNOSTICS");
        if enabled {
            command.env("VASS_RAW_PHASE_DIAGNOSTICS", "1");
        }
        let output = command.output().unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        let mut answer: Value = serde_json::from_slice(&output.stdout).unwrap();
        answer.as_object_mut().unwrap().remove("parse_seconds");
        answer.as_object_mut().unwrap().remove("solve_seconds");
        let records = String::from_utf8(output.stderr)
            .unwrap()
            .lines()
            .map(|l| serde_json::from_str(l).unwrap())
            .collect();
        (answer, records)
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[test]
fn diagnostics_leave_certificates_unchanged_and_match_nested_phases() {
    let fixture = Fixture::new();
    let (plain, silent) = fixture.run(false, "200000");
    let (traced, records) = fixture.run(true, "200000");
    assert!(silent.is_empty());
    assert_eq!(plain, traced);
    assert_eq!(traced["verdict"], "unreachable");
    for phase in [
        "input-read",
        "json-parse",
        "input-validation",
        "serial-schema-discovery",
        "schema-search",
        "semilinear-materialization",
        "projection-preparation",
        "game-expansion",
        "greatest-fixed-point",
        "component-checking",
        "outer-schema-checking",
    ] {
        assert!(
            records
                .iter()
                .any(|r| r["event"] == "phase-start" && r["phase"] == phase),
            "missing {phase}"
        );
    }
    let mut open = std::collections::BTreeSet::new();
    for row in &records {
        let key = (
            row["operation_id"].as_u64().unwrap(),
            row["phase_id"].as_u64().unwrap(),
        );
        if row["event"] == "phase-start" {
            if let Some(parent) = row["parent"].as_object() {
                assert!(open.contains(&(
                    parent["operation_id"].as_u64().unwrap(),
                    parent["phase_id"].as_u64().unwrap()
                )));
            }
            assert!(open.insert(key));
        } else if row["event"] == "phase-end" {
            assert!(open.remove(&key));
        }
    }
    assert!(open.is_empty());
    assert!(records.iter().any(|r| r["activity"] == "transfer-search"));
    assert!(records.iter().any(|r| {
        r["counters"]["transfer_calls"]
            .as_u64()
            .is_some_and(|x| x > 0)
    }));
    assert!(
        records
            .iter()
            .any(|r| r["counters"]["projected_markings_observed"] == 1)
    );
}

#[test]
fn exhausted_work_is_visible_without_changing_unknown() {
    let fixture = Fixture::new();
    let (plain, _) = fixture.run(false, "0");
    let (traced, records) = fixture.run(true, "0");
    assert_eq!(plain, traced);
    assert_eq!(traced["verdict"], "unknown");
    assert!(
        records
            .iter()
            .any(|r| r["event"] == "phase-end" && r["status"] == "work-limit")
    );
    assert!(!records.iter().any(|r| r["phase"] == "game-expansion"));
}

#[test]
fn process_wide_cap_survives_many_separate_operations() {
    let output = Command::new(std::env::current_exe().unwrap())
        .args([
            "--exact",
            "subprocess_cap_probe",
            "--ignored",
            "--nocapture",
        ])
        .env("VASS_RAW_PHASE_DIAGNOSTICS", "1")
        .env("RAW_PHASE_TEST_PROBE", "1")
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stderr.len() <= 128 * 16384);
    let records: Vec<Value> = String::from_utf8(output.stderr)
        .unwrap()
        .lines()
        .map(|l| serde_json::from_str(l).unwrap())
        .collect();
    assert_eq!(records.len(), 128);
    assert_eq!(records.last().unwrap()["event"], "diagnostics-truncated");
    assert_eq!(
        records
            .iter()
            .filter(|r| r["event"] == "diagnostics-truncated")
            .count(),
        1
    );
}

#[test]
#[ignore = "subprocess fixture for isolated environment and process-wide cap"]
fn subprocess_cap_probe() {
    assert!(std::env::var_os("RAW_PHASE_TEST_PROBE").is_some());
    let a = vass_reach::raw_target::SerialAutomaton {
        states: 1,
        initial: 0,
        accepting: vec![0],
        edges: vec![],
    };
    for _ in 0..200 {
        assert_eq!(
            vass_reach::raw_schemas::discover(
                &a,
                std::time::Instant::now() + std::time::Duration::from_secs(5),
                1000,
                10
            )
            .unwrap()
            .len(),
            1
        );
    }
}
