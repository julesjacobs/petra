# Current harder-benchmark evidence and next work

Catalog v5 is `benchmarks/development-hardness-catalog-v5.json`, produced by
`research/build-hardness-catalog-v5.py`; report `research/harder-test-set-v5.md`.
V4 is preserved. The builder reconciles recorded evidence hashes without
measurements, imports, solver executions or proof reruns; its output records counts.

Completed and audited:

- Application 300s qualification: 16/16 rows, four joint survivors, no definitive
  answer from any tested configuration; 28 warnings retained. Saved completion
  receipt records session81844 exit0. SharedMemory-200 RC03/04 and TokenRing-30/40
  RC09 remain unresolved. Preserve 464 slots/448 imports/442 exact representatives,
  the full 13-query 60s stage and the audit-role erratum with original failed audit.
- Transfer v2 export: 12 sources, nine exports, three 120s frontend timeouts.
  Full 24-row legacy/balanced pilot checks six early-release queries per method;
  three available n4 strict queries hit sampled2GiB. Three n6 strict export
  failures stay in every source denominator. V1 syntax failures stay preserved.
- Three transfer phase diagnostics locate memory failures in structural game
  expansion; observed counters remain censored. Dense/compressed full24-row
  comparison has no coverage gain: six checked positives per configuration;
  three dense memory failures become compressed solver timeouts; three exports
  remain unavailable per configuration. Stronger negative proof remains open.
- Original diverse/scaling raw cohorts: 27/27 available checked at60s, 28slots,
  24unique programs, four bridges, one unavailable export. Keep as regression
  baseline; historical work, memory and scheduling failures remain recorded.
- Compressed full raw regression:28audited rows,25/27available checked versus
  dense27/27. n5pairlocked times out in both cohorts around48.2s, before any
  independent check; no returned work-limit cause. Candidate remains experimental.
  See `raw-compressed-cohorts-v1-report.md`; session75521 exited0.
- Direct walk: each fixed seed checks9/9 selected TokenRing gaps, matched batched
  0/9; 36rows and27 checked positives. Integrated warmup:9/9 versus0/9,
  18rows and9 checked positives. These are different queries from the four
  300s survivors. Selected local evidence only, with separate independent checking;
  no full-cohort or Linux timing result inferred.

Next evidence needed:

Latest execution update: full ordinary comparison is running in Linux session20509,
registered by `application-walk-full-v1/plan.json` with hash
`48ae2d642761e6c0fbd5171c73804f99f95edb624511f00fb93d3749aded03aa`.
See that folder's `execution.json` and `run.log`. Preserve the Linux gate:
no builds, imports, bulk transfers or other measurements until terminal completion.
It retains656slots/640imports across five configurations,3280expected rows,
CPU8affinity,2GiB,5s,perf and separate60s native checking. Candidate Linux build
passed232tests (one ignored), and its eight-row smoke independently checked all
seven definitive answers. Package v2 repairs missing Python dependencies without
changing any original frozen Rust source. Full-run results are not yet available.

1. Broader matched regression/competition evaluation of integrated walk, with
   complete parents, fixed limits, independent native checks and ablations.
2. A general negative-proof improvement for three strict transfer cases, checked
   independently. Representation compression alone has not gained coverage.
3. Current-tool historical qualification retaining all eight original cases and
   the620/69/8parent denominators; use its own completed audit before updating
   historical classifications. Its saved preparation is not completion evidence.
4. Failure-phase diagnosis of the four300s ordinary survivors without relabelling
   memory or collection failures as intrinsic search hardness.

This handoff records completed evidence, not live process state. Before starting
any local or Linux measurement/build/export, inspect authoritative current session
handles and workload state; do not infer idleness from old session IDs or this
file. The parent agent owns scheduling and may have started subsequent work.

All22reserved families remain excluded. No reserved payloads/results read.
No pooled timing, held-out, general-superiority or publication-readiness claim.
The full goal remains active; this catalog update does not complete it.

