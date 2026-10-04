use std::{fs, time::Duration};
use vass_reach::{integer_equation, model::Problem, state_equation};

#[test]
#[ignore = "requires collected SER artifact queries"]
fn measured_arithmetic_gaps() {
    for name in [
        "d1_disjunct_0",
        "d3_disjunct_1",
        "d4_disjunct_0",
        "d4_disjunct_1",
        "d4_disjunct_2",
        "d4_disjunct_3",
    ] {
        let p: Problem = serde_json::from_str(
            &fs::read_to_string(format!("results/comparison/{name}.json")).unwrap(),
        )
        .unwrap();
        for integer in [false, true] {
            let out = if integer {
                integer_equation::solve(&p, Duration::from_secs(2), 2000)
            } else {
                state_equation::solve(&p, Duration::from_secs(2), 2000)
            };
            println!("{name} {} {} {}", out.method, out.verdict, out.reason);
            if integer || name.ends_with("disjunct_2") || name.ends_with("disjunct_3") {
                assert_eq!(out.verdict, "unreachable", "{name}");
            }
            if let Some(proof) = out.proof {
                integer_equation::verify_certificate(&p, &proof).unwrap();
            }
            if let Some(proof) = out.certificate {
                state_equation::verify_certificate(&p, &proof).unwrap();
            }
        }
    }
}
