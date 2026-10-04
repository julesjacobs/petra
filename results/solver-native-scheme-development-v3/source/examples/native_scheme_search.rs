use anyhow::{Result, ensure};
use std::{
    env, fs,
    time::{Duration, Instant},
};
use vass_reach::{
    model::Problem,
    scheme_search::{self, Limits},
    word_discovery,
};
fn main() -> Result<()> {
    let started = Instant::now();
    let args: Vec<_> = env::args().collect();
    ensure!(
        args.len() == 4,
        "usage: native_scheme_search PROBLEM SECONDS singleton|cycles"
    );
    let seconds: f64 = args[2].parse()?;
    ensure!(
        seconds.is_finite() && seconds > 0.0 && seconds <= 86400.0,
        "invalid time budget"
    );
    ensure!(
        matches!(args[3].as_str(), "singleton" | "cycles"),
        "invalid discovery mode"
    );
    let problem: Problem = serde_json::from_slice(&fs::read(&args[1])?)?;
    let outcome = scheme_search::solve(
        &problem,
        started + Duration::from_secs_f64(seconds),
        Limits {
            depth: 4,
            schemes: 256,
            entries: 200_000,
            arithmetic_rows: 4096,
            arithmetic_nodes: 4096,
            arithmetic_quantum: Duration::from_millis(50),
            discovery: word_discovery::Limits {
                max_work: 2_000_000,
                max_length: 8,
                extra_words: if args[3] == "cycles" { 128 } else { 0 },
            },
        },
    )?;
    let mut response = serde_json::to_value(&outcome)?;
    if outcome.verdict == "reachable" {
        let marking = vass_reach::accelerated_bmc::check(&problem, &outcome.segments)?;
        response["marking"] =
            serde_json::json!(marking.iter().map(ToString::to_string).collect::<Vec<_>>());
    }
    println!("{response}");
    Ok(())
}
