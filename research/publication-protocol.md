# Publication development protocol

The active objective is a coherent Rust Petri-net reachability contribution with demonstrated gains over strong competitors. The existing portfolio is a starting point; publication readiness, novelty and broad superiority are unproven.

## New independent benchmark selection

`benchmarks/publication-selection.json` freezes 32 models from 16 previously unused MCC 2021 family groups, with all 16 original cardinality properties per model: **512 properties**. No solver results were inspected to make this selection. The source index is retained as `vendor/mcc2021/index.html` and hashed in the selection. Archive hashes are pinned after download.

The rule excludes all previously used family groups, groups numbered RERS problems together, ranks eligible groups by SHA-256 of `pvass-publication-v1:` plus the group name, and selects sixteen groups. Each must contain a family with at least five published instances. Choose the lexicographically first eligible family, then its third and fifth instances in published index order. First eight groups are development; next eight are evaluation. Keep trivial properties and conversion failures in the denominator. `scripts/select_publication_mcc.py` refuses to overwrite a frozen selection.

Development: DLCflexbar, JoinFreeModules, CircularTrains, AutoFlight, Echo, CANConstruction, CloudOpsManagement, GPUForwardProgress.

Evaluation: ShieldPPPs, TwoPhaseLocking, LeafsetExtension, ERK, Sudoku, HirschbergSinclair, AirplaneLD, CloudDeployment.

The corpus spans 8–3,682 places and 6–6,720 transitions. These sizes do not establish difficulty: baseline measurements must do so. All 512 properties imported, and the independent original-XML predicate checker passed 512 × 101 marking comparisons. Evaluation import validation is permitted; solver outcomes must remain unseen until a candidate is frozen. Old MCC evaluation families are now development evidence, never again called untouched.

```sh
python3 scripts/collect_mcc.py --selection benchmarks/publication-selection.json --output benchmarks/mcc-publication
python3 scripts/test_mcc_import.py --corpus benchmarks/mcc-publication --expected 512
```

## Competitive baseline

The SER artifact's restricted SMPT setup is inadequate for a publication comparison. An additional checkout now pins upstream SMPT to `82206ddcca45ecc497f8ed8eebc169a7c69d3641`, with official Tina 4.0.0 Apple Silicon tools (`reduce`, `walk`, `tina`, `ndrio`, `struct`, etc.). The unchanged artifact version remains available for reproducing older results. `scripts/setup-competitive-baselines.sh` pins the official Tina download SHA-256 and the SMPT commit. Python dependencies retain their existing pins in `scripts/requirements.txt`.

`smpt-full` enables automatic structural reduction and all productive methods: WALK, STATE-EQUATION, BMC, INDUCTION, K-INDUCTION, PDR-COV, PDR-REACH, PDR-REACH-SATURATED, SMT and CP. The unsaturated companion is an ablation; do not silently omit the full configuration because of the older artifact's intermittent contradicted verdict. A new version must be checked independently. Applicability remains determined by SMPT. Current upstream and Tina compatibility is established only for cases actually exercised, not assumed globally.

Use `--smpt-original` to preserve PNML NUPN annotations and original property identifiers. Hash original inputs as well as native translations. Full-tool comparisons may exploit original metadata; backend-only comparisons can separately use equivalent converted nets.

```sh
scripts/setup-competitive-baselines.sh
vendor/venv/bin/python scripts/benchmark_smpt_classic.py \
  --binary results/solver-v2/vass-reach \
  --methods portfolio-v2 smpt-full smpt-full-unsaturated \
  --smpt-root vendor/SMPT-upstream \
  --tool-bin vendor/tina/nd.app/Contents/MacOS/bin \
  --track-resources --smpt-original --outer-grace 0 \
  --seconds 10 --output results/classic-full-10s-run2
```

`--outer-grace 0` gives all tools the same whole-property outer wall deadline including startup and reduction. Native disjuncts share their remaining budget. The parser only accepts the requested property ID and rejects conflicting answers within a run. Logs and exported proofs remain available. Definitive conflicts between tools invalidate a competitive conclusion; investigate each and report it explicitly.

