# Rust Petri-net reachability experiments

A native Rust reachability portfolio with reproducible benchmarks from SER, the classical SMPT suites, and MCC 2021.

The current ordinary-net solver is `portfolio-excess`. It combines checked
grouped-excess invariants and an early bounded sparse linear refutation with guided witness search from both the original
initial marking and a divided initial marking, followed by reduction and the
existing search portfolio. `--method auto` selects it by default; raw input
continues to select `raw-potential`. All previous named methods remain available.

The development benchmark now contains **368 original properties** (366 distinct
ordered-branch representatives), including a frozen **192-property expansion**
across six additional MCC families. All imports were independently checked; the
22 reserved evaluation families remain untouched. See the
[benchmark selection and audit](research/benchmark-expansion-2026-10-04/README.md).

The measured five-second configuration is:

```bash
cargo build --release
./target/release/vass-reach --pnml model.pnml --xml properties.xml \
  --property-id QUERY_ID --method portfolio-excess --seconds 5 \
  --max-states 2000000 --buffer-agglomeration
```

The latest [VerifyPN-inspired improvement](research/verifypn-learning-20261004/README.md)
solves **364/368 in both five-second repetitions**, versus **363/368** for the
previous solver, with one repeated gain (Railroad-PT-100 RC09) and zero losses.
All 1,454 definitive answers were independently checked. Early state-equation
proofs avoid spending the search budget on linear contradictions; a sparse-work
limit protects large witness-search cases. These are contended development runs,
so the observed timing reductions do not establish an idle-host speedup. See the
[complete paired results](research/verifypn-learning-20261004/full-v3/REPORT.md).

The preceding two complete Mac repetitions solved **363/368 properties in each**, versus **323 and
322/368** for the frozen baseline. There are **40 gains reproduced in both runs
and zero losses**; all 1,371 definitive answers were independently checked.
The [full report](research/grouped-excess-repeat-20261004/REPORT.md) and
[comparison protocol](research/grouped-excess-repeat-20261004/README.md)
compare this frozen candidate with `portfolio-reduced` on all 368 properties,
including original parsing and every property branch in the five-second budget.
Independent original-input certificate and witness checking is timed separately.
The [first grouped-excess screen](research/grouped-excess-20261004/RESULTS.md)
and [subsequent search diagnostics](research/coverage-third-20261004/RESULTS.md)
use distinct binaries and must not be pooled as repeats.

The [current four-tool Linux comparison](research/competitive-linux-20261004/REPORT.md)
completed all 2,944 five-second invocations. Native coverage was **345 and 358/368**,
versus **298/299** for unrestricted VerifyPN, **205/238** for SMPT's portable MCC
configuration, and **267/274** for ITS-Tools MCC. Against VerifyPN there were
49 gains and two losses reproduced in both runs; VerifyPN was about 1.72 times
faster on the 294 properties both methods solved in both runs, excluding native
checking. All 703 definitive native answers were independently checked; external
answers are tool-reported. **These are contended development runs:** the host was
heavily loaded, coverage varied, and an idle-host comparison remains outstanding.
The report preserves the failed original provenance audit and its narrow amendment
for a Z3 identity recorded before launch but omitted from enforced dependency pins.

The [earlier research assessment](research/research-update-2026-10-04.md) preserves
the 4,224-run comparison, boundedness analysis, and unsuccessful count-dominance
experiment. The [harder benchmark catalog](research/harder-test-set-v5.md) and
[ordinary-cohort protocol](research/application-walk-full-v1/README.md) remain
historical evidence. Raw compressed-control experiments are tracked separately,
including the [n5 accounting regression](research/raw-n5-control-diagnostic-v1-report.md).

`portfolio-v2` remains available for the earlier checked interval partitions and
property-directed projections; see its [design](research/solver-v2.md) and
[historical results](results/SOLVER-V2.md).

