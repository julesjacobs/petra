use anyhow::{Result, ensure};
use std::{
    env, fs,
    time::{Duration, Instant},
};
use vass_reach::{
    complete_arithmetic::{Answer, Limits},
    model::Problem,
    path_scheme,
};

fn main() -> Result<()> {
    let started = Instant::now();
    let args: Vec<_> = env::args().collect();
    ensure!(
        args.len() == 4,
        "usage: native_path_scheme PROBLEM WORDS SECONDS"
    );
    let seconds: f64 = args[3].parse()?;
    ensure!(
        seconds.is_finite() && seconds > 0.0 && seconds <= 86400.0,
        "invalid time budget"
    );
    let deadline = started + Duration::from_secs_f64(seconds);
    let p: Problem = serde_json::from_slice(&fs::read(&args[1])?)?;
    let words: Vec<Vec<usize>> = serde_json::from_slice(&fs::read(&args[2])?)?;
    let limits = Limits {
        deadline: Some(deadline),
        max_rows: Some(4096),
        max_nodes: Some(4096),
    };
    let response = match path_scheme::solve(&p, &words, &limits, 200_000)? {
        Answer::Feasible(segments) => {
            serde_json::json!({"verdict":"reachable", "segments":segments})
        }
        Answer::Infeasible => {
            serde_json::json!({"verdict":"unknown", "reason":"fixed positive-repetition scheme infeasible"})
        }
        Answer::Unknown(reason) => serde_json::json!({"verdict":"unknown", "reason":reason}),
    };
    println!("{response}");
    Ok(())
}
