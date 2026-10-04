use anyhow::{Result, ensure};
use std::{env, fs, time::Duration};
use vass_reach::{count_plan, model::Problem};
fn main() -> Result<()> {
    let a: Vec<_> = env::args().collect();
    ensure!(
        a.len() == 4,
        "usage: count_plan_diagnostic PROBLEM CAP SECONDS"
    );
    let p: Problem = serde_json::from_slice(&fs::read(&a[1])?)?;
    let cap: u32 = a[2].parse()?;
    let seconds: f64 = a[3].parse()?;
    ensure!(
        seconds.is_finite() && seconds > 0.0 && seconds <= 3600.0,
        "invalid time budget"
    );
    println!(
        "{}",
        serde_json::to_string(&count_plan::solve_sparse_with_cap(
            &p,
            Duration::from_secs_f64(seconds),
            2_000_000,
            cap
        ))?
    );
    Ok(())
}
