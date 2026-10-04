use anyhow::{Context, Result, bail};
use clap::Parser;
use serde_json::json;
use std::{
    fs,
    io::Write,
    path::PathBuf,
    time::{Duration, Instant},
};
use vass_reach::{
    backward, cegar, complete, count_plan, guided, input, integer_equation, klmst, model::Problem,
    quotient, reduced, search, state_equation, structural,
};

#[derive(Parser)]
#[command(about = "Native Petri-net reachability experiments; limits return UNKNOWN")]
struct Args {
    /// Original ordinary P/T PNML; --xml selects a property set by exact ID.
    #[arg(long, requires_all = ["xml", "property_id"], conflicts_with_all = ["net", "json", "raw", "unlimited", "verify", "export_json"])]
    pnml: Option<PathBuf>,
    #[arg(long, requires = "pnml")]
    property_id: Option<String>,
    #[arg(long)]
    net: Option<PathBuf>,
    /// Direct original-net/semilinear-complement query exported by ser.
    #[arg(long)]
    raw: Option<PathBuf>,
    #[arg(long)]
    xml: Option<PathBuf>,
    #[arg(long)]
    json: Option<PathBuf>,
    #[arg(long, default_value="portfolio-v2", value_parser=["grouped-excess","portfolio-excess","signed-threshold","signed-threshold-unary","capacity","walk-guided","walk-incremental","pair","phase-pair","portfolio-prechecked-walk","portfolio-walk","portfolio-walk-counts","portfolio-reduced","reduced-bfs","walk","portfolio","portfolio-old","bfs","best-first","state-equation","integer-state-equation","marked-traps","support","klm-schemes","kosaraju","cegar","portfolio-cegar","quotient-bfs","guided","relaxed","local-closure","backward","count-plan","portfolio-next","portfolio-v2","portfolio-v3","portfolio-causal","portfolio-relaxed","portfolio-local","portfolio-focused","portfolio-batched","relaxed-batched","portfolio-stubborn","portfolio-target-stubborn","portfolio-symbolic","dag-sat","relaxed-focused","relaxed-stubborn","relaxed-target-stubborn","interval-invariant","projected-cegar","sparse-state-equation","sparse-count-plan","sparse-count-plan-budget","frontier-count-plan","frontier-count-plan-expanded","causal-state-equation","token-moment","token-cut","bounded-token-cut","finite-token-cut","lazy-finite-token-cut","guided-quotient","bounded-guided","reduced-guided","raw-bfs","raw-search","raw-potential","raw-negative","raw-portfolio","raw-portfolio-balanced","raw-adaptive","raw-portfolio-adaptive","raw-adaptive-groups","raw-portfolio-adaptive-groups"])]
    method: String,
    /// Remove all artificial budgets for the complete Kosaraju procedure.
    #[arg(long)]
    unlimited: bool,
    #[arg(long, default_value_t = 5.0)]
    seconds: f64,
    #[arg(long, default_value_t = 200_000)]
    max_states: usize,
    /// Deterministic seed for the opt-in walk engine.
    #[arg(long, default_value_t = vass_reach::walk::DEFAULT_SEED)]
    walk_seed: u64,
    /// Maximum firings per walk before restarting; total firings use --max-states.
    #[arg(long, default_value_t = vass_reach::walk::DEFAULT_RESTART_STEPS)]
    walk_restart_steps: usize,
    #[arg(long, default_value_t = 2000)]
    max_rows: usize,
    /// Disable structural capacity discovery in focused/stubborn/symbolic PNML pipelines.
    #[arg(long)]
    no_capacity_preprocessing: bool,
    /// Exclude initially empty traps that the target requires to remain empty.
    #[arg(long, conflicts_with_all = ["raw", "unlimited"])]
    target_zero_trap: bool,
    /// Guard nondecreasing total tokens by a checked upper bound from the target.
    #[arg(long, conflicts_with_all = ["raw", "unlimited"])]
    target_path_potential: bool,
    /// Agglomerate initially empty unqueried buffers with checked macro traces.
    #[arg(long, conflicts_with_all = ["raw", "unlimited"])]
    buffer_agglomeration: bool,
    /// Revisit unresolved original-property branches with increasing time shares.
    #[arg(long, requires = "pnml", conflicts_with_all = ["raw", "unlimited"])]
    geometric_branches: bool,
    #[arg(long)]
    export_json: Option<PathBuf>,
    #[arg(long)]
    verify: Option<PathBuf>,
}
fn main() -> Result<()> {
    let args = Args::parse();
    if !args.seconds.is_finite() || args.seconds <= 0.0 {
        bail!("--seconds must be finite and positive");
    }
    if args.unlimited && args.method != "kosaraju" {
        bail!("--unlimited requires --method kosaraju");
    }
    if matches!(
        args.method.as_str(),
        "walk"
            | "walk-guided"
            | "walk-incremental"
            | "portfolio-walk"
            | "portfolio-walk-counts"
            | "portfolio-reduced"
            | "portfolio-excess"
            | "portfolio-prechecked-walk"
    ) && args.walk_restart_steps == 0
    {
        bail!("--walk-restart-steps must be positive");
    }
    let start = Instant::now();
    if let Some(path) = &args.pnml {
        anyhow::ensure!(
            !matches!(
                args.method.as_str(),
                "raw-bfs"
                    | "raw-search"
                    | "raw-potential"
                    | "raw-negative"
                    | "raw-portfolio"
                    | "raw-portfolio-balanced"
                    | "raw-adaptive"
                    | "raw-portfolio-adaptive"
                    | "raw-adaptive-groups"
                    | "raw-portfolio-adaptive-groups"
            ),
            "raw methods require --raw"
        );
        let limit = timeout_from(args.seconds)?;
        let net_xml = fs::read_to_string(path)?;
        let query = vass_reach::pnml::parse(
            &net_xml,
            &fs::read_to_string(args.xml.as_ref().context("--xml is required with --pnml")?)?,
            args.property_id
                .as_deref()
                .context("--property-id is required with --pnml")?,
        )?;
        let use_capacities = !args.no_capacity_preprocessing
            && matches!(
                args.method.as_str(),
                "portfolio-focused"
                    | "portfolio-walk"
                    | "portfolio-walk-counts"
                    | "portfolio-reduced"
                    | "portfolio-excess"
                    | "portfolio-prechecked-walk"
                    | "portfolio-batched"
                    | "portfolio-stubborn"
                    | "portfolio-target-stubborn"
                    | "portfolio-symbolic"
            );
        let seeds = if use_capacities {
            vass_reach::capacity::target_places(&query.targets)
        } else {
            vec![]
        };
        let mut capacities = None;
        let schedule = if args.geometric_branches {
            vass_reach::original::Schedule::Geometric
        } else {
            vass_reach::original::Schedule::SinglePass
        };
        let outcome = vass_reach::original::solve_with_schedule(
            query,
            limit,
            schedule,
            || start.elapsed(),
            |problem, budget| {
                let branch_start = Instant::now();
                if use_capacities {
                    let discovery_budget = budget.mul_f64(0.2).min(Duration::from_millis(500));
                    let discovered = capacities.get_or_insert_with(|| {
                        vass_reach::capacity::discover(
                            problem,
                            &net_xml,
                            &seeds,
                            branch_start + discovery_budget,
                            4_000_000,
                        )
                    });
                    if let Some(outcome) = discovered.refute(problem, branch_start + budget) {
                        return outcome;
                    }
                }
                solve_problem(
                    problem,
                    &args,
                    budget.saturating_sub(branch_start.elapsed()),
                )
            },
        )?;
        let mut output = std::io::stdout().lock();
        serde_json::to_writer(&mut output, &outcome)?;
        writeln!(output)?;
        return Ok(());
    }
    if let Some(path) = &args.raw {
        anyhow::ensure!(
            matches!(
                args.method.as_str(),
                "portfolio-v2"
                    | "portfolio-next"
                    | "raw-bfs"
                    | "raw-search"
                    | "raw-potential"
                    | "raw-negative"
                    | "raw-portfolio"
                    | "raw-portfolio-balanced"
                    | "raw-adaptive"
                    | "raw-portfolio-adaptive"
                    | "raw-adaptive-groups"
                    | "raw-portfolio-adaptive-groups"
            ),
            "--raw requires a raw search, negative or portfolio method"
        );
        let query = vass_reach::raw_target::RawQuery::from_json_file(path)?;
        if let Some(path) = &args.verify {
            let answer: serde_json::Value = serde_json::from_str(&fs::read_to_string(path)?)?;
            let deadline = start + timeout_from(args.seconds)?;
            match answer["verdict"].as_str() {
                Some("unreachable") => {
                    if answer["proof"]["format"] == "raw-automaton-invariant-v1" {
                        let certificate = serde_json::from_value(answer["proof"].clone())?;
                        vass_reach::raw_schema::check(
                            &query,
                            &certificate,
                            deadline,
                            args.max_states.saturating_mul(100),
                        )?;
                    } else {
                        let certificate = serde_json::from_value(answer["proof"].clone())?;
                        vass_reach::raw_invariant::check(
                            &query,
                            &certificate,
                            deadline,
                            args.max_states.saturating_mul(100),
                        )?;
                    }
                }
                Some("reachable") => {
                    let trace: Vec<usize> = serde_json::from_value(answer["trace"].clone())?;
                    let marking = query.net().check_witness(&trace)?;
                    anyhow::ensure!(
                        query.accepts(&marking, deadline, args.max_states.saturating_mul(10))?,
                        "raw witness misses target"
                    );
                }
                _ => bail!("raw verification requires a definitive verdict"),
            }
            println!("{{\"verified\":true}}");
            return Ok(());
        }
        let parse_seconds = start.elapsed().as_secs_f64();
        let solve_start = Instant::now();
        let negative_method = match args.method.as_str() {
            "raw-adaptive-groups" | "raw-portfolio-adaptive-groups" => RawNegativeMethod::Groups,
            "raw-adaptive" | "raw-portfolio-adaptive" => RawNegativeMethod::Adaptive,
            _ => RawNegativeMethod::Structural,
        };
        let (out, proof) = if matches!(
            args.method.as_str(),
            "raw-negative" | "raw-adaptive" | "raw-adaptive-groups"
        ) {
            solve_raw_negative(
                &query,
                start + timeout_from(args.seconds)?,
                args.max_states,
                negative_method,
            )?
        } else if matches!(
            args.method.as_str(),
            "raw-portfolio"
                | "raw-portfolio-balanced"
                | "raw-portfolio-adaptive"
                | "raw-portfolio-adaptive-groups"
        ) {
            let deadline = start + timeout_from(args.seconds)?;
            let balanced = args.method == "raw-portfolio-balanced";
            let mut out = search::Outcome::unknown(&args.method, "no candidate yet", 0);
            let mut proof = None;
            if balanced {
                let remaining = deadline.saturating_duration_since(Instant::now());
                out = vass_reach::raw_potential::solve(
                    &query,
                    (remaining / 8).min(Duration::from_secs(2)),
                    args.max_states,
                );
            }
            if out.verdict == "unknown" {
                let remaining = deadline.saturating_duration_since(Instant::now());
                let negative_time = if balanced {
                    remaining * 3 / 4
                } else {
                    remaining / 4
                };
                (out, proof) = solve_raw_negative(
                    &query,
                    Instant::now() + negative_time,
                    args.max_states,
                    negative_method,
                )?;
            }
            if out.verdict == "unknown" {
                proof = None;
                out = vass_reach::raw_potential::solve(
                    &query,
                    deadline.saturating_duration_since(Instant::now()),
                    args.max_states,
                );
            }
            out.method = args.method.clone();
            (out, proof)
        } else if matches!(
            args.method.as_str(),
            "raw-potential" | "portfolio-next" | "portfolio-v2"
        ) {
            (
                vass_reach::raw_potential::solve(
                    &query,
                    timeout_from(args.seconds)?,
                    args.max_states,
                ),
                None,
            )
        } else {
            (
                vass_reach::raw_search::solve(
                    &query,
                    timeout_from(args.seconds)?,
                    args.max_states,
                    args.method != "raw-bfs",
                ),
                None,
            )
        };
        let output = RawOutput {
            outcome: out,
            proof,
            parse_seconds,
            solve_seconds: solve_start.elapsed().as_secs_f64(),
        };
        let mut stdout = std::io::BufWriter::new(std::io::stdout().lock());
        serde_json::to_writer(&mut stdout, &output)?;
        writeln!(stdout)?;
        stdout.flush()?;
        return Ok(());
    }
    anyhow::ensure!(
        !matches!(
            args.method.as_str(),
            "raw-bfs"
                | "raw-search"
                | "raw-potential"
                | "raw-negative"
                | "raw-portfolio"
                | "raw-portfolio-balanced"
                | "raw-adaptive"
                | "raw-portfolio-adaptive"
                | "raw-adaptive-groups"
                | "raw-portfolio-adaptive-groups"
        ),
        "raw methods require --raw"
    );
    let problem: Problem = if let Some(path) = &args.json {
        serde_json::from_str(&fs::read_to_string(path)?)?
    } else {
        input::parse(
            &fs::read_to_string(args.net.as_ref().context("--net or --json is required")?)?,
            &fs::read_to_string(args.xml.as_ref().context("--xml is required with --net")?)?,
        )?
    };
    problem.validate()?;
    if let Some(path) = &args.export_json {
        fs::write(path, serde_json::to_string_pretty(&problem)?)?;
    }
    if let Some(path) = &args.verify {
        let v: serde_json::Value = serde_json::from_str(&fs::read_to_string(path)?)?;
        match v["verdict"].as_str() {
            Some("reachable") => {
                complete::check_witness(
                    &problem,
                    &serde_json::from_value::<Vec<usize>>(v["trace"].clone())?,
                )
                .map_err(anyhow::Error::msg)?;
            }
            Some("unreachable") if v.get("proof").is_some() => {
                verify_proof(
                    &problem,
                    &v["proof"],
                    start + timeout_from(args.seconds)?,
                    0,
                )?;
            }
            Some("unreachable") => state_equation::verify_certificate(
                &problem,
                &serde_json::from_value::<Vec<String>>(v["certificate"].clone())?,
            )?,
            _ => bail!("no verifiable certificate"),
        }
        println!("{{\"verified\":true}}");
        return Ok(());
    }
    let parse_seconds = start.elapsed().as_secs_f64();
    let solve_start = Instant::now();
    let timeout = Duration::try_from_secs_f64(args.seconds)?;
    let out = solve_problem(&problem, &args, timeout);
    let mut result = serde_json::to_value(&out)?;
    result["parse_seconds"] = json!(parse_seconds);
    result["solve_seconds"] = json!(solve_start.elapsed().as_secs_f64());
    result["places"] = json!(problem.places.len());
    result["transitions"] = json!(problem.transitions.len());
    println!("{}", result);
    Ok(())
}