Subsequent completed evidence: `raw-n5-control-diagnostic-v1-report.md` attributes
the compressed n5 regression to an early negative-game work limit, followed by
positive fallback. The encoded-word accounting repair in `src/raw_negative.rs`
passes233tests (one ignored), formatting and Clippy, and is frozen at
`results/solver-raw-encoded-work-v1`. Its28-row raw regression restores27/27
available checked slots; the12-row transfer qualification still has six checked
positives, three strict timeouts and three unavailable exports. Both audits pass;
sessions20770and80089exited0. See `raw-encoded-work-v1-report.md`. No local
measurement remains from those sessions. Linux20509is still a separate live
measurement and must be polled before releasing its gate.

User clarified the intended publication contribution is a general Petri-net
solver, with serializability as an application. See `contribution-scope-current.md`.

Phase-pair update: session80844 exited0; all8rows pass the saved-artifact audit
`phase-pair-survivors-v1-audit.json`. The opt-in method independently checks
TokenRing-30/40 RC09 (3.900/10.981s local solver, separate1.355/2.695s checker).
Same-binary batched+buffer times out at30s on both. SharedMemory-200 RC03/04 remain
Unknown: pair relation size cap for phase-pair, sampled memory cap for batched.
Thus the older “four unresolved” statement is historical; two now have checked
negative answers. See `phase-pair-survivors-v1-report.md`. All4selected cases and
8rows retained; parent464/448/13/4denominators unchanged. No Linux speed claim.

Current local execution: uniform-pair ablation implemented as `--method pair`,
with the same certificate/checkers and an empty landmark set; no default change.
Frozen `results/solver-pair-ablation-v1`, tests215lib+4original CLI+7phase-pair
passed, Clippy/format passed. Original failed invocation of nonexistent test target
`cli` is retained; corrected `original_cli` invocation passed.
Full ordinary cohort ablation is running in local session6596, registered in
`pair-ablation-full-v1-execution.json`; expected1312rows,656slots/640imports,
phase-pair versus uniform pair,5s and separate60s validation. No local
solver/build/export until terminal. Auditor prepared at
`audit-pair-ablation-full-v1.py`; not run against incomplete results. Linux20509
is independently still running. Neither full result has been audited or claimed.

Further active work: Pro review submitted with305-file source/test/checker snapshot
at https://chatgpt.com/c/6aba1a88-e75c-83ea-8b0d-2d137413267d ; files and submission
receipt in `research/pro-pair-review-v1/`. Existing pro-rust-petri-net-solver
heartbeat updated to this consultation, five-minute interval, quiet while thinking.
Answer not received yet. Implementation guided by that advice should await it.

Manual SharedMemory candidate answers are prepared in
`research/check-sharedmemory-manual-v1.py`, gated on session6596completion.
RC03 candidate200-step trace requests external access for every Active process;
RC04 candidate sparse Farkas proof combines target rows0and2 plus external-access
nonnegativity. See `sharedmemory-manual-diagnostic-v1-proposal.md`. These are
unverified manual proposals, not automatic-solver results. Bounded original-input
Python and per-branch Rust checking still required.

An additional weighted/signed-target soundness test has been appended to
`tests/phase_pair.rs`. It has NOT been compiled/run/formatted yet: no local
solver/build/export until session6596terminal. Frozen measured source is unchanged.

Completed now: local session6596 exited0. All1312rows pass corrected artifact
audit. Phase-pair checks4/640imported slots; uniform pair checks0/640. Both retain
16unavailable. Phase-only: TokenRing-20 RC08,TokenRing-30 RC08/RC09/RC15. See
`pair-ablation-full-v1-report.md`;512properties contain a branch where discovered
group initial mass exceeds1. This is a discovery limitation, not proven unsafety.
The first audit incorrectly expected unavailable verdict unknown; actual
unsupported rows preserved and corrected audit passes. Local measurement gate
released. Linux20509 remains independent and must be polled before engineering.

