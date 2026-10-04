use anyhow::{Result, ensure};
use std::{
    env, fs,
    time::{Duration, Instant},
};
use vass_reach::{count_plan, model::Problem};
fn main() -> Result<()> {
    let start = Instant::now();
    let a: Vec<_> = env::args().collect();
    ensure!(
        a.len() == 4,
        "usage: count_plan_search PROBLEM SECONDS fixed|state-budget"
    );
    let seconds: f64 = a[2].parse()?;
    ensure!(
        seconds.is_finite() && seconds > 0.0 && seconds <= 3600.0,
        "invalid time budget"
    );
    let p: Problem = serde_json::from_slice(&fs::read(&a[1])?)?;
    let budget = Duration::from_secs_f64(seconds).saturating_sub(start.elapsed());
    let out = match a[3].as_str() {
        "fixed" => count_plan::solve_sparse(&p, budget, 2_000_000),
        "state-budget" => count_plan::solve_sparse_with_state_budget(&p, budget, 2_000_000),
        _ => anyhow::bail!("invalid count policy"),
    };
    println!("{}", serde_json::to_string(&out)?);
    Ok(())
}