fn verify_proof(
    problem: &Problem,
    proof: &serde_json::Value,
    deadline: Instant,
    depth: usize,
) -> Result<()> {
    anyhow::ensure!(Instant::now() < deadline, "proof verification deadline");
    match proof["kind"].as_str() {
        Some("grouped-excess-v1") => {
            vass_reach::grouped_excess::verify(problem, proof, deadline)?;
        }
        Some("finite-closure-v1") => {
            vass_reach::reduced_bfs::verify_closure(problem, proof, deadline)?;
        }
        Some("buffer-agglomeration-v1") => {
            anyhow::ensure!(depth < 32, "reduction proof nesting limit");
            let (prepared, inner) = vass_reach::buffer_agglomeration::verify_reduction(
                problem, proof, deadline, 20_000_000,
            )?;
            verify_proof(&prepared.problem, inner, deadline, depth + 1)?;
        }
        Some("target-path-potential-v1") => {
            anyhow::ensure!(depth < 32, "reduction proof nesting limit");
            let (prepared, inner) = vass_reach::target_path_potential::verify_reduction(
                problem, proof, deadline, 20_000_000,
            )?;
            verify_proof(&prepared.problem, inner, deadline, depth + 1)?;
        }
        Some("target-path-potential-infeasible-v1") => {
            vass_reach::target_path_potential::verify_infeasible(
                problem, proof, deadline, 20_000_000,
            )?;
        }
        Some("target-zero-trap-v1") => {
            anyhow::ensure!(depth < 32, "reduction proof nesting limit");
            let (prepared, inner) = vass_reach::target_zero_trap::verify_reduction(
                problem, proof, deadline, 20_000_000,
            )?;
            verify_proof(&prepared.problem, inner, deadline, depth + 1)?;
        }
        Some("target-zero-trap-marked-v1") => {
            vass_reach::target_zero_trap::verify_marked(problem, proof, deadline, 20_000_000)?;
        }
        Some("relevance-v1") => {
            anyhow::ensure!(depth < 32, "relevance proof nesting limit");
            let (prepared, inner) =
                vass_reach::relevance::verify_reduction(problem, proof, deadline, 20_000_000)?;
            verify_proof(&prepared.problem, inner, deadline, depth + 1)?;
        }
        Some("state-equation-v1") => {
            let fields = proof.as_object().context("invalid state equation proof")?;
            anyhow::ensure!(
                fields.len() == 2 && fields.contains_key("certificate"),
                "invalid state equation proof fields"
            );
            state_equation::verify_certificate(
                problem,
                &serde_json::from_value::<Vec<String>>(proof["certificate"].clone())?,
            )?;
        }
        Some("signed-threshold-invariant-v1") => vass_reach::signed_threshold::verify(
            problem,
            &serde_json::from_value(proof.clone())?,
            deadline,
        )?,
        Some("phase-pair-closure-v1") => vass_reach::phase_pair::verify(
            problem,
            &serde_json::from_value(proof.clone())?,
            deadline,
        )?,
        Some("local-closure-v1") => vass_reach::local_closure::verify_certificate(problem, proof)?,
        Some("dag-cnf-rup-v1" | "dag-cnf-rup-v2") => {
            vass_reach::dag_solve::verify_certificate(problem, proof)?
        }
        Some("threshold-closure-v1") => cegar::verify_certificate(problem, proof)?,
        Some("integer-cuts-v1") => integer_equation::verify_certificate(problem, proof)?,
        Some("finite-token-cut-v1") => {
            vass_reach::token_cut::verify_finite_certificate(problem, proof)?
        }
        Some("lazy-finite-token-cut-v1") => {
            vass_reach::lazy_token_cut::verify_certificate(problem, proof)?
        }
        Some("bounded-token-cut-v1") => {
            vass_reach::token_cut::verify_bounded_certificate(problem, proof)?
        }
        Some("token-cut-v1") => vass_reach::token_cut::verify_certificate(problem, proof)?,
        Some("token-moment-v1") => vass_reach::token_flow::verify_certificate(problem, proof)?,
        Some("causal-state-equation-v1") => vass_reach::causal::verify_certificate(problem, proof)?,
        Some("sparse-farkas-v1") => vass_reach::linear::verify_certificate(problem, proof)?,
        Some("projected-closure-v1") => vass_reach::projection::verify_certificate(problem, proof)?,
        Some("interval-invariant-v1") => vass_reach::interval::verify_certificate(problem, proof)?,
        Some("marked-traps") => structural::verify_certificate(problem, proof)?,
        Some("empty-siphon") => structural::verify_support_certificate(problem, proof)?,
        _ => bail!("unsupported proof kind"),
    }
    anyhow::ensure!(Instant::now() < deadline, "proof verification deadline");
    Ok(())
}