Manual SharedMemory checks completed in session48518 exit0: RC03 has a checked
200step counterexample on branch3; RC04 has checked sparse Farkas refutations for
both branches. Every definitive branch passed Rust verification and bounded
independent Python original-input translation/checking. Both original properties
false. See `sharedmemory-manual-v1-report.md` and
`results/manual-sharedmemory-v1/verification.json`. These are NOT automatic solver
results. The synthetic summary's zero timing fields are schema placeholders.
Additional weighted soundness test is currently compiling/running; inspect current
session from root before assuming the local machine idle.

Weighted/signed-target phase-pair validation now complete: session29126 exit0,
all8integration tests pass, including both abstractions versus explicit reachability
on168targets across8small safe nets, with weighted disabled transitions, read arcs,
consumption and negated equalities including i64::MIN. Every emitted negative in
that sweep is independently checked in a batched Python worker. Clippy session78764
exited0; formatting check passes. Logs named `phase-pair-weighted-soundness-v1*`.
This test-only extension is not in the previously frozen measured binary/source.

Linux20509 now TERMINAL exit0. Results retrieved in session59517 exit0, collection
receipt in `application-walk-full-v1/collection.json`. Audit session92531 exit0:
all3280rows pass, no disagreements,76warnings retained. Native-walk632/640,
matchedbatched615, frozen614, VerifyPN603,SMPT394. Walk has17/18gains over two
native controls and no losses;30gains/1loss vsVerifyPN (NoC3x3-8B RC12 reachable),
238gains/no losses vsSMPT. Eight native unknowns listed in the report. The Linux
measurement gate is released; check current remote workloads before new jobs.
Report: `research/application-walk-full-v1/report.md`.
Correction to prior manual-gap status: SharedMemoryRC03 is already automatically
checked by this completed run: branch0causal state-equation negative, branch1
633step uniform-walk positive. Manual200step branch3trace remains valid.

Guided walk implemented opt-in, with an incremental-target uniform control.
Files: `src/walk.rs`, new`src/walk_guidance.rs`, `src/main.rs`, tests. Existing
uniform/default schedules unchanged. All selected tests and Clippy/format pass;
initial missing `policy` in an old Run test initializer was fixed; failed logs
retained. Frozen release build currently session12002; do not start a local
measurement until terminal. New eight-query qualification not yet launched.
Pro review remains thinking at last inspection; monitor active, no final answer.

Guided-walk freeze completed in session12002 exit0: full source and release binary
at`results/solver-guided-walk-v1`. Validation218lib+4original CLI+8phase-pair+
7walk CLI=237passed; Clippy/format pass. Frozen artifacts preserve initial failed
compile logs from the old Run test initializer. New modes are`walk-guided` and
`walk-incremental`; existing uniform behavior and portfolio scheduling unchanged.
Qualification running locally in session79957: all8native-walk Unknowns selected
from completed/audited Linux parent, three modes,24rows,5s,2GiB sampled,separate60s
checking,seed0. Registered`guided-walk-gap-v1-plan.json` and execution record.
NO LOCAL SOLVER/BUILD/EXPORT until79957terminal. Auditor prepared but not run:
`audit-guided-walk-gap-v1.py`. Pro answer still pending at last inspection.

Guided pilot79957 now terminal exit0 and all24rows audited. All three standalone
walk modes check NoC3x3-8B RC12 (AG false); each has7Unknowns. Uniform/incremental
have identical1230step traces; guided1312steps. Local solve times0.234/0.212/0.552s,
one repeat. NO guidance coverage gain or justification for portfolio promotion.
See`guided-walk-gap-v1-report.md`. Local gate released. No local job known active.