The resource runner observes descendant identities (PID plus creation time), samples CPU and aggregate RSS, and kills observed detached children on completion or timeout. This addresses SMPT's separate process groups for external tools. The detached-child timeout regression passes. Sampling can miss short-lived children, so CPU/RSS are lower-bound samples; this is **not** enforced CPU/memory isolation. Sampling also adds timing overhead, especially for sub-millisecond native solves. Current measurements remain shared-host pilots. Publication measurements require Linux cgroups, fixed cores and memory, a quiet machine, longer budgets (e.g. 10/60/300 seconds), randomized balanced run order and repeated runs. Compare equal-core and full-tool configurations separately since SMPT races multiple methods.

## Required evidence still outstanding

- A central algorithm and exact statement of its soundness, scope and limitations; inspect related work before claiming novelty.
- Meaningful held-out gains, with ablations separating proof discovery, reduction, scheduling and implementation speed.
- At least one additional strong current competitor beyond SMPT, ideally a symbolic MCC tool, with a pinned reproducible configuration.
- Full-tool and backend-only measurements, timeout/memory/error accounting, distributions by family, and witness/certificate checking. Never count contradicted external verdicts as verified solves.
- Harder SER programs and raw-export results, including a principled negative reasoning method if serializability is the central contribution.

Pro is reviewing the research direction at https://chatgpt.com/c/6ab917b7-99a8-83ea-8cb3-13a53675ff43. The browser attachment mechanism failed, so the submitted consultation contains substantial algorithmic context and an actual source excerpt, not the full archive. The prepared source archive is `research/publication-context.zip`. Proposed results from this consultation need independent verification.

An initial full-suite pilot in `results/classic-full-10s` aborted during runner cleanup with a macOS process-group permission error after the parent exited. It is incomplete and must not be used as an aggregate result. Cleanup now uses tracked process identities rather than a departed parent's process-group ID; the rerun is separate.

## First full-tool pilot result

`results/classic-full-10s-run2/REPORT.md`: 37 original classical properties, one run, common ten-second outer deadline. Frozen Rust v2 solves **37/37**, full upstream SMPT with Tina solves **36/37**, and full unsaturated SMPT solves **30/37**. No definitive conflicts. Full SMPT's only unknown is Expressiveness/Process. Two full-SMPT logs contain BrokenPipeError from a subprocess while the tool still produces a definitive verdict; these are retained in per-run metadata. Independent checks cover all native definitive answers; SMPT verdicts remain externally unchecked. One run does not establish saturated-PDR reliability.

This substantially narrows the earlier restricted-baseline coverage gap. It argues against presenting the older 37-versus-28 result as a full-tool comparison. The classical set is nearly saturated for both tools and cannot establish broad algorithmic superiority.

The new development baseline is running in `results/publication-development-baseline`, using 256 properties, five-second common outer deadlines, frozen Rust v2 versus full upstream SMPT with original PNML, and a sampled 2 GiB aggregate-RSS limit. This limit may double-count shared pages and overshoot between samples; Linux cgroup enforcement remains required for publication measurements. The evaluation half is untouched. Each new run archives the exact runner sources and refuses to overwrite a previous run directory.

A second baseline is being prepared from official TAPAAL VerifyPN 4.5.0, commit `c8193465bed56654546968bce3a956f0c25c5bee`. `scripts/setup-verifypn.sh` uses the upstream release presets and pinned dependencies, GCC 16, and macOS deployment target 13. No solver configuration or source algorithm is modified. Building and benchmarking remain pending; do not count this as a tested competitor yet. The upstream default includes aggressive net reductions, query simplification, LP reasoning, heuristic search and stubborn-set reduction. Its MCC script uses additional scheduling and shared-query work, so a direct single-property invocation must be labelled as such.

### Baseline capability correction

