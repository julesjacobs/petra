use serde_json::json;
use std::{
    fs,
    time::{Duration, Instant},
};
use vass_reach::{buffer_agglomeration, model::Problem, relevance};

fn main() -> anyhow::Result<()> {
    let args: Vec<_> = std::env::args().collect();
    let mut p: Problem = serde_json::from_slice(&fs::read(&args[1])?)?;
    p.validate()?;
    let mut rows = Vec::new();
    let deadline = Instant::now() + Duration::from_secs(5);
    for round in 0..4 {
        for phase in ["buffer", "relevance"] {
            let before = (p.places.len(), p.transitions.len());
            let start = Instant::now();
            let mut steps = 0;
            if phase == "buffer" {
                if let Some(reduced) = buffer_agglomeration::prepare(&p, deadline, 20_000_000)? {
                    steps = reduced.steps.len();
                    p = reduced.problem;
                }
            } else {
                p = relevance::prepare(&p, deadline, 20_000_000)?.problem;
            }
            rows.push(json!({"round":round,"phase":phase,"before":before,"after":[p.places.len(),p.transitions.len()],"steps":steps,"seconds":start.elapsed().as_secs_f64()}));
        }
    }
    fs::write(&args[2], serde_json::to_vec(&p)?)?;
    println!(
        "{}",
        json!({"phases":rows,"reduced_problem":args[2],"scope":"structural diagnostic only; no original-net verdict"})
    );
    Ok(())
}