Current Linux measurement: session31728, all8historical FastForward/pigeonhole
survivors,5configurations x300s,40rows, CPU8/perf/2GiB and separate60s checking.
Includes strongest audited native-walk, matchedbatched, frozen native, VerifyPN,
repairedSMPT; preserves620/69/8parents and old32rowhistory. New plan
`research/hard-survivors-current-v2/plan.json`, hash
97537ae48199a6d419bea14810050c55e581ead9bbe9b129a2b51d97fdca0651.
Deployment52133completed, all3406identities checked,4missing files deployed.
Read `execution.json` and `run.log` there. NO LINUX BUILDS/IMPORTS/BULK TRANSFERS
or other benchmarks until31728terminal. Do not restart. Use auditv2 after collection.
Pro review still thinking at last current UI observation; monitor active.

## 2026-09-28: capacity pilot and catalog v6

Capacity-combinations frozen build54897 exited0. Source/binary in
`results/solver-capacity-combinations-v1`; selected tests, Clippy and format passed.
Opt-in`--method capacity` adds fair target-row seed selection and two signed-row
Farkas refutations from incidence-discovered0/1nonincreasing potentials. Existing
portfolio/default unchanged; no model-name special cases or new proof rule.

Pilot86289 terminal0, all16rows passed `audit-capacity-combinations-gap-v1.py`.
All8current native-walk Unknowns retained,5s/sampled2GiB,separate60svalidation.
Capacity automatically solves SharedMemory200RC04 in0.625s+4.027schecker, two
checked-capacity-combined branches;933114bytes compact proofs. Same-binary walk
solves NoC3x3-8B RC12 in0.268s using causal-state-equation244step witness. Neither
solves the other6. No historical Linux count changed; new capacity stays opt-in.
See `research/capacity-combinations-gap-v1-report.md` and its audit/plan/receipts.
Local measurement gate released. No known local solver/build job active.

Instruction summary for full Linux walk run is now saved in
`research/application-walk-full-v1/instruction-summary.json`, with reproducible
`summarize-instructions.py`. On jointly definitive pairs with full-coverage
counters, median walk/batched1.091, walk/frozen1.091, walk/VerifyPN1.346,
walk/SMPT0.0139. Exclusions and duplicate slots retained. Checking excluded from
solver counters. Coverage gains cost work; no unconditional speedup claim.

Current catalog is now `benchmarks/development-hardness-catalog-v6.json`.
Builder53246 terminal0; verified20770evidence files and51source files. Preservesv5,
full denominators and historical failures; adds complete Linux3280rows, phase
ablation1312rows, guided24rows, capacity16rows, manual-vs-automatic distinctions,
and repaired raw27/27regression plus unchanged6/3/3transfer classification.

Linux31728 remains live at latest poll: no Linux builds/imports/bulk transfers
until authoritative terminal.40-row historical survivor result remains pending.
Pro tab9 still thinking at last observation; no final answer saved or assessed.
Keep active monitor quiet until final. Its interim dispatch criticism must be
assessed against the intentionally isolated frozen runner (shared scripts pinned
by live Linux experiment). All22reserved families remain untouched.

## 2026-09-28: Pro finished; signed-threshold kernel

Pro tab9 response completed (42m6s). Substantive condensed transcription saved
`research/pro-pair-review-v1/answer.md`; assessment.md and submission.json updated.
Monitor pro-rust-petri-net-solver now PAUSED after saving/reporting. Downloadable
reviewer probes were offered but download timed out; do not claim locally run.
No final-answer verbatim export; answer.md explicitly records condensed status.

Pro recommends signed-threshold binary invariant discovery with exact pullback
and sparse implications. Its ten-new-negatives criterion impossible on current
640imports/8nativeUnknowns; assessment corrects this before outcomes. User
priority confirmed **coverage and speed first**. Checking is correctness support,
not primary contribution. Broader harder development extension needed;22reserved
families remain untouched.

Three agents finished. Phase schema agent repaired full original schema in
`scripts/phase_pair_checker.py` (not pinned by live Linux plan), preserving proof
rules. Common scripts/benchmark.py intentionally unchanged. New frozen runner
`results/runner-phase-pair-v2`,23files, only helper differs fromv1.7Python tests
including30malformed cases, actual bounded original PNML/XML validation and
relevance-wrapped proof composition passed. Evidence `research/phase-pair-schema-v2`.
Historical acceptance of an unreferenced malformed target independently reproduced;
no false refutation of a well-formed query established.

