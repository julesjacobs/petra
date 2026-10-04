use anyhow::{Result, bail};
use std::{
    env, fs,
    time::{Duration, Instant},
};
use vass_reach::{accelerated_bmc, model::Problem};

fn main() -> Result<()> {
    let args: Vec<_> = env::args().collect();
    if args.get(1).is_some_and(|s| s == "discover") {
        if args.len() != 6 {
            bail!("usage: accelerated_bmc discover PROBLEM MAX_LENGTH EXTRA_WORDS MAX_WORK");
        }
        let problem: Problem = serde_json::from_slice(&fs::read(&args[2])?)?;
        let result = vass_reach::word_discovery::discover(
            &problem,
            vass_reach::word_discovery::Limits {
                max_length: args[3].parse()?,
                extra_words: args[4].parse()?,
                max_work: args[5].parse()?,
            },
            Instant::now() + Duration::from_secs(5),
        )?;
        println!("{}", serde_json::to_string(&result)?);
        return Ok(());
    }
    if args.len() < 5 {
        bail!("usage: accelerated_bmc emit|check PROBLEM WORDS DEPTH [MODEL]");
    }
    let problem: Problem = serde_json::from_slice(&fs::read(&args[2])?)?;
    let words: Vec<Vec<usize>> = serde_json::from_slice(&fs::read(&args[3])?)?;
    let depth = args[4].parse()?;
    match args[1].as_str() {
        "emit" => print!("{}", accelerated_bmc::encode(&problem, &words, depth)?),
        "emit-bmc" => print!(
            "{}",
            accelerated_bmc::encode_mode(&problem, &words, depth, false)?
        ),
        "check" => {
            let model = fs::read_to_string(
                args.get(5)
                    .ok_or_else(|| anyhow::anyhow!("missing model"))?,
            )?;
            let status = model.split_whitespace().next();
            if !matches!(status, Some("sat" | "unsat" | "unknown")) {
                bail!("invalid solver output");
            }
            if status != Some("sat") {
                println!(
                    "{}",
                    serde_json::json!({"verdict":"unknown","reason":"no witness at requested word vocabulary and depth"})
                );
                return Ok(());
            }
            let segments = accelerated_bmc::decode(&words, depth, &model)?;
            let marking = accelerated_bmc::check(&problem, &segments)?;
            println!(
                "{}",
                serde_json::json!({"verdict":"reachable","segments":segments,"marking":marking.iter().map(ToString::to_string).collect::<Vec<_>>()})
            );
        }
        _ => bail!("unknown mode"),
    }
    Ok(())
}
