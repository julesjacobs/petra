# Original-net serializability benchmarks

The old corpus contains 218 separately simplified target disjuncts. It loses net structure and queries discarded or never visited by frontend pruning and short-circuiting. The new corpus instead stores one complete question per source program.

## Export boundary

`ser --export-raw` stops after constructing the request-tracking Petri net and the serial-execution Parikh image. It emits the original net and the condition: every local/request place is empty, and the vector of response counts belongs to none of the serial semilinear components. Optional semilinear reductions and Kleene ordering heuristics are disabled. It does not compute an ISL complement, split the target into reachability disjuncts, prune the net, invoke a solver, or use the result cache.

Semantic source compilation and construction of the serial response language remain necessary to state this particular query. Semilinear components encode that language; they are not independently solved reachability subqueries. The frontend can fail before reaching this boundary. Its existing >30-component Kleene-star guard still aborts some inputs, and unsimplified serial-language construction can be exponential. Those outcomes are export failures/timeouts, never solved queries.

The modified vendor frontend is reproducible from `scripts/ser-raw-export.patch` and `scripts/setup-raw.sh`. `vendor/SerializabilityChecker/RAW_EXPORT.md` specifies `ser-raw-v1`. `raw.net` without `query.json` is not the entire question.

## Corpora

- `benchmarks/raw-original`: all 47 original source programs attempted with a five-second frontend limit; 39 exported, five hit the frontend's component limit, three timed out. All statuses and source/query hashes are in `collection.json`. The largest exported serial target has 147,464 components (about 295 MB in pretty JSON).
- `benchmarks/harder-programs` and `benchmarks/raw-harder`: 24 generated programs, all exported. Families are interacting cyclic counters, replicated registers, and phase monitors. Locked/racy pairs have source-level correctness arguments. Sixteen are expected nonserializable and eight serializable; these expectations are not solver results.
- `benchmarks/scaling-programs` and `benchmarks/raw-scaling`: six larger cases generated after freezing the potential-search design, without retuning to those cases. Five exported within ten seconds; the locked domain-31 counter timed out during frontend construction. Exported nets reach 1,570 places. Monitor witnesses require up to 320 advances. These are parameter extrapolations of the same families, not an independent benchmark distribution.

Generation is deterministic; manifests include source hashes, parameters and semantic arguments. Administrative `manifest.json` and `smoke.json` files are not input programs; collect generated sources with `--extensions .ser`.

## Native whole-query support

`vass-reach --raw query.json` evaluates the raw target directly. Exact membership in one linear set searches nonnegative period multiplicities with checked resource budgets, residual memoization, unit-period shortcuts and gcd pruning. It never treats membership timeout as nonmembership. Search caches serial response vectors after a completed marking has been checked.

`raw-bfs` is a direct baseline over original markings. `raw-search` applies request-source/completion reductions with trace recipes, then interleaves completion-directed and FIFO exploration. Response dimensions are protected from elimination. Both return only replayed positive witnesses or unknown: finite exhaustion currently has no raw closure certificate.

`raw-potential` is the new default for raw input. For each selected response coordinate and pairwise difference, it searches for a linear form y such that every period v of every excluded component satisfies y·v <= 0. If b is the maximum y·base across components, all serial response vectors satisfy y·m <= b. Therefore y·m >= b+1 is a sufficient witness goal for the original complement target. These goals guide the existing reduced/directed engine, and all returned traces are replayed against the original net and checked against the full raw target.

This gives useful forbidden-response and response-count-difference goals without constructing the complement or splitting it into an exhaustive DNF. Failure on these sufficient goals proves nothing; the engine falls back to direct whole-query exploration. The current template set uses coordinates and pairwise differences, with bounded candidate count and shared wall time. It does not claim to enumerate all linear consequences or all nonserializable executions.

## Comparisons and evidence

`scripts/benchmark_raw.py` runs sequential cold processes on identical raw JSON bytes. Every positive trace is independently replayed in Python. For the resulting fixed response vector, Z3 checks nonmembership in each excluded linear set by solving its exact nonnegative integer equations. This independent checking is outside solver timing; native search itself does not invoke Z3.

`raw-z3` is a new direct quantified BMC baseline over the same raw net and target. It is **not SMPT**. SMPT's old input path expects the already compiled target, so presenting that run as a raw comparison would quietly restore frontend work. Z3 BMC can itself hit the outer process timeout during formula construction; those remain unknown. Old 217/218 disjunct results are not comparable to whole-program query counts.

Every run records input and binary hashes, solver/outer limits and raw logs. Two seconds and 200,000 search states are used by default. Timing is exploratory on a shared host. Safe generated inputs remain a negative-proof challenge for the raw engines.

## Commands

```sh
./scripts/setup-raw.sh
python3 scripts/generate_harder.py
python3 scripts/collect_raw.py --source benchmarks/harder-programs \
  --extensions .ser --output benchmarks/raw-harder
cargo build --release
./target/release/vass-reach --raw benchmarks/raw-harder/monitor_d3_c12/query.json --seconds 2
vendor/venv/bin/python scripts/benchmark_raw.py --methods raw-bfs raw-potential \
  --repeat 3 --output results/raw-comparison
```
