use serde_json::Value;
use std::{
    fs,
    io::Write,
    path::PathBuf,
    process::{Command, Stdio},
    sync::atomic::{AtomicUsize, Ordering},
};

struct Fixture(PathBuf);

impl Fixture {
    fn new(invariant: bool) -> Self {
        static NEXT: AtomicUsize = AtomicUsize::new(0);
        let directory = std::env::temp_dir().join(format!(
            "pvass-early-linear-cli-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&directory).unwrap();
        fs::write(
            directory.join("model.pnml"),
            "<pnml><net id='n' type='x/ptnet'><page id='page'>
            <place id='a'><initialMarking><text>1</text></initialMarking></place>
            <place id='b'/>
            <transition id='split'/><transition id='join'/>
            <arc source='a' target='split'/>
            <arc source='split' target='b'><inscription><text>7</text></inscription></arc>
            <arc source='b' target='join'><inscription><text>7</text></inscription></arc>
            <arc source='join' target='a'/>
            </page></net></pnml>",
        )
        .unwrap();
        let bound = |value| {
            format!(
                "<integer-le><integer-constant>{value}</integer-constant>
                <tokens-count><place>a</place><place>b</place></tokens-count></integer-le>"
            )
        };
        let predicate = format!("<disjunction>{}{}</disjunction>", bound(8), bound(9));
        let formula = if invariant {
            format!("<all-paths><globally><negation>{predicate}</negation></globally></all-paths>")
        } else {
            format!("<exists-path><finally>{predicate}</finally></exists-path>")
        };
        fs::write(
            directory.join("property.xml"),
            format!(
                "<property-set><property><id>weighted-total</id>
                <formula>{formula}</formula></property></property-set>"
            ),
        )
        .unwrap();
        Self(directory)
    }

    fn check_original_proofs(&self, answer: &Value) {
        let mut checker = Command::new("python3")
            .args([
                "-c",
                "import json, sys
from pathlib import Path
sys.path.insert(0, 'scripts')
from native_original import translate
from benchmark import verify_proof
assert __debug__
answer = json.load(sys.stdin)
net, prop = translate(Path(sys.argv[1]), Path(sys.argv[2]), 'weighted-total')
assert prop['kind'] == answer['property_kind']
assert len(prop['targets']) == answer['branch_count'] == len(answer['attempts']) == 2
for index, (target, attempt) in enumerate(zip(prop['targets'], answer['attempts'])):
    assert attempt['branch'] == index
    assert verify_proof(dict(net, target=target), attempt['outcome']['proof']) == 'python-sparse-farkas'
",
            ])
            .arg(self.0.join("model.pnml"))
            .arg(self.0.join("property.xml"))
            .current_dir(env!("CARGO_MANIFEST_DIR"))
            .env_remove("PYTHONOPTIMIZE")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .unwrap();
        checker
            .stdin
            .take()
            .unwrap()
            .write_all(&serde_json::to_vec(answer).unwrap())
            .unwrap();
        let output = checker.wait_with_output().unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        fs::remove_dir_all(&self.0).unwrap();
    }
}

#[test]
fn weighted_conservation_is_refuted_before_walks_for_every_original_branch() {
    for invariant in [false, true] {
        let fixture = Fixture::new(invariant);
        for method in ["portfolio-excess", "auto"] {
            let output = Command::new(env!("CARGO_BIN_EXE_vass-reach"))
                .arg("--pnml")
                .arg(fixture.0.join("model.pnml"))
                .arg("--xml")
                .arg(fixture.0.join("property.xml"))
                .args([
                    "--property-id",
                    "weighted-total",
                    "--method",
                    method,
                    "--seconds",
                    "5",
                ])
                .env("VASS_PORTFOLIO_PROFILE", "1")
                .output()
                .unwrap();
            assert!(
                output.status.success(),
                "{}",
                String::from_utf8_lossy(&output.stderr)
            );
            let answer: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(answer["kind"], "original-property-v1");
            assert_eq!(answer["property_kind"], if invariant { "AG" } else { "EF" });
            assert_eq!(answer["verdict"], "unreachable");
            assert_eq!(answer["property_truth"], invariant);
            assert_eq!(answer["deadline_exceeded"], false);
            assert_eq!(answer["branch_count"], 2);
            let attempts = answer["attempts"].as_array().unwrap();
            assert_eq!(attempts.len(), 2);
            for (index, attempt) in attempts.iter().enumerate() {
                assert_eq!(attempt["branch"], index);
                assert_eq!(attempt["outcome"]["verdict"], "unreachable");
                assert_eq!(attempt["outcome"]["method"], "sparse-state-equation");
                assert_eq!(attempt["outcome"]["proof"]["kind"], "sparse-farkas-v1");
            }
            let phases: Vec<_> = String::from_utf8_lossy(&output.stderr)
                .lines()
                .filter_map(|line| serde_json::from_str::<Value>(line).ok())
                .filter(|event| event["event"] == "phase-start")
                .map(|event| event["name"].as_str().unwrap().to_owned())
                .collect();
            assert_eq!(
                phases,
                [
                    "grouped_excess::solve",
                    "linear::solve_bounded",
                    "grouped_excess::solve",
                    "linear::solve_bounded",
                ]
            );
            fixture.check_original_proofs(&answer);
        }
    }
}