`src/signed_threshold.rs` and independent`scripts/signed_threshold_checker.py`
implement supplied-invariant exact numerical2CNF checking. CLI --verify dispatch
added, no solver method/default changed. Contract/design and experiment gates in
`research/signed-threshold-v1-{contract,experiment}.md`. Both enumerate all original
obligations and reject reachable targets/mutations. No discovery, monitor, paths,
watched dependencies, cross-template axioms, or corpus coverage yet.

Root tests: session64250unit0;80990integration0;20420full selected0 (242Rust tests).
Python15tests exit0; Clippy16276exit0;fmtcheck exit0. Rust Boolean1800and finite1000,
PythonBoolean400and finite624differential cases included. New kernel source frozen
`results/kernel-signed-threshold-v1` with logs, complete inherited source and
archive rehash; no benchmark release binary. Report `research/signed-threshold-v1-report.md`.
Root reduced delta calculations to certificate forms instead of all interned guard
forms; validated by final test run. Parent portfolio/capacity behavior unchanged.

NEXT: implement bounded automatic clause-pool growth/full-rescan Houdini, unary
ablation and independent checking before corpus timing; only then optimize cache/
paths if cost warrants. Need new isolated runner version for threshold dispatch;
phase-pair-v2 currently handles existing proof kinds, no threshold dispatch yet.
Do not promote method or count supplied fixtures as solver results.
Linux31728 still live at latest authoritative poll; no remote builds/imports/bulk
transfers. No local solver/build process known active. Catalog remainsv6; no
new benchmark outcome this turn.

## 2026-09-28: automatic threshold discovery running

Automatic engine implemented in `src/threshold_discovery.rs`, privately included
by signed_threshold.rs; opt-in CLI `signed-threshold` and `signed-threshold-unary`.
Public solve(problem,timeout,max_work,max_clause_arity). Target/predecessor-cube
growth, initially true clauses, deterministic full-rescan simultaneous Houdini,
full-pool restarts;2048clauses/64candidateforms/64thresholdsperform/8checkedrounds
(max7expansions). Guards exempt from candidate vocabulary caps. Sparse incidence
identifies exact zero changes; every negative reverified with original kernel.
Final reason records logical work/candidates/rounds/scans/removals/revivals/caps.
No default portfolio changes, no new affine synthesis or trace monitor.

Validation:67521initial filtered kernel0 (integration filters excluded tests);
13042integration0;40048selected0;39461revival0;78442final0=243Rust tests
(228lib+4originalCLI+5thresholdkernel+6discovery), including336finite queries,
automatic weighted/unbounded binary-vs-unary gap, resurrection of removed clauses.
Clippy11770exit0 and finalclippyexit0;formatexit0. Staleunusedvariable fixed before
final tests; no unresolved project warnings. Existing vendor warnings remain.
Four Python bounded-original composition tests pass; helper unchanged.

New isolated `results/runner-threshold-v1` has24files, adds threshold dispatch
and source recording only in isolated scripts; allparentv1/v2hashes unchanged.
ArchiveSHA dec8c7cdb3f7faf1e524bd07df371b8021c9c648488ebe27091b8cae5bf3ed99.
Evidence `research/threshold-composition-v1`. CheckerSHA
f7cd30ad9ad15fc3f3d12e4a667a5705e1551a98730e8f85655cab19a78a4bbd.

Frozen release session57621terminal0: `results/solver-signed-threshold-v1`.
Full local screen RUNNING session34053,1312rows(all656/640/16slots),two modes,
5s/sampled2GiB/separate60schecking,one repeat. Plan+execution:
`research/signed-threshold-full-v1-{plan,execution}.json`; log
`research/signed-threshold-full-v1.log`; output`results/local-signed-threshold-full-v1`.
Do NOT run local builds,solvers,imports,exports until34053authoritative terminal.
Do not restart. Auditor prepared`research/audit-signed-threshold-full-v1.py`,
not run yet. Derive coverage/complementarity from complete audited rows only;
no benchmark conclusion yet. Use strongest native632/640Linux parent for coverage
context, not cross-machine speed comparison or weakerbaseline superiority.

