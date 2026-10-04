use serde_json::Value;
use std::{fs, process::Command};

#[test]
fn original_pipeline_emits_existing_proofs_and_supports_an_ablation() {
    let directory = std::env::temp_dir().join(format!("pvass-capacity-cli-{}", std::process::id()));
    fs::create_dir(&directory).unwrap();
    fs::write(
        directory.join("net.pnml"),
        "<pnml><net id='n' type='x/ptnet'><page id='page'>
        <place id='a'><initialMarking><text>1</text></initialMarking></place>
        <place id='b'/><place id='guard'><initialMarking><text>1</text></initialMarking></place>
        <transition id='move'/><arc source='a' target='move'/><arc source='guard' target='move'/>
        <arc source='move' target='b'/><arc source='move' target='guard'/>
        <toolspecific tool='nupn'><structure root='root' safe='false'>
        <unit id='root'><places>a</places><subunits>leaf</subunits></unit>
        <unit id='leaf'><places>b</places><subunits/></unit>
        </structure></toolspecific></page></net></pnml>",
    )
    .unwrap();
    fs::write(directory.join("property.xml"), "<property-set><property><id>q</id><formula><exists-path><finally>
        <integer-le><integer-constant>2</integer-constant><tokens-count><place>b</place></tokens-count></integer-le>
        </finally></exists-path></formula></property></property-set>").unwrap();
    for (method, disabled) in [
        "portfolio-focused",
        "portfolio-stubborn",
        "portfolio-target-stubborn",
    ]
    .into_iter()
    .flat_map(|method| [false, true].map(|disabled| (method, disabled)))
    {
        let mut command = Command::new(env!("CARGO_BIN_EXE_vass-reach"));
        command
            .arg("--pnml")
            .arg(directory.join("net.pnml"))
            .arg("--xml")
            .arg(directory.join("property.xml"))
            .args(["--property-id", "q", "--method", method, "--seconds", "2"]);
        if disabled {
            command.arg("--no-capacity-preprocessing");
        }
        let result = command.output().unwrap();
        assert!(
            result.status.success(),
            "{}",
            String::from_utf8_lossy(&result.stderr)
        );
        let answer: Value = serde_json::from_slice(&result.stdout).unwrap();
        assert_eq!(answer["verdict"], "unreachable");
        let outcome = &answer["attempts"][0]["outcome"];
        if disabled {
            assert_ne!(outcome["method"], "checked-capacity");
        } else {
            assert_eq!(outcome["method"], "checked-capacity");
            assert_eq!(outcome["proof"]["kind"], "sparse-farkas-v1");
        }
    }
    fs::remove_dir_all(directory).unwrap();
}