fn solve_problem(problem: &Problem, args: &Args, timeout: Duration) -> search::Outcome {
    let timeout = if args.method == "portfolio-excess" {
        let start = Instant::now();
        let out = profile_phase("grouped_excess::solve", || {
            vass_reach::grouped_excess::solve(
                problem,
                (timeout / 10).min(Duration::from_millis(100)),
                args.max_states.saturating_mul(20).min(20_000_000),
            )
        });
        if out.verdict != "unknown" {
            return out;
        }
        timeout.saturating_sub(start.elapsed())
    } else {
        timeout
    };
    if !args.target_zero_trap {
        return solve_with_target_path_potential(problem, args, timeout);
    }
    use vass_reach::target_zero_trap::{self, Preparation};
    let start = Instant::now();
    let deadline = start + timeout;
    let work = args.max_states.saturating_mul(100).min(20_000_000);
    let prepared = target_zero_trap::prepare(
        problem,
        start + (timeout / 10).min(Duration::from_millis(100)),
        work,
    );
    if std::env::var_os("VASS_PORTFOLIO_PROFILE").is_some() {
        let detail = match &prepared {
            Ok(Preparation::Marked { trap }) => {
                json!({"initially_marked":true,"trap_places":trap.len()})
            }
            Ok(Preparation::Reduced(p)) => {
                json!({"initially_marked":false,"trap_places":p.trap.len(),
                "retained_places":p.places.len(),"retained_transitions":p.transitions.len()})
            }
            Err(error) => json!({"fallback":error.to_string()}),
        };
        eprintln!(
            "{}",
            json!({"event":"target-zero-trap", "phase_seconds":start.elapsed().as_secs_f64(),
            "original_places":problem.places.len(),"original_transitions":problem.transitions.len(),"detail":detail})
        );
    }
    let prepared = match prepared {
        Ok(Preparation::Marked { trap }) => {
            let proof = json!({"kind":"target-zero-trap-marked-v1","trap":trap});
            if let Err(error) = target_zero_trap::verify_marked(problem, &proof, deadline, work) {
                return search::Outcome::unknown("target-zero-trap", &error.to_string(), 0);
            }
            let mut answer = search::Outcome::unknown(
                "target-zero-trap",
                "initially marked trap is required empty at target",
                0,
            );
            answer.verdict = "unreachable";
            answer.proof = Some(proof);
            return answer;
        }
        Ok(Preparation::Reduced(p)) if !p.trap.is_empty() => p,
        _ => {
            return solve_with_target_path_potential(
                problem,
                args,
                deadline.saturating_duration_since(Instant::now()),
            );
        }
    };
    let answer = solve_with_target_path_potential(
        &prepared.problem,
        args,
        deadline.saturating_duration_since(Instant::now()),
    );
    lift_target_reduction(
        TargetReduction::Trap(prepared),
        problem,
        answer,
        deadline,
        work,
    )
}