An earlier experimental candidate is `--method portfolio-local`: checked causal count refinement, [necessary local-target closures](research/local-closure.md), [relaxed prerequisite guidance](research/relaxed-witness-search.md), and the existing fallback portfolio. On all 256 development properties, it solved 256 in both five-second original-input repetitions, versus 251 for unrestricted VerifyPN. Every native answer was independently checked. VerifyPN was about 2.12 times faster geometrically on their 251 common solved cases; higher coverage is not a general speedup. See [the complete comparison](results/publication-local-development/REPORT.md). On the separate 256-property evaluation set, the same frozen candidate solved 251, versus 254 for unrestricted VerifyPN and 170 for frozen-v2, consistently across two repetitions with no definitive disagreements. See [the evaluation comparison](results/publication-local-evaluation/REPORT.md).

Research development continues in [the current progress record](research/publication-progress.md). [Causal proof trees](research/causal-state-equation.md) combine support refinements with exact arithmetic. [Token moments](research/token-moment.md), [lazy flow cuts](research/token-cut.md), and [certified finite token bounds](research/bounded-token-cut.md) provide separate negative-proof experiments. None is a new complete decision procedure. The [stress expansion](research/stress-benchmark-protocol.md) freezes 23 larger MCC models and 18 raw SER source programs; collection and measured difficulty are separate from input selection.

Performance claims remain exploratory. A process audit found orphaned Tina WALK jobs overlapping several recent measurements; those runs now carry `TIMING-CAVEAT.md` and are being repeated with workload preflight. Older nominal full-SMPT configurations also had missing-dependency/interface failures. See [the evaluation protocol](research/publication-protocol.md) before interpreting historical counts or timings. No broad competitive superiority or publication readiness is established.

Implemented methods:

- `bfs`: explicit breadth-first exploration, shortest witnesses.
- `best-first`: explicit exploration prioritized by target constraint violations.
- `state-equation`: exact rational elimination, equality substitution and dominance reduction, with Farkas certificates.
- `integer-state-equation`: integer elimination with gcd rounding cuts and four elimination orders, with proof DAGs.
- `marked-traps`: marked-trap invariants strengthening the rational state equation.
- `support`: initially empty siphon invariants strengthening the rational state equation.
- `kosaraju`: complete generalized-VASS decomposition with exact native arithmetic and Karp–Miller pumping tests; use `--unlimited` to remove resource budgets.
- `klm-schemes`: exact repeated-word acceleration, mining words up to length four and choosing repetitions from target and enabling constraints; interleaves greedy and FIFO exploration.
- `portfolio`: short BFS, integer arithmetic, marked traps, support, a larger BFS pass, then accelerated search and complete decomposition, sharing one time budget.
- `portfolio-old`: the original BFS/rational/greedy schedule with the current improved rational engine.

**The native `kosaraju` engine implements the complete Kosaraju procedure.** Its unlimited mode removes artificial search budgets; timed runs can return `unknown`. The other engines, including `klm-schemes`, remain incomplete. The portfolio uses Kosaraju as its final fallback if time remains. See [implementation and completeness details](research/complete-implementation.md).

`klm-schemes` is bounded path-scheme search and does not implement generalized VASS decomposition. Its witnesses are capped at one million transitions. `kosaraju` instead uses arbitrary-precision arithmetic and has no such cutoff in unlimited mode. Every returned reachable result is replayed. Kosaraju unreachability results do not yet export a standalone decomposition certificate.

The traditional complete VASS reachability algorithm is **KLMST**, the Mayr/Kosaraju/Lambert decomposition family. Karp–Miller decides coverability and cannot directly answer these exact linear-constraint reachability queries. See the [Pro recommendations](research/pro-answer.md) and [original coverage assessment](research/pro-assessment.md).

## Run

```sh
cargo build --release --locked
./target/release/vass-reach \
  --net benchmarks/serializability/a2/smpt_petri_disjunct_0.net \
  --xml benchmarks/serializability/a2/smpt_constraints_disjunct_0.xml \
  --method portfolio --seconds 2
```

Output is JSON with a three-way verdict, method, reason, counters, timings, and a firing sequence or arithmetic/structural certificate when available. Transition indices refer to input order. Petri-net markings and arc multiplicities use `u64`; target arithmetic is checked; state-equation arithmetic uses arbitrary-precision rationals.

The reader supports the artifact's TINA `.net` subset: `net`, `pl NAME (TOKENS)`, and `tr NAME INPUTS -> OUTPUTS`, including `PLACE*WEIGHT` arcs. Arc-only places start at zero. It preserves read arcs. MCC XML must contain exactly one existential eventuality whose target is a conjunction of linear integer comparisons. Unsupported syntax, unknown places, nonlinear arithmetic, multiple properties, and other temporal operators fail explicitly.

