use anyhow::{Result, ensure};
use num_bigint::BigInt;
use std::{
    env, fs,
    time::{Duration, Instant},
};
use vass_reach::{linear, model::Problem};
fn main() -> Result<()> {
    let args: Vec<_> = env::args().collect();
    ensure!(
        args.len() == 4,
        "usage: count_bound_diagnostic PROBLEM CAP SECONDS"
    );
    let cap: u32 = args[2].parse()?;
    let seconds: f64 = args[3].parse()?;
    ensure!(
        seconds.is_finite() && seconds > 0.0 && seconds <= 3600.0,
        "invalid deadline"
    );
    let deadline = Instant::now() + Duration::from_secs_f64(seconds);
    let p: Problem = serde_json::from_slice(&fs::read(&args[1])?)?;
    p.validate()?;
    let mut system = linear::state_equation(&p);
    system.rows.push(linear::Row {
        coefficients: (0..system.variables)
            .map(|i| (i, BigInt::from(-1)))
            .collect(),
        bound: -BigInt::from(cap),
    });
    if let Some(certificate) = system.refute(deadline) {
        system.check(&certificate)?;
        println!(
            "{}",
            serde_json::json!({"status":"cap-refuted","cap":cap,"multipliers":certificate})
        );
    } else {
        println!("{}", serde_json::json!({"status":"unknown","cap":cap}));
    }
    Ok(())
}