enum TargetReduction {
    Trap(vass_reach::target_zero_trap::Prepared),
    Potential(vass_reach::target_path_potential::Prepared),
    Buffer(vass_reach::buffer_agglomeration::Prepared),
}

impl TargetReduction {
    fn engine(&self) -> &'static str {
        match self {
            Self::Trap(_) => "target-zero-trap",
            Self::Potential(_) => "target-path-potential",
            Self::Buffer(_) => "buffer-agglomeration",
        }
    }

    fn lift_witness(
        &self,
        original: &Problem,
        trace: &[usize],
        deadline: Instant,
        work: usize,
    ) -> Result<(Vec<usize>, Vec<u64>)> {
        match self {
            Self::Trap(p) => p.lift_witness(original, trace, deadline, work),
            Self::Potential(p) => p.lift_witness(original, trace, deadline, work),
            Self::Buffer(p) => p.lift_witness(original, trace, deadline, work),
        }
    }

    fn wrap_proof(
        &self,
        inner: serde_json::Value,
        deadline: Instant,
        work: usize,
    ) -> Result<serde_json::Value> {
        match self {
            Self::Trap(p) => p.wrap_proof(inner, deadline, work),
            Self::Potential(p) => p.wrap_proof(inner, deadline, work),
            Self::Buffer(p) => p.wrap_proof(inner, deadline, work),
        }
    }
}

fn lift_target_reduction(
    prepared: TargetReduction,
    problem: &Problem,
    mut answer: search::Outcome,
    deadline: Instant,
    work: usize,
) -> search::Outcome {
    let lifted = match answer.verdict {
        "reachable" => prepared
            .lift_witness(problem, &answer.trace, deadline, work)
            .map(|(trace, marking)| {
                answer.trace = trace;
                answer.marking = Some(marking);
            }),
        "unreachable" => {
            let inner = answer.proof.take().or_else(|| {
                answer.certificate.take().map(
                    |certificate| json!({"kind":"state-equation-v1","certificate":certificate}),
                )
            });
            match inner {
                Some(proof) => prepared
                    .wrap_proof(proof, deadline, work)
                    .map(|proof| answer.proof = Some(proof)),
                None => Err(anyhow::anyhow!("missing reduced proof")),
            }
        }
        _ => return answer,
    };
    if let Err(error) = lifted {
        return search::Outcome::unknown(
            prepared.engine(),
            &format!("lifting: {error}"),
            answer.states,
        );
    }
    if Instant::now() >= deadline {
        return search::Outcome::unknown(prepared.engine(), "lifting deadline", answer.states);
    }
    answer
}

fn solve_with_target_path_potential(
    problem: &Problem,
    args: &Args,
    timeout: Duration,
) -> search::Outcome {
    if !args.target_path_potential {
        return solve_with_buffer_agglomeration(problem, args, timeout);
    }
    use vass_reach::target_path_potential::{self, Preparation};
    let start = Instant::now();
    let deadline = start + timeout;
    let work = args.max_states.saturating_mul(100).min(20_000_000);
    let prepared = target_path_potential::prepare(
        problem,
        start + (timeout / 10).min(Duration::from_millis(100)),
        work,
    );
    if std::env::var_os("VASS_PORTFOLIO_PROFILE").is_some() {
        let detail = match &prepared {
            Ok(Some(Preparation::Infeasible)) => json!({"infeasible":true}),
            Ok(Some(Preparation::Reduced(p))) => json!({"slack":p.problem.initial.last()}),
            Ok(None) => json!({"applicable":false}),
            Err(error) => json!({"fallback":error.to_string()}),
        };
        eprintln!(
            "{}",
            json!({"event":"target-path-potential",
            "phase_seconds":start.elapsed().as_secs_f64(),"detail":detail})
        );
    }
    let prepared = match prepared {
        Ok(Some(Preparation::Infeasible)) => {
            let proof = json!({"kind":"target-path-potential-infeasible-v1"});
            if let Err(error) =
                target_path_potential::verify_infeasible(problem, &proof, deadline, work)
            {
                return search::Outcome::unknown("target-path-potential", &error.to_string(), 0);
            }
            let mut answer = search::Outcome::unknown(
                "target-path-potential",
                "nondecreasing total exceeds target upper bound",
                0,
            );
            answer.verdict = "unreachable";
            answer.proof = Some(proof);
            return answer;
        }
        Ok(Some(Preparation::Reduced(p))) => p,
        _ => {
            return solve_with_buffer_agglomeration(
                problem,
                args,
                deadline.saturating_duration_since(Instant::now()),
            );
        }
    };
    let answer = solve_with_buffer_agglomeration(
        &prepared.problem,
        args,
        deadline.saturating_duration_since(Instant::now()),
    );
    lift_target_reduction(
        TargetReduction::Potential(prepared),
        problem,
        answer,
        deadline,
        work,
    )
}