Inspection of the completed development logs found two capability failures in the nominal full configuration: `qsolve` (4ti2) is missing on this host, and upstream SMPT's sliced WALK command uses reduction flags rejected by Tina 4.0.0. Therefore neither the classical pilot nor the new development run establishes a fully functioning full-tool baseline. Their verdict counts are observed results of the recorded configuration, not evidence that all enabled engines ran correctly. Before competitive claims, install and pin 4ti2 and use a Tina version compatible with the upstream interface (or a documented compatibility adapter), then rerun. Preserve existing raw logs/results. The corrected baseline may be stronger.

The completed development pilot has Rust 179/256, SMPT 205/256 definitive verdicts, 77/50 unknowns respectively and one SMPT error (timeout plus BrokenPipeError). There are no definitive conflicts. All native definitive answers were independently checked. These 256 properties are development evidence; the separate evaluation half remains unused.

### Portable upstream configuration

4ti2 1.6.15 is now built, tested and installed locally from commit `f93eb8e419322a9ce653a6285f3febdbb2f24da4`, with Homebrew GLPK 5.0 and GMP. `scripts/setup-4ti2.sh` reproduces it. Both official Tina 3.7.5 and 4.0.0 reject SMPT's internal sliced-WALK options; the earlier inference that these options were removed in version 4 was unsupported. `scripts/setup-smpt-portable.py` creates a separate pinned upstream copy with one compatibility change: it turns off WALK's unavailable internal slicing. WALK still runs on the original net, with Parikh guidance when supplied; all other proof methods and the separate automatic structural reduction stay enabled. The original upstream checkout is preserved. The patched file and original file hashes are recorded in `vendor/SMPT-portable/PORTABILITY.json`.

Name this configuration **SMPT portable, with plain WALK**, not unmodified full upstream. Use `--methods smpt-full-portable --smpt-root vendor/SMPT-portable --tool-bin vendor/tina/nd.app/Contents/MacOS/bin --tool-bin vendor/4ti2-install/bin`. The harness checks qsolve availability, rejects incompatible sliced-WALK builds in unpatched modes, and records dependency/interface failures in results. Two original-PNML smoke cases (AutoFlight02a RC00 and DLCflexbar4a RC01) now run without those errors; both tools agree and native witnesses/proofs check. A broader rerun remains necessary.

The preliminary candidate portfolio `portfolio-v3` checks the initial marking, spends at most 20%/500ms on sparse arithmetic, then uses the existing v2 engines with the remaining budget. Its snapshot is `results/solver-v3-candidate`. The first full candidate run was aborted on detecting overlap with dependency build/tests; `results/publication-v3-candidate/ABORTED.md` excludes those incomplete timings from comparison. No result union should be substituted for a measured portfolio result.


## Discovered timing contamination and rerun requirement

On 2026-09-27 eight orphaned workspace-owned Tina WALK processes were found consuming CPU; process identities, exact executable paths and working directories are archived in `research/orphan-walk-cleanup.json`. Their lifetimes overlap the classical-full run2, publication development baseline, sparse-linear run, sparse-primal frontier pilot and portable smoke. Their proof/witness artifacts remain usable, but comparative timing and equal-budget coverage claims from those runs must be withdrawn pending remeasurement. The first causal/portable run was aborted upon discovery and excluded.

The runner now checks for overlapping workspace solvers/builds before every measured invocation, records hashes of transitive4ti2 binaries and struct, and supports a separate frozen baseline binary in a paired run. This guard does not provide OS-level isolation or prevent other user applications from using CPU. The new clean rerun remains exploratory until reproduced with repetitions and controlled resources.


## Input-cost boundary for the current pilot

Current native runs start from pretranslated canonical JSON and split the original property into imported branches; PNML/XML translation is outside their timing. `--smpt-original` gives SMPT original PNML/XML, so its parsing and reductions are inside timing. The whole-property truth values agree semantically, but this is not yet a matched original-input end-to-end comparison. Publication claims require either charging native original-input conversion under the same deadline or a separate common-representation comparison, alongside the best-tool original-input track. Preserve this distinction when reporting coverage at short deadlines.

