use anyhow::{Result, ensure};
use serde_json::json;
use std::{
    env, fs,
    time::{Duration, Instant},
};
use vass_reach::{linear, model::Problem};

fn main() -> Result<()> {
    let args: Vec<_> = env::args().collect();
    ensure!(
        args.len() == 2,
        "usage: count_obstruction_diagnostic PROBLEM"
    );
    let p: Problem = serde_json::from_slice(&fs::read(&args[1])?)?;
    p.validate()?;
    let Some(counts) = linear::state_equation(&p)
        .integer_model(Instant::now() + Duration::from_secs(5), 1_999_999)
    else {
        println!("{}", json!({"status":"no-model"}));
        return Ok(());
    };
    let mut deficits = vec![];
    for (t, tr) in p
        .transitions
        .iter()
        .enumerate()
        .filter(|(t, _)| counts[*t] > 0)
    {
        for &(place, need) in &tr.pre {
            let supply = p
                .transitions
                .iter()
                .enumerate()
                .filter(|(u, _)| *u != t)
                .map(|(u, other)| {
                    let pre = other
                        .pre
                        .iter()
                        .find(|&&(q, _)| q == place)
                        .map_or(0, |&(_, w)| w);
                    let post = other
                        .post
                        .iter()
                        .find(|&&(q, _)| q == place)
                        .map_or(0, |&(_, w)| w);
                    u128::from(post.saturating_sub(pre)) * u128::from(counts[u])
                })
                .sum::<u128>()
                + u128::from(p.initial[place]);
            if supply < u128::from(need) {
                deficits.push(
                    json!({"transition":t,"place":place,"need":need,"supply":supply.to_string()}),
                );
            }
        }
    }
    let mut remaining = counts.clone();
    let mut marking = p.initial.clone();
    let mut trace = vec![];
    while trace.len() < 100_000 {
        let mut next = None;
        for (t, &count) in remaining.iter().enumerate() {
            if count > 0
                && let Some(m) = p.fire(&marking, t)?
            {
                next = Some((t, m));
                break;
            }
        }
        let Some((t, m)) = next else { break };
        remaining[t] -= 1;
        marking = m;
        trace.push(t);
    }
    let blocked: Vec<_> = p.transitions.iter().enumerate().filter(|(t, _)| remaining[*t] > 0)
        .map(|(t, tr)| json!({"transition":t,"name":tr.name,"remaining":remaining[t],
            "deficits":tr.pre.iter().filter(|&&(q,w)| marking[q]<w)
                .map(|&(q,w)| json!({"place":q,"name":p.places[q],"have":marking[q],"need":w})).collect::<Vec<_>>()}))
        .collect();
    println!(
        "{}",
        json!({"status":"candidate","counts":counts,"first_occurrence_deficits":deficits,
        "greedy_prefix":trace,"remaining":remaining,"marking":marking,"blocked":blocked})
    );
    Ok(())
}