fn solve_with_buffer_agglomeration(
    problem: &Problem,
    args: &Args,
    timeout: Duration,
) -> search::Outcome {
    if !args.buffer_agglomeration {
        return solve_problem_inner(problem, args, timeout);
    }
    let start = Instant::now();
    let deadline = start + timeout;
    let work = args.max_states.saturating_mul(100).min(20_000_000);
    let prepared = vass_reach::buffer_agglomeration::prepare(
        problem,
        start + (timeout / 10).min(Duration::from_millis(100)),
        work,
    );
    if std::env::var_os("VASS_PORTFOLIO_PROFILE").is_some() {
        let detail = match &prepared {
            Ok(Some(p)) => json!({"steps":p.steps.len(),
                "retained_places":p.problem.places.len(),
                "retained_transitions":p.problem.transitions.len()}),
            Ok(None) => json!({"applicable":false}),
            Err(error) => json!({"fallback":error.to_string()}),
        };
        eprintln!(
            "{}",
            json!({"event":"buffer-agglomeration",
            "phase_seconds":start.elapsed().as_secs_f64(),"detail":detail})
        );
    }
    let prepared = match prepared {
        Ok(Some(p)) => p,
        _ => {
            return solve_problem_inner(
                problem,
                args,
                deadline.saturating_duration_since(Instant::now()),
            );
        }
    };
    let answer = solve_problem_inner(
        &prepared.problem,
        args,
        deadline.saturating_duration_since(Instant::now()),
    );
    lift_target_reduction(
        TargetReduction::Buffer(prepared),
        problem,
        answer,
        deadline,
        work,
    )
}

fn solve_problem_inner(problem: &Problem, args: &Args, timeout: Duration) -> search::Outcome {
    let solve_start = Instant::now();
    match args.method.as_str() {
        "walk" => vass_reach::walk::solve(
            problem,
            timeout,
            args.max_states,
            vass_reach::walk::Options {
                seed: args.walk_seed,
                restart_steps: args.walk_restart_steps,
            },
        ),
        "kosaraju" => complete::solve(
            problem,
            if args.unlimited { None } else { Some(timeout) },
            if args.unlimited {
                None
            } else {
                Some(args.max_states)
            },
            if args.unlimited {
                None
            } else {
                Some(args.max_rows)
            },
        ),
        "portfolio-next" => next_portfolio(problem, timeout, args.max_states, args.max_rows),
        "projected-cegar" => vass_reach::projection::solve(problem, timeout, args.max_states),
        "sparse-state-equation" => vass_reach::linear::solve(problem, timeout),
        "sparse-count-plan" => count_plan::solve_sparse(problem, timeout, args.max_states),
        "sparse-count-plan-budget" => {
            count_plan::solve_sparse_with_state_budget(problem, timeout, args.max_states)
        }
        "frontier-count-plan" => {
            vass_reach::frontier_counts::solve(problem, timeout, args.max_states)
        }
        "frontier-count-plan-expanded" => {
            vass_reach::frontier_counts::solve_expanded(problem, timeout, args.max_states)
        }
        "causal-state-equation" => vass_reach::causal::solve(problem, timeout, args.max_states),
        "token-moment" => vass_reach::token_flow::solve(problem, timeout),
        "token-cut" => vass_reach::token_cut::solve(problem, timeout),
        "finite-token-cut" => with_relevance(
            problem,
            timeout,
            args.max_states.saturating_mul(100),
            "finite-token-cut",
            vass_reach::token_cut::solve_finite,
        ),
        "lazy-finite-token-cut" => with_relevance(
            problem,
            timeout,
            args.max_states.saturating_mul(100),
            "lazy-finite-token-cut",
            vass_reach::lazy_token_cut::solve,
        ),
        "bounded-token-cut" => vass_reach::token_cut::solve_bounded(problem, timeout),
        "portfolio-v3" => sparse_portfolio(problem, timeout, args.max_states, args.max_rows),
        "portfolio-causal" => causal_portfolio(
            problem,
            timeout,
            args.max_states,
            args.max_rows,
            CausalContinuation::Existing,
        ),
        "portfolio-relaxed" => causal_portfolio(
            problem,
            timeout,
            args.max_states,
            args.max_rows,
            CausalContinuation::Relaxed,
        ),
        "dag-sat" => vass_reach::dag_solve::solve(problem, timeout, args.max_states),
        "portfolio-symbolic" => {
            symbolic_portfolio(problem, timeout, args.max_states, args.max_rows)
        }
        "grouped-excess" => {
            vass_reach::grouped_excess::solve(problem, timeout, args.max_states.saturating_mul(100))
        }
        "portfolio-walk" | "portfolio-walk-counts" | "portfolio-reduced" | "portfolio-excess" => {
            let deadline = solve_start + timeout;
            let candidate = vass_reach::walk::solve(
                problem,
                (timeout / 10).min(Duration::from_millis(100)),
                args.max_states,
                vass_reach::walk::Options {
                    seed: args.walk_seed,
                    restart_steps: args.walk_restart_steps,
                },
            );
            if candidate.verdict == "reachable" {
                candidate
            } else {
                if matches!(
                    args.method.as_str(),
                    "portfolio-walk-counts" | "portfolio-reduced" | "portfolio-excess"
                ) && args.max_states > 0
                    && sparse_precheck_fits(
                        problem,
                        args.max_states.saturating_mul(10).min(100_000),
                    )
                {
                    let remaining = deadline.saturating_duration_since(Instant::now());
                    let out = profile_phase("count_plan::solve_sparse_with_state_budget", || {
                        count_plan::solve_sparse_with_state_budget(
                            problem,
                            (remaining / 5).min(Duration::from_millis(250)),
                            args.max_states,
                        )
                    });
                    if out.verdict == "reachable" {
                        return out;
                    }
                }
                if matches!(
                    args.method.as_str(),
                    "portfolio-reduced" | "portfolio-excess"
                ) {
                    let remaining = deadline.saturating_duration_since(Instant::now());
                    let out = profile_phase("reduced_bfs::solve", || {
                        vass_reach::reduced_bfs::solve(
                            problem,
                            (remaining / 3).min(Duration::from_secs(1)),
                            args.max_states,
                        )
                    });
                    if out.verdict != "unknown" {
                        return out;
                    }
                }
                relevant_portfolio(
                    problem,
                    deadline.saturating_duration_since(Instant::now()),
                    args.max_states,
                    args.max_rows,
                    CausalContinuation::LocalBatched,
                )
            }
        }
        "portfolio-prechecked-walk" => with_relevance(
            problem,
            timeout,
            args.max_states.saturating_mul(100),
            "portfolio-prechecked-walk",
            |relevant, remaining| prechecked_walk_portfolio(relevant, args, remaining),
        ),
        "portfolio-batched" => relevant_portfolio(
            problem,
            timeout,
            args.max_states,
            args.max_rows,
            CausalContinuation::LocalBatched,
        ),
        "relaxed-batched" => vass_reach::relaxed::solve_batched(problem, timeout, args.max_states),
        "portfolio-focused" => relevant_portfolio(
            problem,
            timeout,
            args.max_states,
            args.max_rows,
            CausalContinuation::LocalFocused,
        ),
        "portfolio-stubborn" => relevant_portfolio(
            problem,
            timeout,
            args.max_states,
            args.max_rows,
            CausalContinuation::LocalStubborn,
        ),
        "portfolio-target-stubborn" => relevant_portfolio(
            problem,
            timeout,
            args.max_states,
            args.max_rows,
            CausalContinuation::LocalTargetStubborn,
        ),
        "portfolio-local" => causal_portfolio(
            problem,
            timeout,
            args.max_states,
            args.max_rows,
            CausalContinuation::LocalRelaxed,
        ),
        "portfolio-v2" => improved_portfolio(problem, timeout, args.max_states, args.max_rows),
        "interval-invariant" => {
            vass_reach::interval::solve(problem, timeout, args.max_states, args.max_rows)
        }
        "count-plan" => count_plan::solve(problem, timeout, args.max_states, args.max_rows),
        "reduced-guided" => reduced::solve(problem, timeout, args.max_states),
        "bounded-guided" => guided::solve_bounded(problem, timeout, args.max_states),
        "guided-quotient" => guided::solve_quotient(problem, timeout, args.max_states),
        "guided" => guided::solve(problem, timeout, args.max_states),
        "walk-guided" | "walk-incremental" => {
            let solve = if args.method == "walk-guided" {
                vass_reach::walk::solve_guided
            } else {
                vass_reach::walk::solve_incremental
            };
            solve(
                problem,
                timeout,
                args.max_states,
                vass_reach::walk::Options {
                    seed: args.walk_seed,
                    restart_steps: args.walk_restart_steps,
                },
            )
        }
        "signed-threshold" | "signed-threshold-unary" => vass_reach::signed_threshold::solve(
            problem,
            timeout,
            args.max_states,
            if args.method == "signed-threshold" {
                2
            } else {
                1
            },
        ),
        "capacity" => {
            vass_reach::capacity::solve(problem, timeout, args.max_states.saturating_mul(20))
        }
        "phase-pair" => vass_reach::phase_pair::solve(problem, timeout, args.max_states),
        "pair" => vass_reach::phase_pair::solve_uniform(problem, timeout, args.max_states),
        "local-closure" => vass_reach::local_closure::solve(problem, timeout, args.max_states),
        "relaxed" => vass_reach::relaxed::solve(problem, timeout, args.max_states),
        "relaxed-focused" => vass_reach::relaxed::solve_focused(problem, timeout, args.max_states),
        "relaxed-stubborn" => {
            vass_reach::relaxed::solve_stubborn(problem, timeout, args.max_states)
        }
        "relaxed-target-stubborn" => {
            vass_reach::relaxed::solve_target_stubborn(problem, timeout, args.max_states)
        }
        "backward" => backward::solve(problem, timeout, args.max_states),
        "quotient-bfs" => quotient::solve(problem, timeout, args.max_states),
        "cegar" => cegar::solve(problem, timeout, args.max_states),
        "reduced-bfs" => vass_reach::reduced_bfs::solve(problem, timeout, args.max_states),
        "bfs" => search::solve(problem, false, timeout, args.max_states),
        "best-first" => search::solve(problem, true, timeout, args.max_states),
        "state-equation" => state_equation::solve(problem, timeout, args.max_rows),
        "integer-state-equation" => integer_equation::solve(problem, timeout, args.max_rows),
        "marked-traps" => structural::solve(problem, timeout, args.max_rows),
        "support" => structural::solve_support(problem, timeout, args.max_rows),
        "klm-schemes" => klmst::solve(problem, timeout, args.max_states),
        "portfolio" => portfolio(problem, timeout, args.max_states, args.max_rows, false),
        "portfolio-cegar" => portfolio(problem, timeout, args.max_states, args.max_rows, true),
        _ => {
            let first = search::solve(
                problem,
                false,
                timeout.min(Duration::from_millis(100)),
                args.max_states.min(10_000),
            );
            if first.verdict != "unknown" {
                first
            } else {
                let second = state_equation::solve(
                    problem,
                    timeout
                        .saturating_sub(solve_start.elapsed())
                        .min(Duration::from_millis(500)),
                    args.max_rows,
                );
                if second.verdict != "unknown" {
                    second
                } else {
                    search::solve(
                        problem,
                        true,
                        timeout.saturating_sub(solve_start.elapsed()),
                        args.max_states,
                    )
                }
            }
        }
    }
}

