use anyhow::{Context, Result, ensure};
use serde_json::json;
use std::{
    env, fs,
    time::{Duration, Instant},
};
use vass_reach::{buffer_agglomeration, model::Problem};

fn main() -> Result<()> {
    let args: Vec<_> = env::args().skip(1).collect();
    ensure!(
        args.len() == 2,
        "usage: inspect_buffer_agglomeration QUERY.json SECONDS"
    );
    let seconds: f64 = args[1].parse()?;
    ensure!(
        seconds.is_finite() && seconds > 0.,
        "invalid preparation budget"
    );
    let problem: Problem = serde_json::from_slice(&fs::read(&args[0])?)?;
    problem.validate()?;
    let start = Instant::now();
    let deadline = start
        .checked_add(Duration::try_from_secs_f64(seconds)?)
        .context("deadline overflow")?;
    let result = buffer_agglomeration::prepare(&problem, deadline, 20_000_000);
    let elapsed = start.elapsed().as_secs_f64();
    let detail = match result {
        Ok(Some(prepared)) => json!({"status":"reduced", "steps":prepared.steps,
            "places":prepared.places, "transitions":prepared.transitions,
            "reduced":prepared.problem}),
        Ok(None) => json!({"status":"inapplicable"}),
        Err(error) => json!({"status":"preparation-failed", "error":error.to_string()}),
    };
    println!(
        "{}",
        json!({"preparation_seconds":elapsed,
        "original_places":problem.places.len(),
        "original_transitions":problem.transitions.len(),"detail":detail})
    );
    Ok(())
}
