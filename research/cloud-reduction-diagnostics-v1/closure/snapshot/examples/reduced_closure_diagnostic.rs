use serde_json::json;
use std::{
    fs,
    time::{Duration, Instant},
};
use vass_reach::{buffer_agglomeration, model::Problem, relevance, search};

fn main() -> anyhow::Result<()> {
    let args: Vec<_> = std::env::args().collect();
    let mut p: Problem = serde_json::from_slice(&fs::read(&args[1])?)?;
    p.validate()?;
    let start = Instant::now();
    let deadline = start + Duration::from_secs(3);
    let mut reductions = Vec::new();
    for _ in 0..2 {
        if let Some(prepared) = buffer_agglomeration::prepare(&p, deadline, 20_000_000)? {
            reductions.push(json!({"kind":"buffer", "steps":prepared.steps}));
            p = prepared.problem;
        }
        let prepared = relevance::prepare(&p, deadline, 20_000_000)?;
        reductions.push(json!({"kind":"relevance", "places":prepared.places, "transitions":prepared.transitions}));
        p = prepared.problem;
    }
    let answer = search::solve(
        &p,
        false,
        deadline.saturating_duration_since(Instant::now()),
        200_000,
    );
    println!(
        "{}",
        json!({"scope":"diagnostic reduction chain and reduced-net answer", "reductions":reductions, "reduced_problem":p,"answer":answer,"seconds":start.elapsed().as_secs_f64()})
    );
    Ok(())
}