fn profile_phase(name: &str, work: impl FnOnce() -> search::Outcome) -> search::Outcome {
    if std::env::var_os("VASS_PORTFOLIO_PROFILE").is_none() {
        return work();
    }
    static START: std::sync::OnceLock<Instant> = std::sync::OnceLock::new();
    let origin = START.get_or_init(Instant::now);
    let start = Instant::now();
    eprintln!(
        "{}",
        json!({"event":"phase-start", "name":name,
        "elapsed_seconds":origin.elapsed().as_secs_f64()})
    );
    let result = work();
    eprintln!(
        "{}",
        json!({"event":"phase-end", "name":name,
        "elapsed_seconds":origin.elapsed().as_secs_f64(), "phase_seconds":start.elapsed().as_secs_f64(),
        "verdict":result.verdict, "reason":result.reason, "states":result.states})
    );
    result
}

fn portfolio(
    p: &Problem,
    timeout: Duration,
    max_states: usize,
    max_rows: usize,
    use_cegar: bool,
) -> search::Outcome {
    let start = Instant::now();
    let budget = |fraction: f64| {
        timeout
            .saturating_sub(start.elapsed())
            .min(timeout.mul_f64(fraction))
    };
    let out = profile_phase("search::solve", || {
        search::solve(p, false, budget(0.05), max_states.min(10_000))
    });
    if out.verdict != "unknown" {
        return out;
    }
    let out = profile_phase("integer_equation::solve", || {
        integer_equation::solve(p, budget(0.2), max_rows)
    });
    if out.verdict != "unknown" {
        return out;
    }
    let out = profile_phase("structural::solve", || {
        structural::solve(p, budget(0.15), max_rows)
    });
    if out.verdict != "unknown" {
        return out;
    }
    let out = profile_phase("structural::solve_support", || {
        structural::solve_support(p, budget(0.1), max_rows)
    });
    if out.verdict != "unknown" {
        return out;
    }
    let out = profile_phase("search::solve", || {
        search::solve(p, false, budget(0.25), max_states)
    });
    if out.verdict != "unknown" {
        return out;
    }
    let out = if use_cegar {
        profile_phase("cegar::solve", || {
            cegar::solve(p, timeout.saturating_sub(start.elapsed()), max_states)
        })
    } else {
        profile_phase("klmst::solve", || {
            klmst::solve(p, timeout.saturating_sub(start.elapsed()), max_states)
        })
    };
    if out.verdict != "unknown" {
        return out;
    }
    profile_phase("complete::solve", || {
        complete::solve(
            p,
            Some(timeout.saturating_sub(start.elapsed())),
            Some(max_states),
            Some(max_rows),
        )
    })
}