`--export-json problem.json` saves a normalized problem; `--json problem.json` reads it. The library exposes the net representation and solvers separately. A VASS can be encoded as a Petri net with control-state places.

Save a result to `answer.json` and verify it with:

```sh
./target/release/vass-reach --json problem.json --verify answer.json
```

The standalone verifier supports firing sequences, Farkas certificates, integer rounding-cut DAGs, marked traps, empty siphons and threshold abstraction closures. Finite-state exhaustion does **not** yet export a standalone certificate; the benchmark checker independently reconstructs its finite closure up to 200,000 states. `scripts/benchmark.py` additionally verifies these certificates using independent Python code and exact integer/rational arithmetic.

## Reproduce the comparison

Requirements: Rust, Python 3, C/Clang headers, ISL development headers/library, curl/unzip. Homebrew ISL is detected on macOS; elsewhere set `ISL_PREFIX`. The artifact and baseline are downloaded with a pinned SHA-256 and kept under `vendor/`. Existing system dependencies are not installed automatically.

```sh
./scripts/setup.sh
python3 scripts/collect.py --seconds 20 --outer-seconds 40
python3 scripts/benchmark.py --seconds 2 --repeat 3 \
  --methods portfolio smpt --output results/comparison
python3 scripts/summarize.py results/comparison
```

Use `--methods bfs best-first state-equation integer-state-equation marked-traps support klm-schemes portfolio-old portfolio smpt` for an ablation, or `--filter '^(a2|e1|g4)_'` for a focused subset. Processes run sequentially; each pair receives byte-identical input, and input hashes are recorded. Repeat order alternates. Both native and SMPT runs have an outer process-group timeout. SMPT uses the artifact's `STATE-EQUATION BMC` configuration with proof export and Z3 5.1.0.

The comparison measures **backend-only** wall time, including startup and parsing. Internal solver timings are also recorded, but have different boundaries across tools. Frontend compilation, target generation, and frontend proof validation are excluded. Avoid concurrent workloads when timing. Reports use medians over repetitions and distinguish syntactically false targets.

The collector attempts all 47 paper benchmarks. Some are discharged by frontend preprocessing, and some time out. It saves each query emitted before completion, a counterexample, or timeout; it does not force enumeration of all disjuncts. Consequently backend query results do not establish end-to-end serializability performance. Collection logs retain the distinction; the artifact can exit successfully while reporting TIMEOUT.

See [the benchmark report](results/comparison/REPORT.md), [provenance](research/artifact.md), and raw timing records under `results/`. The scratch `results/initial` run used polling-based waits and is diagnostic only.

## Checks

```sh
cargo test
cargo clippy --all-targets -- -D warnings
```

Tests cover read arcs, weighted arcs, exact reachability versus coverability, arithmetic overflow, malformed/unsupported input, Farkas certificate rejection, and differential checks on 120 bounded random nets against an independent exhaustive enumeration.

## Classical SMPT suites

The published TACAS 2022 artifact adds **37 original properties**: NTest (21), Sara (3), TokenTank (6), expressiveness (5), and certificates (2). All import successfully from their original PNML/XML files. The two certificate examples repeat expressiveness examples.

```sh
python3 scripts/setup-smpt-benchmarks.py
python3 scripts/smpt_import.py
python3 scripts/test_smpt_import.py
python3 scripts/benchmark_smpt_classic.py --seconds 2 \
  --methods portfolio-next smpt --output results/smpt-classic
```

The downloader checks a pinned archive hash. The importer preserves the original net and handles both EF reachability and AG invariants. The runner combines disjunctive targets under one property budget and records the original property truth value. Three two-second runs consistently solved 27/37 properties with Rust and 16/37 with SMPT's selected `STATE-EQUATION BMC` configuration, with no definitive disagreements. Every definitive native result was independently checked. See [provenance, semantics, and commands](research/smpt-classic.md) and [results](results/smpt-classic-repeated/REPORT.md).