Implementation report`research/signed-threshold-discovery-v1-report.md`;
exactalgorithm`research/signed-threshold-v1-discovery.md`. Next first poll local34053
and Linux31728; audit/collect only when respective terminal. Linux31728stilllive,
no remote builds/imports/bulktransfers. Pro complete/monitorPAUSED from priorturn.
Userpriority remains coverage/speed; no new question pending. Allagentsfinished.

## 2026-09-28: general development extension preregistered

Both active handles independently confirmed live this turn: local34053threshold
screen and remote31728historical300scomparison. No benchmarks/builds/imports/
exports added; only small metadata reads and new selection/protocol files.
Existing application ladder has exhausted later indexed instances of its five
families. Frozen a broader metadata-only unused-group development selection:
`benchmarks/general-development-v3-selection.json`,11models/176plannedslots,
6groups:TriangularGrid,IBM319,RERS17pb114,RefineWMG,CloudReconfiguration,DNAwalker.
No acquisition, payload reading or solver qualification performed yet; not proven
harder. SHA8b0c3496bc31f6fecf4cb54ff49a8d826b10feb7387ea5a1de7f562d1616fc90.

Deterministic SHA family rank after excluding22reserved families and previously
used groups; median/final ordinals, deduplicated singleIBM319instance. Conservative
RERS/IBM/DLC/ProductionCell/GPU grouping prevents obvious potential relatives;
not a verified generator-independence claim. All113indexed family decisions saved.
Selector `research/select-general-development-v3.py`; independent metadata audit
`research/audit-general-development-v3-selection.py` passed and saved hashes.

`research/general-development-v3-protocol.md` has exact bounded collector command
ready ONLY AFTER local34053terminal and workload preflight. 120s/model,2GiB,
256MiBarchive/1GiBexpansion+artifact; all176slots retained. Audit original import
semantics/canonical duplicates before solver qualification. Linux31728separate
gate remains. All22reserved payloads/results untouched. Goal priority coverage/
speed; existing local1312rows must reach terminal and audit before conclusions.

## 2026-09-28: single-core SMPT source review and post-run preparation

Latest authoritative polls still show local34053 and Linux31728 live. Local
threshold run has927/1312recorded rows at this checkpoint, not an audited result.
No builds, imports, exports, solvers, remote changes or bulk transfers launched.
Keep both measurement gates; do not restart either handle.

Independent read-only agent review confirmed: SMPT launches one process per
EFFECTIVE method. Full requests10but target/reduction gates mean not necessarily
10workers; K-INDUCTION adds BMC. No official sequential/worker-count flag. Official
--mcc uses a distinct preliminary stage/schedule. --auto-reduce is not --project;
projection requires octant.exe, capability not yet checked. Source findings and
proposed complete176-slot SMPT screen in`research/smpt-single-core-review-v1.md`.
Proposed four additional configurations:compact WALK/STATE-EQUATION/BMC/
K-INDUCTION/SMT,PDR-REACH+SMT,PDR-REACH-SATURATED+SMT,official--mcc. Together with
fullSMPT,three native controls andVerifyPN,this would be9configs/1584rows.
Not executed/frozen; no performance advantage claimed. Generalv3protocol links
review; selection unchanged,22reservedfamilies untouched. Agent finished.

Prepared only (ASTsyntaxchecked; not executed):
- `research/collect-hard-survivors-current-v2.py`: requires both terminal receipts,
  matching plan hash,local/remote idle preflight; collects whole remote result
  directory with path-checked extraction and archive receipt.
- `research/audit-hard-survivors-current-v2.py`: uses existing v2artifact auditor,
  verifies40rows/8survivors/620+69parents and records stale inherited plan fields.
  Plan'sexpected_solver_invocations=3200,kind_preserving_representatives=630and
  reportingprose describe earlier ordinarycohort; actual frozen command/matrix
  is8queries*5configs*1repeat=40. Preserve plan bytes; never report stale values.