fn next_portfolio(
    p: &Problem,
    timeout: Duration,
    max_states: usize,
    max_rows: usize,
) -> search::Outcome {
    let start = Instant::now();
    let budget = |fraction: f64| {
        timeout
            .saturating_sub(start.elapsed())
            .min(timeout.mul_f64(fraction))
    };
    let out = profile_phase("search::solve", || {
        search::solve(p, false, budget(0.025), max_states.min(2000))
    });
    if out.verdict != "unknown" {
        return out;
    }
    let out = profile_phase("integer_equation::solve", || {
        integer_equation::solve(p, budget(0.2), max_rows)
    });
    if out.verdict != "unknown" {
        return out;
    }
    let out = profile_phase("structural::solve", || {
        structural::solve(p, budget(0.1), max_rows)
    });
    if out.verdict != "unknown" {
        return out;
    }
    let out = profile_phase("reduced::solve", || {
        reduced::solve(p, budget(0.15), max_states)
    });
    if out.verdict != "unknown" {
        return out;
    }
    let out = profile_phase("guided::solve", || {
        guided::solve(p, budget(0.35), max_states)
    });
    if out.verdict != "unknown" {
        return out;
    }
    let out = profile_phase("count_plan::solve", || {
        count_plan::solve(p, budget(0.1), max_states, max_rows)
    });
    if out.verdict != "unknown" {
        return out;
    }
    let out = profile_phase("backward::solve", || {
        backward::solve(p, budget(0.1), max_states)
    });
    if out.verdict != "unknown" {
        return out;
    }
    profile_phase("quotient::solve", || {
        quotient::solve(p, timeout.saturating_sub(start.elapsed()), max_states)
    })
}

#[derive(Clone, Copy)]
enum RawNegativeMethod {
    Structural,
    Adaptive,
    Groups,
}

#[derive(serde::Serialize)]
#[serde(untagged)]
enum RawProof {
    Component(vass_reach::raw_invariant::Certificate),
    Automaton(vass_reach::raw_schema::Certificate),
}

#[derive(serde::Serialize)]
struct RawOutput {
    #[serde(flatten)]
    outcome: search::Outcome,
    #[serde(skip_serializing_if = "Option::is_none")]
    proof: Option<RawProof>,
    parse_seconds: f64,
    solve_seconds: f64,
}

fn solve_raw_negative(
    query: &vass_reach::raw_target::RawQuery,
    deadline: Instant,
    max_states: usize,
    negative_method: RawNegativeMethod,
) -> Result<(search::Outcome, Option<RawProof>)> {
    let method = match negative_method {
        RawNegativeMethod::Structural => "raw-negative",
        RawNegativeMethod::Adaptive => "raw-adaptive",
        RawNegativeMethod::Groups => "raw-adaptive-groups",
    };
    let mut out = search::Outcome::unknown(method, "no invariant found", 0);
    if query.target.excluded_automaton.is_some() {
        let discover = match negative_method {
            RawNegativeMethod::Structural => vass_reach::raw_schema::discover,
            RawNegativeMethod::Adaptive => vass_reach::raw_schema::discover_adaptive,
            RawNegativeMethod::Groups => vass_reach::raw_schema::discover_adaptive_groups,
        };
        match discover(query, deadline, max_states.saturating_mul(100)) {
            Ok(certificate) => {
                out.verdict = "unreachable";
                out.reason =
                    "checked serial path schemas and original-net component invariant".into();
                out.states = certificate.invariant.nodes.len();
                return Ok((out, Some(RawProof::Automaton(certificate))));
            }
            Err(error) => out.reason = error.to_string(),
        }
        return Ok((out, None));
    }
    let discover = match negative_method {
        RawNegativeMethod::Structural => vass_reach::raw_negative::discover,
        RawNegativeMethod::Adaptive => vass_reach::raw_negative::discover_adaptive,
        RawNegativeMethod::Groups => vass_reach::raw_negative::discover_adaptive_groups,
    };
    match discover(query, deadline, max_states.saturating_mul(100)) {
        Ok(certificate) => {
            out.verdict = "unreachable";
            out.reason = "checked original-net serial-component invariant".into();
            out.states = certificate.nodes.len();
            return Ok((out, Some(RawProof::Component(certificate))));
        }
        Err(error) => out.reason = error.to_string(),
    }
    Ok((out, None))
}

fn timeout_from(seconds: f64) -> Result<Duration> {
    Ok(Duration::try_from_secs_f64(seconds)?)
}

fn improved_portfolio(
    p: &Problem,
    timeout: Duration,
    max_states: usize,
    max_rows: usize,
) -> search::Outcome {
    let start = Instant::now();
    let budget = |fraction: f64| {
        timeout
            .saturating_sub(start.elapsed())
            .min(timeout.mul_f64(fraction))
    };
    let out = profile_phase("search::solve", || {
        search::solve(p, false, budget(0.02), max_states.min(2000))
    });
    if out.verdict != "unknown" {
        return out;
    }
    if p.places.len() <= 64 {
        let out = profile_phase("vass_reach::interval::solve", || {
            vass_reach::interval::solve(
                p,
                budget(0.15).min(Duration::from_millis(50)),
                max_states,
                max_rows,
            )
        });
        if out.verdict != "unknown" {
            return out;
        }
    }
    let out = profile_phase("vass_reach::projection::solve", || {
        vass_reach::projection::solve(p, budget(0.1).min(Duration::from_millis(50)), max_states)
    });
    if out.verdict != "unknown" {
        return out;
    }
    if p.places.len() <= 128 {
        let out = profile_phase("structural::solve_support", || {
            structural::solve_support(p, budget(0.05).min(Duration::from_millis(25)), max_rows)
        });
        if out.verdict != "unknown" {
            return out;
        }
    }
    next_portfolio(
        p,
        timeout.saturating_sub(start.elapsed()),
        max_states,
        max_rows,
    )
}

fn sparse_portfolio(
    p: &Problem,
    timeout: Duration,
    max_states: usize,
    max_rows: usize,
) -> search::Outcome {
    let start = Instant::now();
    if p.accepts(&p.initial).unwrap_or(false) {
        let mut out = search::Outcome::unknown("initial", "initial marking satisfies target", 1);
        out.verdict = "reachable";
        out.marking = Some(p.initial.clone());
        return out;
    }
    let out = profile_phase("vass_reach::linear::solve", || {
        vass_reach::linear::solve(p, timeout.mul_f64(0.2).min(Duration::from_millis(500)))
    });
    if out.verdict != "unknown" {
        return out;
    }
    improved_portfolio(
        p,
        timeout.saturating_sub(start.elapsed()),
        max_states,
        max_rows,
    )
}

#[derive(Clone, Copy)]
enum CausalContinuation {
    Existing,
    Relaxed,
    LocalRelaxed,
    LocalFocused,
    LocalBatched,
    LocalStubborn,
    LocalTargetStubborn,
}

