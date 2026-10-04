# Broader benchmarks and the second native portfolio

## Benchmark design

The classical SMPT corpus is useful but small: 35 distinct problems plus two repeated certificate examples. The new corpus adds **384 original MCC 2021 reachability-cardinality properties**, from 24 instances across 12 families: Kanban, FMS, Philosophers, Peterson, LamportFastMutEx, DatabaseWithMutex, RwMutex, SharedMemory, SwimmingPool, TCPcondis, TokenRing, and DoubleExponent. Models range from 9 to 830 places and from 7 to 3,616 transitions.

Sources are the [MCC 2021 inputs hosted by Yann Thierry-Mieg](https://yanntm.github.io/pnmcc-models-2021/), which are also referenced by SMPT's benchmark tooling. `benchmarks/mcc-selection.json` pins the URLs and SHA-256 hashes of all 24 archives. `scripts/collect_mcc.py` retains all archive files and extracts the original inputs under `vendor/mcc2021/`. Original model metadata stays with the source files. The corpus is a specified selection, not the entire MCC repository.

Each model contributes all 16 original cardinality properties. Import preserves the original P/T net, weighted/read arcs and initial marking. Known NUPN structural annotations and Tina display size/color annotations are omitted from the conversion; they do not change ordinary P/T firing semantics. No net reduction or target satisfiability simplification is performed. EF/AG polarity and disjunctive-target aggregation follow the classical importer. Source and converted hashes are recorded.

The split was fixed by family before changing the solver: sort the twelve family names by SHA-256 of `pvass-v2:` followed by the family name; the first six are development families and the remaining six evaluation families. Thus related instances never cross the split. Each split contains 192 original properties.

The first published instance from each family was initially selected. The old solver solved all 96 development properties, so the third published instance of each family was added using the same rule and split, without inspecting evaluation results. The expanded development set is substantially harder: the old portfolio solved 140/192 at two seconds in the first pass. These are curated, within-distribution evaluation families, not a claim of representative performance on all Petri nets.

The original properties include easy cases: 47/192 development and 12/192 evaluation queries have a reachability target containing the initial marking. All are retained rather than selecting properties after seeing solver results. The independent source-XML comparison covers the initial marking and 100 deterministic sample markings for every MCC property (38,784 predicate checks).

`benchmarks/mcc2021-development-hard/manifest.json` additionally selects the 52 development queries that the old portfolio left unknown in the first expanded run. It records the selecting run's hash. This is a tuning convenience; coverage claims use the full predetermined sets, not this result-selected subset.

## Solver changes

`portfolio-v2` adds two complementary negative-proof engines before the existing arithmetic and witness-search portfolio. The old `portfolio-next` remains selectable for comparisons. Raw SER queries continue to use the existing `raw-potential` engine.

**Inductive interval partitions.** Each region records lower and upper bounds for all places, with selected control coordinates exact. Small structurally nonincreasing place sums suggest control coordinates. Abstract transition images intersect the precondition before applying the effect, so enabling thresholds can establish bounds such as a fuel place remaining at least two. Regions with the same control marking are joined; repeated bound changes widen upper bounds to infinity or lower bounds to zero. Region, work and time budgets prevent discovery from running indefinitely.

The exported certificate contains the region union and an arithmetic exclusion for each region. The checker verifies that the union contains the initial marking and is closed under every original transition. For each region it combines those interval bounds, the target, and the original net's state equation; an exact arithmetic certificate refutes their conjunction. Discovery heuristics and widening choices are not trusted by the checker.

**Property-directed projections.** Begin with places appearing in the target, then expand through enabling dependencies of transitions that change selected places. Each projected net forgets other coordinates and therefore overapproximates original executions. Duplicate projected transitions and transitions that leave the projection unchanged are removed. Finite threshold abstraction with refinement can certify that the target is unreachable in the projection. The certificate checker reconstructs the projection and checks its abstract closure. A projected witness is accepted only if every step can be instantiated by an enabled original transition and the entire resulting trace passes original-net replay and the original target check. Failed lifting supplies no verdict.

The interval engine produces checked negative answers or unknown; projection additionally permits the replayed positive witnesses just described. Neither new engine calls SMT. Both certificate formats have independent Python implementations in the benchmark verifier, and the Rust CLI accepts them through `--verify`. The portfolio limits interval discovery to nets with at most 64 places and support refinement to at most 128 places, leaving more search time for larger nets. Interval and projection stages receive at most 50 ms each and support refinement at most 25 ms, also subject to their fractional shares of the total budget. The standalone engines remain available independently with the requested full budget.

## Development evidence

The interval engine alone first raised classical coverage from 27/37 to 34/37 in the portfolio, but the first MCC development comparison lost two old solves. That intermediate configuration was not selected on the classical result alone. Lower-bound widening was then added to avoid countdown-length discovery, and projected closures were added to handle small relevant portions of larger nets. The second revision solved all 37 classical properties in its development pass, with independent verification. A final development adjustment added checked witness lifting and limited the large-net overhead of preliminary proof stages.

Final measurements, including the untouched evaluation families, are recorded separately in [the final report](../results/SOLVER-V2.md). Intermediate measurements remain under `results/interval-classic`, `results/projection-classic`, and `results/mcc-development-v2`; they are not final-configuration measurements.

## Reproduction

```sh
python3 scripts/collect_mcc.py
cargo build --release --locked
python3 scripts/test_smpt_import.py
python3 scripts/test_invariant_checker.py
python3 scripts/benchmark_smpt_classic.py \
  --corpus benchmarks/mcc2021-evaluation \
  --methods portfolio-next portfolio-v2 smpt-portfolio-unsaturated \
  --seconds 2 --output results/mcc-evaluation-v2
```

Individual methods are available as `--method interval-invariant` and `--method projected-cegar`. `--method portfolio-next` preserves the earlier portfolio. The default `portfolio-v2` is an incomplete budgeted portfolio; the separately available complete Kosaraju procedure is unchanged.

Tests cover enabling bounds, irreversible control phases, projection soundness, malformed/forged certificates, and differential checks against exhaustive reachability on 100 bounded nets. Independent checker tests reject removed closure states, missing target coordinates, incorrect interval bounds, and altered transition preconditions. The pre-existing reachability and arithmetic regression suite remains in place.