NEXT: after34053terminal, run signed-threshold auditor redirecting verbose output
to a log, assess whole-cohort binary/unary coverage and complementarity/cost
against strongest native. Then acquire frozen generalv3cohort. After31728terminal
record authoritative exit receipt; fetch only when BOTH measurement gates are
clear, then run new collector/auditor and investigate failures before conclusions.
No aggregate threshold outcome yet, no goal-completion or superiority claim.

## 2026-09-28: threshold outcome and new cohort acquired/checked

Prior turn is progress plus verified wait. Local34053authoritativelyterminal0;
fullthresholdauditor39878terminal0,summaryscriptterminal0. Full1312rows audit
passed:binary100/640checkednegatives,unary41;39shared,61binaryonly,2unaryonly.
No added coverage over632/640strongestnativehistoricalLinux. Binarygains span
5families;no disagreement. Onebinarycandidate(TokenRing40RC04)checker60stimeout
retainedUnknown. Report`research/signed-threshold-full-v1-report.md`;detailed
costs/families/complementarity`...-summary.json`;reproducer`...summarize...py`.
Maxbinarysolver1.120salthough5sallowance;687unresolvedbinarybranchattempts hit
logical2Mcap versus188candidateexhaustion. Thus no claim all8gaps exhaust language.
Binary100checkedsolvermedian.050s/checker.148s;checkermaximum50.778s. Default
portfolio unchanged;no crosshostcost comparison or measured integratedgain.

Acquisition25370terminal0:all176/176imports,11models,6newfamilygroups. Recorded
`research/general-development-v3-collection-{execution,terminal}.json` andlog.
Collection audit initially failed on two prior serializability source manifests
that arearrays;failure/source preserved`research/general-development-v3-collection-v1-initial-failure`.
Auditor now explicitly classifies these as source-only/noncomparable(metadata
schema verified,no.serpayloadread). Rerunpassed0:905files/958559077bytes,
831referencedinputs,11archives,175exactordered/kindrepresentatives. Soleduplicate
DNAwalker09ringLRRC00/RC07EF. No overlap against included frozenprior metadata;
priorpayloadsnotrehashed,latestladdernotinitsowninventory. ManifestSHA
 d774ca296c4894ba9c77ec8107488699892d9f60de7b8c0022d878864ea0ff71.
22reservedfamiliesuntouched. Difficulty still unmeasured.

Independent Rust/Python importer agreement also PASSED176/176,allbranches/polarity,
inputsunchanged:session36814terminal0. New example`examples/check_original_import.rs`
readsPNML/XMLviaRustparser,compares every typedmodel/targetfield against canonical
Pythonimports. No solver invoked. Onecomparisonmutationunit testpasses,release
examplebuild39319terminal0. Initialcargo fmt--exampleunsupported(nochanges);
correctedrustfmtandtest/buildpass. Existingvendoredvarisatwarningsremain.
Bounded60s/2GiBperqueryreproducer`research/check-general-development-v3-imports.py`;
artifacts`research/general-development-v3-imports/`includeplan,all176rows,summary,
frozenhelperbinaryand69sourcefiles+archive. Executionreceiptupdatedcompleted.

Isolated SMPT runner ready`results/runner-smpt-single-core-v1`,24parentfiles,
onlybenchmark_smpt_classic.pychanged. Fouraddedlabels:smpt-compact-portable,
smpt-pdr-reach-portable,smpt-pdr-saturated-portable,smpt-mcc-portable. --mccpasses
required--methods,butrecordslistignoredforofficialscheduling. Resource/portable
preflight+auto-reduce;alladdedmodesrejectlateanswers;oldmodesbehaviorpreserved.
13mocktests(includingactualSMPTparserASTslice)pass,noexternaltoolsran.
ArchiveSHA5ad4ebe9557775469544182d51e9b9aa8e8e60300fea107aa2b0104ca4eae20d.
Report`research/smpt-single-core-runner-v1-report.md`;notdeployed,nolivecompetitor
preflightyet,needsnewmatrixauditorawareofrequested_methods/schedulingmetadata.

