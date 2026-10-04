# Integrated solver results

The new default `portfolio-next` solves **217/218** exported SER backend queries at two seconds and 200,000 states, compared with **211/218** for the original Rust portfolio and **209/218** for the artifact SMPT STATE-EQUATION+BMC configuration in the same repeated run.

| Method | Reachable | Unreachable | Unknown | Errors/unstable |
|---|---:|---:|---:|---:|
| New Rust portfolio | 20 | 197 | 1 | 0 |
| Previous Rust portfolio | 14 | 197 | 7 | 0 |
| SMPT + Z3 | 12 | 197 | 9 | 0 |

Three repetitions per query; sequential cold processes; method order alternates. There are no conflicting definitive verdicts and no lost solves relative to either baseline. Every definitive native answer passed independent Python verification, including all 60 positive traces across repetitions.

On commonly solved queries, the median wall-time speedup is **25.94× over SMPT** (209 queries) and **1.48× over the previous Rust portfolio** (211 queries). Geometric means are 26.06× and 1.40× respectively. Excluding syntactically false targets, the median speedup over SMPT is 25.49× on 126 commonly solved queries. This is a backend-only, shared-host experiment. It does not establish an end-to-end paper speedup or superiority over all SMPT configurations. The earlier SMPT run solved 210/218; this run's `g4_disjunct_0` also timed out, so coverage depends on the time budget and host conditions.

## New coverage

New solves over the previous two-second Rust portfolio: `c1_disjunct_0`, `e2_disjunct_0`, `e3_disjunct_2`, `e4_disjunct_2`, `g1_disjunct_0`, and `g3_disjunct_1`. These are positive results with replayable witnesses. Only **`g2_disjunct_1` remains unknown**.

The previous five-second/500,000-state experiment solved 215/218. The new solver solves the two additional cases and all earlier positives at the smaller, matched two-second/200,000-state limits.

## What contributed

The default schedule's first repetition discharged 179 queries by integer cuts, 2 by marked traps, 28 by the small BFS, and 8 by the new reduction plus directed/quotient search. The remaining query exhausted the portfolio without an answer. The gains in this run therefore come from the new positive search and reductions, alongside the existing negative proof engines.

The count-plan engine couples integer count candidates with forward/reverse support and memoized exact realization. The backward engine uses exact guarded word summaries. Both are implemented, tested and available independently, but **neither contributed unique coverage in this run**. Pilot count-plan runs on the three previous residuals ran out of arithmetic budget. Do not attribute the measured gains to those components, or to BDDs/PDR/LP-dual learning, which are not implemented.

## Reproduction and checks

```sh
cargo build --release
./target/release/vass-reach --json problem.json --seconds 2
python3 scripts/benchmark.py --methods portfolio-next portfolio smpt \
  --seconds 2 --repeat 3 --output results/integrated-comparison
python3 scripts/summarize.py results/integrated-comparison
```

`--method portfolio` retains the original schedule; the default changed only after the comparison completed. The exact benchmark executable is preserved as `results/integrated-comparison/vass-reach` with its SHA-256 in `environment.json`. Later edits changed the CLI default, formatting and test type aliases; algorithmic code used for the comparison is unchanged.

Tests cover exact summary composition/repetition, read arcs, signed/equality targets, 120 bounded guided-search differential cases, support-family refinements, memoized count realization, source/completion trace lifting, and the no-negative-answer boundary of quotient/bounded search. The full suite passed before the final CLI default change; targeted tests and Clippy were rerun afterward.

[Full tables](integrated-comparison/REPORT.md) · [Design](../research/integrated-solver.md) · [Initial engine pilot](integrated-pilot/runs.jsonl) · [Count-plan and quotient pilot](integrated-pilot2/runs.jsonl)