fn causal_portfolio(
    p: &Problem,
    timeout: Duration,
    max_states: usize,
    max_rows: usize,
    continuation: CausalContinuation,
) -> search::Outcome {
    let start = Instant::now();
    let out = profile_phase("vass_reach::causal::solve", || {
        vass_reach::causal::solve(
            p,
            timeout.mul_f64(0.2).min(Duration::from_millis(500)),
            max_states,
        )
    });
    if out.verdict != "unknown" {
        return out;
    }
    if matches!(
        continuation,
        CausalContinuation::LocalRelaxed
            | CausalContinuation::LocalFocused
            | CausalContinuation::LocalBatched
            | CausalContinuation::LocalStubborn
            | CausalContinuation::LocalTargetStubborn
    ) {
        let remaining = timeout.saturating_sub(start.elapsed());
        let out = profile_phase("vass_reach::local_closure::solve", || {
            vass_reach::local_closure::solve(
                p,
                remaining.mul_f64(0.05).min(Duration::from_millis(100)),
                max_states,
            )
        });
        if out.verdict != "unknown" {
            return out;
        }
    }
    if matches!(
        continuation,
        CausalContinuation::Relaxed
            | CausalContinuation::LocalRelaxed
            | CausalContinuation::LocalFocused
            | CausalContinuation::LocalBatched
            | CausalContinuation::LocalStubborn
            | CausalContinuation::LocalTargetStubborn
    ) {
        let remaining = timeout.saturating_sub(start.elapsed());
        let out = if matches!(continuation, CausalContinuation::LocalTargetStubborn) {
            profile_phase("vass_reach::relaxed::solve_target_stubborn", || {
                vass_reach::relaxed::solve_target_stubborn(p, remaining.mul_f64(0.6), max_states)
            })
        } else if matches!(continuation, CausalContinuation::LocalStubborn) {
            profile_phase("vass_reach::relaxed::solve_stubborn", || {
                vass_reach::relaxed::solve_stubborn(p, remaining.mul_f64(0.6), max_states)
            })
        } else if matches!(continuation, CausalContinuation::LocalBatched) {
            profile_phase("vass_reach::relaxed::solve_batched", || {
                vass_reach::relaxed::solve_batched(p, remaining.mul_f64(0.6), max_states)
            })
        } else if matches!(continuation, CausalContinuation::LocalFocused) {
            profile_phase("vass_reach::relaxed::solve_focused", || {
                vass_reach::relaxed::solve_focused(p, remaining.mul_f64(0.6), max_states)
            })
        } else {
            profile_phase("vass_reach::relaxed::solve", || {
                vass_reach::relaxed::solve(p, remaining.mul_f64(0.6), max_states)
            })
        };
        if out.verdict != "unknown" {
            return out;
        }
    }
    improved_portfolio(
        p,
        timeout.saturating_sub(start.elapsed()),
        max_states,
        max_rows,
    )
}

fn sparse_precheck_fits(p: &Problem, max_work: usize) -> bool {
    let target_rows = p.target.len().saturating_mul(2);
    let mut construction_work = p
        .places
        .len()
        .saturating_add(p.transitions.len())
        .saturating_add(target_rows.saturating_mul(p.places.len()));
    if construction_work > max_work {
        return false;
    }
    for transition in &p.transitions {
        let arcs = transition.pre.len().saturating_add(transition.post.len());
        construction_work =
            construction_work.saturating_add(target_rows.saturating_add(1).saturating_mul(arcs));
        if construction_work > max_work {
            return false;
        }
    }
    true
}

fn prechecked_walk_portfolio(p: &Problem, args: &Args, timeout: Duration) -> search::Outcome {
    let deadline = Instant::now() + timeout;
    // State-equation construction is not interruptible, so cap its expansion first.
    if args.max_states > 0
        && sparse_precheck_fits(p, args.max_states.saturating_mul(10).min(100_000))
    {
        let remaining = deadline.saturating_duration_since(Instant::now());
        let out = profile_phase("precheck::sparse-state-equation", || {
            vass_reach::linear::solve(p, (remaining / 20).min(Duration::from_millis(10)))
        });
        if out.verdict != "unknown" {
            return out;
        }
    }
    let remaining = deadline.saturating_duration_since(Instant::now());
    let candidate = profile_phase("vass_reach::walk::solve", || {
        vass_reach::walk::solve(
            p,
            (remaining / 10).min(Duration::from_millis(100)),
            args.max_states,
            vass_reach::walk::Options {
                seed: args.walk_seed,
                restart_steps: args.walk_restart_steps,
            },
        )
    });
    if candidate.verdict == "reachable" {
        return candidate;
    }
    causal_portfolio(
        p,
        deadline.saturating_duration_since(Instant::now()),
        args.max_states,
        args.max_rows,
        CausalContinuation::LocalBatched,
    )
}

fn relevant_portfolio(
    p: &Problem,
    timeout: Duration,
    max_states: usize,
    max_rows: usize,
    continuation: CausalContinuation,
) -> search::Outcome {
    with_relevance(
        p,
        timeout,
        max_states.saturating_mul(100),
        match continuation {
            CausalContinuation::LocalTargetStubborn => "portfolio-target-stubborn",
            CausalContinuation::LocalBatched => "portfolio-batched",
            CausalContinuation::LocalStubborn => "portfolio-stubborn",
            _ => "portfolio-focused",
        },
        |problem, remaining| {
            causal_portfolio(problem, remaining, max_states, max_rows, continuation)
        },
    )
}

fn with_relevance(
    p: &Problem,
    timeout: Duration,
    work: usize,
    method: &str,
    solve: impl Fn(&Problem, Duration) -> search::Outcome,
) -> search::Outcome {
    let start = Instant::now();
    let deadline = start + timeout;
    let preparation = vass_reach::relevance::prepare(p, (start + timeout / 10).min(deadline), work);
    let original = || solve(p, deadline.saturating_duration_since(Instant::now()));
    let Ok(prepared) = preparation else {
        return original();
    };
    if prepared.places.len() == p.places.len() && prepared.transitions.len() == p.transitions.len()
    {
        return original();
    }
    let mut answer = solve(
        &prepared.problem,
        deadline.saturating_duration_since(Instant::now()),
    );
    let lifted = match answer.verdict {
        "reachable" => {
            prepared
                .lift_witness(p, &answer.trace, deadline, work)
                .map(|(trace, marking)| {
                    answer.trace = trace;
                    answer.marking = Some(marking);
                })
        }
        "unreachable" => {
            let inner = answer.proof.take().or_else(|| {
                answer.certificate.take().map(
                    |certificate| json!({"kind":"state-equation-v1","certificate":certificate}),
                )
            });
            match inner {
                Some(proof) => prepared
                    .wrap_proof(proof, deadline, work)
                    .map(|proof| answer.proof = Some(proof)),
                None => Err(anyhow::anyhow!("missing reduced proof")),
            }
        }
        _ => return answer,
    };
    if let Err(error) = lifted {
        return search::Outcome::unknown(
            method,
            &format!("relevance lifting: {error}"),
            answer.states,
        );
    }
    if Instant::now() >= deadline {
        return search::Outcome::unknown(method, "relevance lifting deadline", answer.states);
    }
    answer
}

fn symbolic_portfolio(
    p: &Problem,
    timeout: Duration,
    max_states: usize,
    max_rows: usize,
) -> search::Outcome {
    let start = Instant::now();
    let out = profile_phase("vass_reach::dag_solve::solve", || {
        vass_reach::dag_solve::solve(p, timeout.mul_f64(0.4), max_states)
    });
    if out.verdict != "unknown" {
        return out;
    }
    relevant_portfolio(
        p,
        timeout.saturating_sub(start.elapsed()),
        max_states,
        max_rows,
        CausalContinuation::LocalFocused,
    )
}