### Original-input native track

`--native-original` now launches `scripts/native_original.py` under one outer deadline. This is a **Python PNML/XML frontend with a Rust backend**. Python startup, original-input parsing, exact requested-property selection, EF/AG target conversion, DNF expansion, branch JSON serialization and all native invocations are charged. NUPN annotations are ignored by this frontend; PNML P/T-net semantics are preserved. SMPT remains free to exploit those annotations. Use both `--native-original --smpt-original --outer-grace 0 --track-resources` for the original-input track. The default canonical-JSON track remains available and records its different cost boundary.

All branches share the remaining internal budget; a single process-tree watchdog bounds the whole property including conversion. The frontend emits stable translated branch files and answer logs into a per-run `.original` directory. After the timed process exits, the parent compares **every translated branch** with the hashed canonical manifest, checks exact property ID and polarity, and independently checks each definitive answer. Unavailable certificate checks downgrade the proposed answer to unknown; invalid witnesses/proofs are errors. An outer timeout is unknown even if partial logs exist. An empty DNF proves the target false only after exact translation comparison. Checkers and canonical comparison are excluded from timing on both native tracks. Original-input translation shares code with the importer; the separate original-XML predicate tests remain necessary to assess translation correctness.

The frontend/interpreter hashes and input-cost boundary are recorded in `environment.json`; runner sources are snapshotted. This mode does not retroactively fix older comparisons. Fair publication timing still requires controlled resources and repeated measurements.

## Linux measurement track

User-provided Tailscale host: `jules-b650-aorus-elite-ax-v2`; workspace `/home/jules/experiments/pvass-publication`. Native builds explicitly use Rust 1.97.1 with locked dependencies and optimized release profile. Frozen v2 and causal sources are rebuilt independently from their retained archives; macOS binaries are never compared on Linux. VerifyPN uses the same pinned 4.5.0 source and upstream release configuration; actual compiler/package versions and binary hashes must accompany each run.

Use `--native-original --smpt-original --linux-cpus 8 --perf --memory-mib 2048 --outer-grace 0 --order-seed 20260927`. The runner places each command and descendants in its own user-systemd cgroup, with enforced memory/swap limits and a fixed logical CPU. The 7950X3D has different L3cache sizes across its two core groups; CPU 8 is in the 32 MiB group, and its SMT sibling is CPU 24. This pins execution but does not reserve the CPU from unrelated jobs. Report a separate wider-affinity full-tool track if desired rather than conflating single-core and multicore budgets.

`perf stat` records user-space retired instructions, user-space cycles and task clock with event runtime/running percentages; cgroup accounting records total CPU and peak memory separately. Counters reduce some sensitivity to clock frequency and interference, but cannot replace elapsed time or make timeout results independent of host load. Thread races, polling, search policies and wall-clock cutoffs can change executed instructions. Timeout/OOM results stay unknown, and missing counters after a cgroup kill remain explicitly unavailable. A failed counter setup on an otherwise completed run aborts measurement. See `linux-runner.md` for exact timing and stop-grace semantics.

The harness records property order and a seed. With a seed, properties are shuffled reproducibly and method order rotates over properties/repetitions. Evaluation families remain untouched; this setup currently operates only on development inputs. The global runtime performance-counter setting was enabled with user authorization; no persistent sysctl configuration was changed.

## VerifyPN trace configuration

The historical `verifypn` mode requests `--trace`; it is a trace-reconstruction baseline. Upstream disables structural reductions H/J/R/S/Q in this mode and stores predecessor information. The separately named `verifypn-default` mode runs unrestricted single-property defaults without `--trace`. Both receive the original PNML/XML and the same outer resource budget. Their configurations are recorded explicitly, and old records retain their original meaning.

Independently replayed diagnostic traces support witness validity only for the measured trace-mode executions. Do not attach those traces to unrestricted timings or treat unrestricted negatives as checked proofs. Upstream MCC multi-property scheduling remains a separate configuration.