A broader comparison found that SMPT's available portfolio **without saturated PDR returns 28/37 definitive answers**, consistently across three runs, versus Rust's 27/37. Including saturated PDR returns 35/37 in one run but produces a false unreachability answer contradicted by a checked witness. The 16/37 baseline therefore understates SMPT's capabilities. See [mode results and correctness conflict](research/smpt-modes.md).

## Original-net queries and harder programs

`ser --export-raw` exports one original request-tracking Petri net and its serial semilinear language per program, before complement construction, target decomposition, pruning, or solving. Optional semilinear simplifications are disabled. The solver tests for a completed execution whose response counts lie outside that language.

```sh
./scripts/setup-raw.sh
python3 scripts/generate_harder.py
python3 scripts/collect_raw.py --source benchmarks/harder-programs \
  --extensions .ser --output benchmarks/raw-harder
./target/release/vass-reach --raw benchmarks/raw-harder/monitor_d3_c12/query.json \
  --seconds 2 > answer.json
./target/release/vass-reach --raw benchmarks/raw-harder/monitor_d3_c12/query.json \
  --verify answer.json
vendor/venv/bin/python scripts/benchmark_raw.py --methods raw-bfs raw-potential \
  --repeat 3 --output results/raw-comparison
```

The default raw engine, `raw-potential`, derives linear bounds on serial response counts and searches for violations, then falls back to direct search. Its earlier 24-program comparison found 16 counterexamples versus 10 for raw BFS at two seconds; locked programs were then unresolved.

Use `--method raw-portfolio` for both verdicts. It first searches for a credited component invariant, allocating at most one quarter of the remaining solver budget, then uses `raw-potential` if that search is inconclusive. `--method raw-negative` runs invariant discovery alone. Negative proofs describe finite controller closure and exact affine maps between components of the original serial language; both Rust and Python check the original query. Positive witnesses require independent Python replay and Z3 nonmembership checking.

The frozen portfolio verifies **12/12 valid stress queries twice** at a 10-second input-inclusive deadline: nine positives and three negatives. All 18 selected source programs remain in the denominator; six exports timed out. These are development results on the shared Mac, not independent evaluation or evidence of general superiority. See the [portfolio report](results/raw-stress-portfolio-v1/REPORT.md) and [invariant argument](research/credited-component-invariants.md).

```sh
vendor/venv/bin/python scripts/benchmark_stress_raw.py \
  --corpus benchmarks/raw-stress-v1 --binary results/solver-raw-portfolio-v1/vass-reach \
  --methods raw-portfolio --seconds 10 --memory-mib 2048 --repeat 2 --all-sources \
  --output results/raw-stress-portfolio-rerun
```

These are whole-program queries, distinct from the old 218 simplified disjuncts. See [export semantics and reproduction](research/raw-benchmarks.md) and [measurements and remaining challenges](results/RAW.md).

## Complete-algorithm baseline

The external Haskell KReach implementation supplies an experimental Kosaraju/KLMST-family baseline. The adapted build fails smoke tests with direct read arcs and with multiple control states; benchmark inputs therefore use a single-state consume/produce encoding. Its verdicts remain unverified. Build with `scripts/setup-kreach.sh`; run via `scripts/benchmark.py --methods kreach`. It uses Z3 internally and a compatibility adaptation to the installed GHC/SBV versions. See [build provenance and input encoding](research/kreach-build.md).

`scripts/kreach_adapter.py` reduces signed linear targets to exact final markings and splits transitions into atomic consume/produce phases to preserve read-arc semantics. Conversion is outside the timed process, while parsing and solving the larger net are included. KReach has an external wall-time limit and exports no checked witness/certificate. The native Rust portfolio does not invoke KReach or Z3.

## Latest results

The revised portfolio solves **211/218** exported queries at a two-second limit (14 reachable, 197 unreachable), versus **210/218** for SMPT in three repetitions. `c5_disjunct_0` is solved only by Rust; no definitive verdicts disagree. Median backend wall-time speedup on 210 commonly solved queries is **19.34x** (18.93x excluding syntactically false targets). Other compiler workloads were active, so treat wall timings as exploratory.