CURRENT LOCAL GATE:session23071higher-workdiagnostic RUNNING. Samefrozenbinary/
runner/twoengines/5swall/2GiB/separate60schecking,maxlogicalwork100M. Exactly10
outcome-selectedqueries:eightnativegaps+twounary-onlyanswers;20rows,parent656/640/16.
Plan`research/signed-threshold-workcap-v1-plan.json`SHA
7d2af05b1eb723e5005f9d62083306cae4f642193f04ccd796cf30296de7d639.
Launcherwritesexecution/terminalreceipts;rootaddedhandle23071toexecutionreceipt.
DO NOT restart;no localbuilds/imports/solvers/export/competingmeasurements until
terminal. Then`research/audit-signed-threshold-workcap-v1.py`,compareall20rows
withv1;nofullcohortgaininference. Fourmetadata/mockpreparationtestspassed.

Linux31728stillauthoritativelyliveatlatestpoll;no remotechanges/builds/transfers.
Afterterminalandlocalgateclear,collect/audithistorical40rowsusingpreparedscripts.
ThenprepareactualsinglecoreLinuxqualificationofnew176cohort,includingstronger
SMPTconfigsafterrealcapabilitypreflight. Fullcohortqualificationstillpending.

Additionalread-onlyspeedlead:priorcompletedinstruction-summaryhaslargewalk-first
overheadsoncheaprefutations(e.g.SmallOperatingSystemMT2048DC1024RC12:1.577Bvs2.097M
instructions,752x). Savedbatchedansweris2quickcausalFarkasbranches,sourcewalkmode
runsupto100mswalkbeforecausal/relevance. Notanewmeasurement;noimprovedschedule
implemented. Investigatecheapprecheck/reusablesolverstateaftergatesratherthan
lettingpositive-onlywalksdominateeasynegatives. No novelty/superiorityclaim.

### Same turn: higher-work diagnostic completed

Session23071authoritativeexit0;auditoralsoexit0. All20rowspass. Binary1/10,
unary2/10checkednegatives;NONEof8historicalnativegapssolved. Binaryrecovers
SharedMemory50RC04(0.840s+.939schecker),alreadyunarysolved. TokenRing40RC04binary
againchecker60stimeout;unarypasses(.531s+28.515s). Sixbinarygaprowsreachouterwall,
NoCexhaustsboundeddiscovery,Shared200RC04stilllogical100Mlimit. Report
`research/signed-threshold-workcap-v1-report.md`,all20comparisons
`research/signed-threshold-workcap-v1-comparison.json`. No fullcohortinference.
Initialad-hoccomparisonreadfailedonemptytimeoutJSON;correctedcomparisonpreserves
emptyoutputsandtimeoutreasons. Thiswaspostprocessingonly,notanexperimentfailure.
Do notpromotethresholdenginebasedonthisdiagnostic. Newcohortqualificationand
walk-firstoverheadtakepriority. CURRENTLOCALGATECLEAR:no localmeasurementknownlive.

Linux31728remainsliveatlatestauthoritativepollAFTER23071completion. No remote
builds/transfers/qualificationuntilterminal. Preparedcollectorcanrunthenbecause
local34053(andfollowup23071andimports36814)alreadyterminal. Historicalcollector
requires`research/hard-survivors-current-v2/terminal.json`authoritativeexitreceipt.
New176cohortreadyforqualificationbutnoneexecuted; strongerSMPTrealcapability
preflightandmatrixauditoradaptationstillneeded. Catalogv6predatesthiswholeturn.
OneoptionalquestionaboutLinux-onlyartifactversusmacOSsupportpending;notablocker,
publicationmeasurementsremainsinglecoreLinuxasuserexplicitlyrequested.