See the [complete portfolio report](results/PORTFOLIO.md), [repeated comparison](results/portfolio-comparison/REPORT.md), [all-method ablation](results/portfolio-ablation/REPORT.md), and [implementation details](research/portfolio-implementation.md). The ablation used the initial portfolio schedule; its BFS result motivated the second BFS pass in the final schedule. All standalone engines are unchanged between those runs. This is a backend comparison on the collected query corpus, not an end-to-end paper benchmark result.

The external KReach pass reported 157 unreachable and 61 unknown queries, with no additional coverage. Its adapted build remains unverified; see the correctness caveats in the complete report.

## Complete procedure

```sh
./target/release/vass-reach --json problem.json --method kosaraju --unlimited
```

For bounded experiments use `--method kosaraju --seconds 2`; `--max-states` also limits decomposition/coverability work and `--max-rows` limits exact arithmetic. The full native implementation does not call SMT or KReach. Its worst-case cost is enormous, and witness extraction currently uses exact BFS after reachability is established. See [the design and tests](research/complete-implementation.md).

The complete-engine benchmark at a two-second budget proved 186/218 queries unreachable; the remaining 32 were unknown. The portfolio still solved 211/218, with no conflicting verdicts. All 54 Rust tests and Clippy pass. See [the complete-engine results](results/complete-comparison/REPORT.md). Full completeness is exposed through unlimited mode; short timed runs do not inherit an eventual-decision guarantee.

## CEGAR prototype

Use `--method cegar` for finite threshold abstraction with concrete path replay and counterexample-driven threshold refinement. Negative answers export abstract closure certificates, checked by both `--verify` and the independent Python benchmark checker. `--method portfolio-cegar` combines the existing arithmetic/structural stages with this search. This earlier experiment did not change the default portfolio.

This prototype uses explicit abstract-state BFS. BDDs, residues and relational predicate learning are not implemented. See [the design](research/cegar-implementation.md) and [benchmark results](results/CEGAR.md).

```sh
python3 scripts/benchmark.py --methods cegar portfolio portfolio-cegar \
  --seconds 2 --output results/cegar-comparison
python3 scripts/summarize.py results/cegar-comparison
python3 scripts/test_threshold_checker.py
```

`--max-states` on the benchmark script sets the native engines' state budget (default 200,000). Proof checking runs outside the timed backend process.

The CEGAR comparison solved 153/218 with CEGAR alone and 211/218 with either portfolio at two seconds. A separate full run with the existing portfolio at five seconds and 500,000 states solved **215/218**: increasing the BFS budget found four additional independently checked witnesses. Use `--method portfolio --seconds 5 --max-states 500000` for this configuration. The three remaining unknowns are `c1_disjunct_0`, `e4_disjunct_2`, and `g2_disjunct_1`. See [the experiment report](results/CEGAR.md).

## Prior portfolio

`--method portfolio-next` selects the earlier integrated portfolio; `--method portfolio` preserves its predecessor. It combines integer/trap proofs with source/completion reduction, directed search, shared-count support refinement, exact backward word summaries and sink-counter quotient search.

At **two seconds and 200,000 states**, three repeated runs solved **217/218**, versus **211/218** for the old Rust portfolio and **209/218** for the artifact SMPT configuration in the same run. The new solver lost no old solves. Every definitive native result passed independent Python checking. Median cold-process speedup was **25.94× over SMPT** and **1.48× over the old portfolio** on commonly solved queries. Timings remain exploratory on a shared host; the earlier SMPT run solved 210/218.

```sh
cargo build --release
./target/release/vass-reach --json problem.json --seconds 2
python3 scripts/benchmark.py --methods portfolio-next portfolio smpt \
  --seconds 2 --repeat 3 --output results/integrated-comparison
```

Only `g2_disjunct_1` remains unknown. These are backend measurements, not a general reachability record or an end-to-end serializability result. See [results](results/INTEGRATED.md), [full comparison](results/integrated-comparison/REPORT.md), and [engine design](research/integrated-solver.md).

The [stress expansion](research/stress-collection-results.md) adds 368 imported MCC properties from 23 larger instances and 18 frozen raw serializability sources. Full raw collection produced 12 structurally validated queries and 6 frontend timeouts, all retained. The four-method, ten-second raw pilot leaves 7 of the 12 valid queries unresolved by every tested approach; the 368-property single-core Linux pilot is still running.
