# 2026-09-28 continuation

Deployment completed: 867 missing files transferred; all 907 runtime and 33 preflight pins verified on Linux. Existing files were never replaced with different bytes. See deployment.json and deployment-inventory.json. Linux idle observation and perf smoke succeeded. Historical survivor run remains interrupted 27/40; no restart.

Capability v1 and v2 each terminated exit 1. Their 36-row outputs are preserved remotely. Synthetic PNML lacked names (v1), and both lacked the PNML namespace required by SMPT ids_mapping. SMPT failed with KeyError q before solving; these are fixture compatibility failures, not solver coverage results. v3 has explicit names and the exact namespace from SMPT source.

CURRENT: local exec session 75689 runs remote research/preflight-general-development-v3-linux-v3.py, stdout/stderr in capability-v3-run.log. Poll this handle before doing any further remote solver work; do not restart on observation failure. Original plan and all pinned runner files unchanged. If passed it writes capability-harness.json, not the final capability.json.

Next run the already deployed research/preflight-general-development-v3-components.py after v3 is authoritatively terminal and passed. This exercises fully reduced SMT/CP plus portable WALK using Linux limits and perf, then writes capability.json only on success. Inspect all evidence and fetch capability artifacts before launching the full frozen 1584-row qualification. Full run is NOT launched. Preserve all failed smoke artifacts and scripts. Strengthen smoke audit if discrepancies emerge.

User suggested BMC + acceleration as the coherent algorithmic direction. We have exact repeated-word enabling/effect summaries in src/klmst.rs and single-transition acceleration in src/repeat_fire.rs, but no integrated accelerated BMC refinement loop. Explore a bounded path-scheme SMT encoding with symbolic repetitions and exact prefix guards; bounded UNSAT must remain unknown for global unreachability. This is a proposal, no implementation or performance evidence yet.

## Later continuation: capability passed; full run launched

v3 session75689 terminal0. All36harnessrows pass. Component session49289 terminal0:
SMT SAT/UNSAT,CP SAT/UNSAT,WALK SAT all pass with matching techniques and real
Linux cgroup/perf. Fetched all three smoke attempts, corpora, logs and receipts in
capability-evidence.tar.gz; hash f13522cf74bba6d0bdff8fe673937fd2d599529d1e353a766ad91f4d5598b81c.
Verified final plan/runs/environment hashes, five component log hashes and all36
expected truth values, with no capability/subprocess/validation failures.

Full frozen qualification now RUNNING remotely, detached from SSH:
pid561786,creation1790597491.09,boot17c1d989-ad9a-424e-9347-88bc5cb8e11b.
Dispatch receipt saved locally/remotely. `research/poll-general-development-v3-linux-v1.py`
checks exact process identity and terminal receipt. Latest observation:live,86/1584rows.
No remote solver/build/deployment/bulk collection until terminal; no restart.
Next fetch complete outputs and run existing artifact auditor after terminal.

Local accelerated-BMC prototype implemented and tested (not in running benchmark).
See research/accelerated-bmc-prototype.md. Four new Rust tests, four existing summary
tests and 66 real Z3 semantic checks pass. Every51SATmodels checked independently
in Python, including compressed trillion-step witness. Vocabulary manually supplied;
automatic discovery, bounded production runner and fair performance ablations remain.
Clippy session93137 was launched last; poll before new local cargo work.
Goal remains active; no superiority/publication-readiness conclusion.

Clippy93137 initially failed on one test-only unnecessary clone. Replaced with
slice::from_ref; clippy80685terminal0. Changed-file rustfmt check passes. Existing
vendored varisat warnings remain. Latest exact-identity Linux poll:live107/1584.

## Automatic-word prototype continuation

Previous turn is concrete progress plus verified remote wait. Added word_discovery.rs:
all singletons plus budgeted shortest production-dependency cycles, no model-name
special cases. Added ordinary-BMC ablation, sparse frame encoding, whole-query
Python Rust/Z3 driver and independent compressed checker. Default/main portfolio
unchanged. Twelve targeted Rust tests,66Z3queries,3mode ablation and6driver checks
pass; final targeted Clippy98817terminal0 and formattingpass. All local cargo
sessions terminal; driver/sparse semantic56650terminal0.

Frozen complete classical development screen8165terminal0:111/111rows auditpasses.
Ordinary0/37, singleton1/37,cycles1/37 checked reachable; bothaccelerated solve3u.
All othersUnknown. Historical checked classic-v2-final contains only1positive,
36negative per repetition, so this is a weak positive-search benchmark, not evidence
that all36unknowns are missing reachable witnesses. Source/binary frozen in
results/solver-accelerated-bmc-v1; full results/plan/audit in
results/abmc-classic-mechanism-v1. Report research/accelerated-bmc-discovery-v1-report.md.
No speed/competitive/novelty claims. Local measurement gate now clear.

Next: full192-property MCC DEVELOPMENT (not evaluation) mechanism/control screen.
Need preregister matched frozen native control: local solver-repeated-search-v1
binary exists; strongest walk-sparse-v2 local artifact contains only source tar,
Linux executable is remotely pinned. Can rebuild exactv2source locally in isolated
checkout if using strongest baseline; never substitute localbinary for remotepin.
Avoid selecting only known positive cases; retain complete192denominator.

Remote qualification pid561786 exactidentity last verifiedlive291/1584rows. Use
poll-general-development-v3-linux-v1.py; no remote work until terminal. Full goal
still active and substantially incomplete.

## Full192development comparison completed and audited

No rebuild needed: local walk-sparse-v1 binary matches provenance; all200v1source
files are preserved in v2Linux packaging. Strong local control therefore reused
that exact frozen Mac binary, alongside repeated-search-v1 frozen control.
Prepared960row plan SHA25d4ee18b974f1f2180dfdd98486fe3b0448d94e3a8fbe7e893acdc28264d6ee.
Ten capability cases pass32144terminal0. Initial source-snapshot-path launch failed
before execution/rows because ROOT pointed at nestedsource; failedlogpreserved.
Rootcontrollerhashverifiedidentical; corrected34323terminal0,960rows auditpassed.
No validation warnings/disagreements. Local measurement gate CLEAR.

Coverage(R/U/?):ordinary67/0/125,singleton68/0/124,cycles69/0/123,
native-walk101/85/6,native-frozen98/85/9. All47initialpositive properties solved.
Cycle3gains2losses vs singleton; no positives beyond either nativecontrol.
AllBMCdiagnosticunion71 addsnonevswalk. Native judgments independently checked.
Reportresearch/abmc-mcc-development-v1/report.md and audit.json/diagnostics.json.
Reproducerresearch/run-abmc-mcc-development-v1.py; frozen evidence/results preserved.
Ad-hoc diagnostics initially typo'd map/json argument; corrected reusable summarizer
passes and writes diagnostics. No experiment rerun or lost rows.

NEXT IMPLEMENTATION: real sparse word summaries. Current formula sparse but summary
construction dense words*places; eachBMCmode hits200k summarycell cap on80branches
across48properties,21ofwhich native findspositive. Don't removecap blindly.
Candidate implement sparse guard/effect maps and sparse per-place selection terms,
keep dense independentchecker and differentialtests; freeze new candidate and rerun
full192cohort with matched controls/limits. Then incrementalZ3 prefix-model discovery.

Relatedwork primarysource inspected: Frohn/Giesl FM2024 ABMC DOI
10.1007/978-3-031-71162-6_4; PDF/provenance/Crossref/OpenAlex/evaluationpage saved in
research/accelerated-bmc-related-work-v1. Algorithms2/3 visually reviewed pages6/11,
Sections3/4/6text inspected. Dynamicprefixmodels,cacheIDs,blocking requiringEXACT
acceleration for safety. Ours lacks these; no noveltyclaim. LoATv0.7.0 release metadata
saved (69MBstaticbinarynotdownloaded),2.18GBZenodoartifactmetadataonly. Readassessment.md.

Linux561786 remained exactidentitylive at latestpoll590/1584; no remotebuilds,solvers,
transfers untilterminal. Continue poll script, then collect and existingaudit.

## Sparse-summary candidate implemented, verified, full comparison RUNNING

Previous goal turn was a verified wait (Linux exact-identity live665/1584).
This turn implemented sparse BTreeMap hurdle/effect summaries in accelerated_bmc.rs,
per-place nonzero effect indexing, and sparse-construction work accounting in the
Python driver (vocabulary+word lengths+2*arc visits). Dense witness checker retained.
No default change. Report research/abmc-sparse-summaries-v1/report.md.

Two new unit tests pass (5832 dense/sparse word comparisons and cancellation/read
case);12integrationtests;66Z3queries/51independentSATchecks;three-modeablation;
sixdriverchecks;three500-place/budgetregressions;targetedClippyandformatpass.
Synthetic ablation formula hashes unchanged. All build/check sessions terminal.
Initial test command filtered out integration tests; separate unfiltered run passed.
Systempython prepare failed before any artifact due missingpsutil; preserved note,
then used exact previous vendor/venv/bin/python. Frozen prior results untouched.

NEW LOCAL FULL SCREEN RUNNING: exec session47272, redirected to
research/abmc-mcc-sparse-v1/run.log. Last confirmedlive21/960rows.
PlanSHA7895a8c918a2ad7a1b8a88900d85d6a817640a2fd6f64f42cfe843e9f5a80f31.
10smokecasespass;192properties,same5modes/order/1sbudget/controls as previous.
Frozen results/solver-abmc-mcc-sparse-v1; output results/abmc-mcc-sparse-v1.
Use vendor/venv/bin/python research/audit-abmc-mcc-sparse-v1.py after terminal,
then research/summarize-abmc-mcc-sparse-v1.py; compare against previous complete
screen conservatively (one shared-Mac repetition, no stable timing claim).
Do not build or launch other local solver measurements until47272terminal.
No restart on observationfailure. No performance result yet.

Linux remote561786 last exactidentitylive714/1584. Existing poll script only;
no remotebuild/deployment/solver/bulktransfer before terminal. Goal stillactive.

## Collection and paired-analysis preparation

Previous turn classified progress (sparse summaries + verification + frozen launch).
This turn both jobs authoritatively confirmed LIVE: local exec47272 (510/960rows),
remote exactidentity561786 (817/1584rows). No other builds/solver runs or bulk transfer.
Added research/collect-general-development-v3-linux-v1.py: --check remotely verifies
dispatch identity/liveness/terminal plan pin; actual collection also requires local
and remote workload gates clear, validates archive paths/types/duplicates, stages
all files and checks existing bytes before importing, records SHA256 file inventory.
--check executed successfully and returned live=true,terminal=null,ready=false.
No results archive created. Full collection/extraction remains unexecuted pending
terminal and measurement gates. Invoke with vendor/venv/bin/python once BOTH runs
are terminal, then existing Linux auditor. Preserve failed/partial archives.

Added research/compare-abmc-sparse-v1.py. Requires two passed audits and identical
inputs/order/budgets/native controls; reports per-mode paired gains/losses and caps,
with no stable timing claim. Both new scripts AST-parse, but full execution awaits
completion. Local next: poll47272; on terminal run sparse audit, summarizer, then
paired comparison. Preserve all outcomes and investigate disagreements.

## Sparse screen complete and audited; next architectural experiment

Previous turn classified progress (guarded collector + paired report preparation)
and verified wait. This turn local47272 TERMINAL0,960/960; auditpassed, no warnings
or disagreements. Unchangedcontrols exactsameanswers. R/U/?: ordinary67/0/125,
singleton69/0/123,cycles69/0/123,nativewalk101/85/6,frozen98/85/9.
Only pairedchange singleton gainsTokenRing-PT-005__RC14; no otherpositivegains/losses.
BMCunion71 addsnothingbeyondcontrols. Reportresearch/abmc-mcc-sparse-v1/report.md.
Auditor,summarizer,compare scripts executedsuccessfully; all logs/artifacts saved.

Added/executed diagnose-abmc-sparse-followthrough-v1.py: all80formerlysummarycapped
branches across48properties perBMCmode stillunknown. Outerexpiration counts74/73/75;
encodingcap5/6/5,ordinaryoneencodingdeadline; zeromemorylimitfailures. Summarycap
removed, but no substantialcoveragebenefit. Phasefilepresence shows SMTinvocations
atdepth1/2/4; logs do NOT provide phase duration attribution. No timingclaim.

LOCAL MEASUREMENT GATE CLEAR. Next implement persistent incremental SMT (reuse Rust
summaries and prefix constraints) as a separate ablation from feasible-prefix-model
wordlearning. Record phase timings. Keep original-transition-word exact summaries;
be careful nested symbolic repeat counts introduce products and are not QF_LIA.
No safetyblocking/globalnegativeproof claim. PublishedABMCpriorart inspected earlier.
Freeze and run fullcohort after meaningful semantic/tests; do not tune only gains.

RemoteLinux561786 still exactidentityLIVE962/1584, no terminal. Pollsamejob; no
remotebuild/deployment/solver/bulktransfer. Collector prepared lastturn still must
wait for terminal. Goalactive and substantialperformance/noveltyevidence absent.

## Encoder refactor and user architecture question

Started incremental work: accelerated_bmc.rs now has reusable Encoder with cached
sparse summaries/effects, initial/extend_to/target/values methods. Existing encode
uses it. This is ONLY encoder refactoring: no persistent SMT driver/session or
learning implemented yet. Two summaryunit tests,12integrationtests,debug example
build,and66realZ3semanticqueries/51independentSATchecks pass. Logs /tmp/pvass-
incremental-encoder-{build,tests,example,semantic}.log. Sessions97954/85119terminal0.
Release example NOT rebuilt; current default experimental Python still uses old
release binary, frozen results unaffected. Need direct incremental push/pop tests
and Clippy before treating Encoder API as verified for incremental sessions.

User asks whether SMT is necessary or we can make an independent tool. Answer:
SMT is optional; strongest native portfolio already independent of externalSMT.
Standalone native accelerated search is viable, but requires own repetition-count
constraint solving/pruning. Recommend native Rust as main backend, Z3 as experimental
reference, given current evidence. User has not explicitly directed abandoning SMT
experiments; do not infer that question alone cancels goal or authorizes superiority
claims. No new benchmark launched thisturn. Remote lastknownlive962, re-poll.

## Native fixed-scheme arithmetic implemented and verified

Previous goal turn progress: reusableEncoder refactor+66semantics; user asked ifSMT
needed, answerednativepossible/currentstrongestalreadyexternalSMTfree. This turn
implemented path_scheme.rs and examples/native_path_scheme.rs: fixedorderedwords
with strictlypositiverepetitioncounts, x=n-1 encoding, exactBigInt linear guards,
existing complete_arithmetic::solve_integer, independentdensecompressedcheck.
No externalSMT process. SparseWordSummary/sparse_summary moved from accelerated_bmc
into summary.rs and shared. No new vocabulary heuristic/search or defaultchange.
Native scheme infeasibility is only scheme-level; CLI maps to reachabilityunknown.
Explicitentrybudget,requireddeadline,arithmeticrow/nodecaps; outerguard stillneeded.

Tests:10368directreplayconstraintassignments;trillioncompoundwordnativewitness and
disabledinternalguard;empty/budget/malformedcases.14realZ3fixedschemecases agree,
5positivePythonchecks.12integrationtests,66BMCsemantics,andtargetedClippypass.
Semantic source hashes match current. Report/logs research/native-path-scheme-v1;
research/check-native-path-scheme-v1.py reproducible. Sessions78132,73019,99374,
23549allterminal0. Debugexamplesrebuilt; releaseexample NOT rebuilt. No benchmarks.

NEXT: native automatic scheme selection/refinement, using this arithmetic primitive
rather than launching SMT. Need a coherent bounded algorithm, cost measurements,
and whole-cohort comparisons. Do not present manuallysuppliedschemes as a complete
solver improvement. Reusable SMT Encoder remains available as reference, but no
persistent SMTsession driver or directpush/poptest yet. No noveltyclaim.
RemoteLinux561786 lastconfirmedlive1123/1584 before finalpoll. Poll samejob and
collect/audit only when terminal. Local measurementgateclear. Goal remainsactive.

## Automatic native scheme search implemented; full v2 screen RUNNING

Previous turn progress: nativefixedschemearithmetic+verification. Added
scheme_search.rs, examples/native_scheme_search.rs: automaticdependencyworddiscovery,
boundedBFS withlazychildgeneration,adjacentidenticalwordmerge, nativeexacttarget
queries and target-freeprefixqueries. Only exactprefixinfeasibility prunes; Unknown
extends. Search/agenda/entries/deadline/querybudgets; allglobalfailuresUnknown.
Discovery/target/prefixtimes recorded. NoexternalSMT; nodefaultchange ornoveltyclaim.
Reportresearch/native-scheme-search-v1/report.md. Unit3tests,4end-to-endcases,
productionPythoncheckerCLIforpositives,targetedClippy/releasebuildpass.

First freeze/smoke native-scheme-development-v1 FAILED on missing reportedmarking
in CLIoutput (witness valid). Preserved completefailedsnapshot/plan/smoke/logs; no
fullrowslaunched. CorrectedCLI addsdensecheckedmarking; testsnowexercise actualCLI
checkercontract. New v2freeze/smoke10casespass. Allbuild/test/smokesessions terminal.

LOCAL NEW FULL RUN LIVE exec53031, logresearch/native-scheme-development-v2/run.log.
PlanSHAa76f6820cbca629ab22f4d5d6f4130aa2b12e7bbd441f1804f1f46239a3818e2.
192propertiesx5modes=960rows: native-singleton,native-cycles,cycles(SMT),native-walk,
native-frozen. Native depth4/schemes256/query50ms/rows4096/nodes4096/entries200k;
SMTfrozenunchangeddepth16. Same1spropertybudget/sharedbranches/sample2GiB.
Frozenresults/solver-native-scheme-development-v2; rawresults/native-scheme-development-v2.
No localbuild/solverexperiment/bulktransfer until53031terminal.
Oncompletion run vendor/venv/bin/python research/audit-native-scheme-development-v2.py;
report completecoverage and investigate any warnings/disagreement before conclusions.
Auditor adapted for positionalnativeCLI and compressedmarking; not yet executed on
completefullresults. Preservefailures. Comparison is algorithmic/internalboundsdiffer.

RemoteLinux561786 lastconfirmedlive1264beforefinalpoll. Pollsameprocess; no remote
build/deployment/solver/bulktransfer untilterminal. Guardedcollector exists; wait
for BOTHmeasurementgatesclear. Goalactive; performance not yet established.

## Native v2 audited; root-guard optimization v3 RUNNING

Previous turnprogress(auto native search+frozenv2launch). This turn53031terminal0,
960rows auditedPASS,no warnings/disagreements. R/U/?: native-singleton61/0/131,
native-cycles60/0/132,SMTcycles69/0/123,nativewalk101/85/6,frozen98/85/9.
Nativecyclesgainsnothingvsanycontrol/singleton,losesSharedMemory5RC13vssingleton.
Nativeinitialpositives47each. Reportresearch/native-scheme-development-v2/report.md.
New summarizer and rootdiagnosis scripts executed and reports saved.

Measured root-only unknownbranches singleton81/cycles113; cyclesroot-onlyattempts
27313,prefixrefuted25656. Implemented exactroot-hurdlecheck before arithmetic attempt
count, recordsroot_guard_checks/root_refutations; skipredundantprefixquerywhenroot
isexactlyenabled. GeneralprefixUnknown stillretained; only exactinfeasibleprunes.
4unittests,4productionCLIcases,Clippy/releasebuildpass. Report/rootguardlogs in
research/native-scheme-root-guards-v1. Alltestbuildsmokesessions terminal0.

NEW LOCAL LIVE exec77187: research/native-scheme-development-v3/run.log;
960rows,planSHAa6c242699f40a9fc2f6deaeac8c971bc30496d9771bfe4208ddd0c224877bcc5.
10capabilitycasespass. Same5methods/input/order/wallbudget/controls asv2; rootchecks
no longerconsume256arithmeticattempts. Preserve priorv2unchanged.
Onterminal run vendor/venv/bin/python research/audit-native-scheme-development-v3.py
then summarize-native-scheme-development-v3.py. Compare fullpairedsets tov2;
no further localbuild/solvermeasurements/bulktransfer until77187terminal.

Linux561786 lastconfirmedexactidentityLIVE1480/1584,noreceipt. Remotejob may finish
soon; pollsameprocess. No remotechanges/bulk untilterminal. Guardedcollector requires
bothlocal/remote measurementgatesclear; then collection+Linuxaudit are highpriority.
Goalactive; no substantialadvantage demonstrated. Defaultportfolio unchanged.

## BOTH screens completed, collected and audited; all gates CLEAR

Previous turn progress(nativev2audit+rootguardimplementation+v3launch). This turn
local77187terminal0,960rows. Nativev3audit/summarizer/pairedcomparisonPASS withzero
warnings/disagreements. Native-singleton61positive/native-cycles60positive unchanged
sets; SMT69positive; nativewalk101R85U; frozen98R84U (one lostnegativevspriorrepeat,
SharedMemory20RC08). Reportresearch/native-scheme-development-v3/report.md. Root
pruning removesmanydisabledproposals but coverageunchanged; arithmeticbudgetspent
onothercandidates. Stop assuming more smallguardtuning fixesuninformed BFS.

Remote561786 AUTHORITATIVELY TERMINAL0,notlive,1584rows. Finalreceipt2026-09-28
13:28:29UTC. Collected6060files/4331803bytes; archiveSHA
86014ebcbe46887b0d9e753422143317c4510540a88b1a28810f54dd654ce04c.
Initialcollectorimportfailedbeforewrites: dispatchJSONformatdiff(local411bytes vs
remote448),semanticallyidentical. Preservedfailedlogandcollector; added
--import-existingandremote-receipts/dispatch.json remap (neveroverwriteoriginal).
Imported existingarchive successfully, no retransfer. collection.json inventories
hashesandpathmapping. Collector45246exit1preserved; import+audit89335terminal0.

LINUXAUDITPASSED0issues/0disagreements:176properties/175exactrepresentatives.
Nativewalk87R45U=132;batched83R45U=128;frozen83R45U=128;VerifyPN83R46U=129;
SMPTfull47R30U=77;compact47R30U=77;PDR19R7U=26;saturated15R11U=26;
officialMCCportable51R45U=96. WalkvsVerifyPN5gains2losses;vsSMPTMCC36gains0losses;
vsfrozen4gains0losses(allRERScheckedpositives). Nativeonly4;competitoronly2VerifyPN
CloudReconfiguration311RC06,RefineWMG100101RC11. Allmethodsunknown42 (41distinct),
DNAwalker/RERS. 4warnings aboutmissingperf on2interruptedSMPTsaturatedrows; noimputation.
StrongSMPTconfig improves19vsfull. One5srepeat, no substantialsuperiority claim.
Reportresearch/general-development-v3-linux-v1/report.md; summary.json and audit.json.
Added/executed summarize-general-development-v3-linux-v1.py. Entire rawresults in
results/linux-general-development-v3-v1. No remotejob remains to poll/restart.

Fixed common scripts/process_runner.py workloadinventory to recognize newnative
examplesandargvbasename. Observed live native_scheme_search pid97917 aspositivecheck,
then emptyaftertermination. This commonhelper edit occurred afterv3freeze/launch;
runningrunner's loaded/frozensourceunchanged, not silentlyupdatedbaseline. No new
measurement ongoing; LOCAL+REMOTE GATES CLEAR. Collector helper remote remains
old but no newexperimentalnativebinaries were launchedthere.

NEXT architectural work: native target/model-guided scheme selection/refinement,
rather than vocabularyBFS, with fullcohortablation againstfrozenreferences. Existing
nativearithmetic/correctnessfoundation valid but no coverageadvantage. Alternative
highvalue investigation: twoVerifyPN-onlycases and42all-unresolved cases, with
registeredlongerbudgets beforecallingthem intrinsicallyhard. Need meaningful
contribution,heldout/repetition,strongcompetitiveevidence; goalstillactive.

## VerifyPN-only diagnosis: checked 9970-step witness beyond old count cap

Previous turnprogress: bothfullscreenscompleted/audited, Linux132vs129vs96 etc.
This turn examined competitoronly2cases. Cloud311RC06 reportednegative byVerifyPN;
RefineWMG100101RC11 reportedpositive. Frozenlocal8canonicalbranchesx2methods
(portfolio-walk,sparse-count-plan),2s/branch exploratorydiagnostics,16rowsterminal0.
Allunknown. Refinecountplanner nointegermodel; Cloudmanysupportrefinements.

Found hardcoded8192totalfiringcap. For Refinebranch4 nativeFarkas boundrefutation,
independentPythonFractioncheck reconstructsoriginalarcs/targets and proves
sumcounts>=99283/10 hence>=9929. Usesbranch4targetrows0+1; don'tgeneralize toallbranches.
Added public count_plan::solve_sparse_with_cap and examples/count_plan_diagnostic.rs;
existingdefault+allfallbacks KEEP8192. Updated5privatecallers afterinitialcompile
failure (logpreserved). Existingcounttests+newcount_captest+targetedClippypass.
examples/count_bound_diagnostic.rs builds/proposesboundcerts; standalonechecker
research/check-count-bound-diagnostic-v1.py verifies independently.

Registeredbranch4caps8192/16384/65536,5sinternal/5.3outer/sample2GiB/check30s:
8192unknown(0models);16384and65536REACHABLE9970firingwitnesses, independentlychecked.
cap-auditpasses allsource/logpins andsavedcheckerreceipts. Report andeverything in
research/verifypn-gap-diagnostics-v1. Scripts diagnose-verifypn-gaps-v1.py,
probe-count-caps-v1.py. Allsessions73412,93182,47942(failedcompile),52443,76385,88880
terminal; no ongoingbuild/benchmark. Nativecountplan defaultunchanged.

NEXT: principled countcap derived from remaining expanded-trace statebudget
(currentrealizerconsumesstatepertransition; maxstates2M vs countcap8192). Don'tjust
hardcode16384foronecase. Test complete192development cohort against8192/frozenstrong
controls, not justthisgain. Need wholeproperty original-input confirmation too.
If compressedrealization introduced later, statebudget!=firingcountbudget anymore.
Cloudnegativegap remainsseparate. All Linuxjobs completed; doNOTrestart oldones.
Goalactive; substantialadvantage/coherentnovelresearch stillunproven.

## General count-budget policy verified; full cohort RUNNING

Previous turnprogress(diagnosed8192cap,proved>=9929,checked9970witness). This turn
added count_plan::solve_sparse_with_state_budget and CLI sparse-count-plan-budget.
Each arithmetic query cap=min(i32MAX,max_states-states-1), matching realizer's
pre-acceptance limit check. Shared CountCap policyimplementation; oldsolve_sparse
and densefallbacks retainFixed8192. No defaultportfoliochange. Existingcounttests,
3captests(boundaries,empty,9000witness),targetedClippy,example+CLIbuildpass.

RealRefinebranch4fixedunknown/budgetreachable9970 independentlychecked. FULLORIGINAL
RefineWMG100101RC11 PNML/XML5s+buffer-agglom: fixedunknownallsix; budgetREACHABLE
branch0,29381firingwitness. Existing boundedrust-original-v1validator independently
translates originalinputs/canonicalagreement and replays; python-witness passes.
Reportresearch/count-budget-policy-v1/report.md; original-plan/results/logs and
semantic.json saved. No crosshosttimingcomparisonclaim.

Preserved oldcap-probe source againstrecordedhashes. Reconstructed original
count_plan.rs byreversingnewpolicy andverifiedSHAidentical; savedbinaryandhelpers.
Mappingresearch/verifypn-gap-diagnostics-v1/cap-source-snapshots.json (postrunarchive,
not pretendedprefreeze). Extendedcommonworkloadgate names for count_plan_search and
count diagnostics BEFORE newfullfreeze. Allbuild/test/diagnostics terminal.

NEW LOCAL FULL RUN LIVE exec6811, logresearch/count-budget-development-v1/run.log.
PlanSHA40655271b11a809126e02abe33c0c23d5361c027ca2911b8b4c4153b2d8ca749.
192propertiesx5modes=960:count-fixed,count-budget,cycles(SMT),native-walk,native-frozen.
Sameorder/1spropertybudget/sampled2GiB/independentchecks aspreviousscreens.
10capabilitycasespass. Source+candidateexample+experimentalCLI frozen in
results/solver-count-budget-development-v1. No localbuild/solvermeasurement until
6811terminal. Oncompletion run research/audit-count-budget-development-v1.py using
vendor/venv/bin/python, then summarize fullresults and pairedcount-budget/count-fixed.
Auditor adapted for ordinary expanded-witness checker, not compressed checker.
No fullcohort resultyet. BothpriorLinux/localrunsalreadyfinished; don'trestart.
Goalactive: this is promisingcheckedgapclosure, not substantialgeneraladvantage.


## Count cap audited; optional portfolio integration verified

Previous user-facing turn answered the SMT question without changing state (no
progress); this continuation verified current files and resumed implementation.
Old count-budget development session6811 terminal0: full960rows auditPASS with no
warnings/disagreements. Fixed and state-budget counts both93R/0U/99unknown, exact
same positive set. SMT69R; walk101R85U; frozen98R85U. Report now saved in
research/count-budget-development-v1/report.md. No new coverage on192; the
RefineWMG gain remains outside that cohort. Old remote Linux run remains finished.

Added optional CLI portfolio-walk-counts, same walk warmup then sparse count budget
min(remaining/5,250ms), gated by sparse construction work, accepting only reachable
and falling back to unchanged relevant/causal/batched portfolio. Original-input
capacity preprocessing enabled as for portfolio-walk. Defaults unchanged.
11 targeted tests pass, including9000trace, warmup, checkednegativefallback,
restart validation; targetedClippy+releasebuildpass. All build sessions terminal.

Original PNML/XML RefineWMG100101RC11 at5s: matchedwalk outerexpired at5.3s, empty
output preserved unknown; countportfolio REACHABLE branch0,29381trace independently
translated/replayed using boundedrust-original-v1 validator. Wall0.173s in one Mac
probe, not stable timing. Fullsource/binarysnapshot, plan/results/receipts,
originalaudit and report at research/portfolio-walk-counts-v1.

CURRENT LOCAL FULL RUN exec73728, research/portfolio-counts-development-v1/run.log.
Frozen192propertiesx3modes=576rows, candidate/native-walk/native-frozen;1sproperty,
sharedcanonicalbranches,sampled2GiB,independentchecks. PlanSHA
55930816fd6efbb35535d5a79d0ed08a56f06b7e90fd676a437d942107aaaf33.
6capabilitycasespass. Source+3binariesfrozen results/solver-portfolio-counts-development-v1.
Lastobservedlive380/576. Pollsamehandle; no otherlocalbuild/measurement/bulktransfer
untilterminal. Then run research/audit-portfolio-counts-development-v1.py and report
pairedpositive AND negative losses/gains; audit adapted but not yet run fullmatrix.
Goalactive; broader harder original-input Linux screen and heldout/repeats remain.


## Portfolio development screen completed and audited; all local gates CLEAR

exec73728 terminal0, all576rows; auditPASS, zero warnings/disagreements. Candidate
and frozenwalk both101R85U6unknown, EXACT same definitive sets (no positive or
negative losses). Frozenexisting98R85U9unknown. Bothwalkmethods gainTokenRing15
RC08/RC14/RC15 overfrozenexisting. Report, audit, diagnostics saved in
research/portfolio-counts-development-v1. New summarizer records all definitive
pairedgains/losses, not just positives. No localbuild/measurement remains.

NEXT: harder176original-input Linux candidate screen with fair frozencontrols and
same5s/cpu8/enforced2GiB/boundedindependentvalidation as previous qualification.
Need freeze/deploy new candidate source and rebuild Linuxbinary with provenance;
never reuse Macbinary remotely or substitute historicaltimings for matchedrepeat.
Existing fullLinuxcomparison completed/audited; do not restart old561786job.
Candidate default not promoted. Coherent novelalgorithm, heldout/repeats and
substantialgeneraladvantage stillunestablished; goalactive.


## Harder candidate comparison prepared, verified and RUNNING on Linux

Previousgoalturnprogress: candidateintegration+full192audit186/192nochanges.
Thisturnprogress: froze/deployed candidateLinuxsources, matchedRust1.97.1build,
11testsPASS, all20configurationcapabilities+5SMPTcomponentsPASS, fetched/audited
capabilityevidence, froze880rowplan and dispatched fullcomparison.

Initialbuild20849terminal101 because defaultRust1.78lacksedition2024. Preserved
build-portfolio-counts-linux-v1.py, build.log/build-receipt.json and localstdout.
Explicit1.97.1 v2build21558terminal0, tests11pass. No sourcechange, same source pins
as testedMacfreeze. Allbuild artifacts collected results/linux-solver-portfolio-counts-v1.
Capability82458terminal0; components30234terminal0; fetchedarchiveSHA
cdbf5a999c269179d06af81429214a9c5ac54c0252586e0e3f7cf5f376f5c5cb.
LocalartifactauditPASS. Runtime1158/preflight45pinsverified before launch.

NEW REMOTE JOB pid1211679,created1790604831.58,
boot17c1d989-ad9a-424e-9347-88bc5cb8e11b, exactidentityconfirmedLIVE,
executionexists, no terminal, initially0/880rows. Folderresearch/portfolio-counts-linux-v1;
outputresults/linux-portfolio-counts-v1. PlanSHA
 de15c42faa62b3dffd6a8a27a6d922b7691fe1fbc51edf54b19cdb903cb38f40.
176properties/175representatives,5s,CPU8,enforced2GiB,perf,1repeat;
native-counts/native-walk/native-frozen/VerifyPNdefault/SMPTMCCportable.
Strongcompetitorselectionbasedoncompletedpriorwholecohort; no instanceoracle.

Poll research/poll-portfolio-counts-linux-v1.py; doNOTrestart on observationfailure.
No remote build, solver, deploy or bulk transfer until authoritative terminal.
Local gateclear; no localjob. Ontermination collect with
research/collect-portfolio-counts-linux-v1.py then generic audit explicit
--plan research/portfolio-counts-linux-v1/plan.json
--results results/linux-portfolio-counts-v1
--output research/portfolio-counts-linux-v1/audit.json;
then research/summarize-portfolio-counts-linux-v1.py. README has exactcommands.
No competitiveoutcome yet. Goalactive; novelty/substantialadvantage/heldout stillopen.


## Local Cloud negative diagnosis independently verified; Linux still LIVE

Previousgoalturnprogress: deployedmatchedLinuxcandidate and launched880rowcomparison.
Thisturnprogress: studied savedVerifyPNCloud311RC06log (2585/3095 ->52/115,
3410explored); added bounded reductiondiagnostics and reducedsearchablation.
Two existingbuffer/relevance rounds yield branch0 87places456transitions andbranch1
84/453. BFS exhausts101476/74840states; frozenportfolio-counts unknown onboth at3s.
Duplicate removal yields184/180distincttransitions, unlocks3morebuffers, final84/181
and81/177. BFS exhausts67960/43090; portfolio also negative onthese diagnosticnets.
First-round-onlyBFS not measured: don'tattribute gain to saturation/dedupalone.

CRITICAL VERIFIED ORIGINAL RESULT: newexamples/reduced_closure_diagnostic.rs preserves
4reductionsteps plus reducedBFSanswer. check-cloud-reduced-closure-v1.py independently
translatesoriginalPNML/XML,checksallcanonicalbranches,reconstructseachbuffer/relevance
step,comparesfinalnet,and exhaustivelychecksclosure. BOTHbranchesPASS, originalproperty
UNREACHABLE independentlyestablished. NOdedupusedinthisoriginalproof. Perbranch3s
allocation,observedwalls0.676/0.316s;checks9.115/6.679soutside timing. Diagnostic,
not productionwholepropertybenchmark or stabletiming. ArtifactauditPASS.

Everythingresearch/cloud-reduction-diagnostics-v1: initialplan/results, dedup/,
search/(8rows),closure/(plans,snapshots,chains,checkerreceipts,audit). Report.md details
limits. Diagnostic Rust examples compiledrelease; all sessions11364,41219,95135,
79080,51103terminal0. No localmeasurement remains. Addedbothdiagnosticbasenames to
currentprocess_runnerworkloadgate AFTERfrozenruns; preserved snapshotsunchanged.
Main/defaultsolverunchanged. No noveltyclaim; productionneeds bounded compositional
reductions+finiteclosureproofsupport with witnesslifting and independentchecking.

Remotecomparison pid1211679 lastverifiedexactidentityLIVE144/880,noterminal.
Pollresearch/poll-portfolio-counts-linux-v1.py; no remotebuild/solver/transfer until
terminal. Do not restart. Collection/auditinstructions in previoushandoff and newREADME.
Nextlocally:first-roundBFSablation; then generic checkedreductioncomposition/closure
if justified. Fullgoalactive,heldout/coherentnovelcontribution/substantialadvantagestillopen.


## Reduced BFS implemented and original-property verified; new LOCAL run LIVE

Previousgoalturnprogress: independentCloudnegative diagnosis. This turn registered
6case rounds0/1/2ablation forbothbranches. 3s/200kstates:0and1bothhitstatecap;
2roundsclose101476/74840stateswithindependentoriginalchecks. AuditPASS.
research/cloud-reduction-rounds-v1; no claim1roundcannotworkwithlargerbudget.

Added src/reduced_bfs.rs and optional CLI reduced-bfs. Max4 buffer/relevance rounds,
preparationmin(timeout/5,200ms), BFS90%remaining, capmin(maxstates,200k), reverse
positivewitnesslifting, nestedexistingreductionproofswithnewfinite-closure-v1 leaf.
Leafrecordsstatecount; Rust/Pythonverifiersre-exploreclosure andcheckcount. No explicit
invariantsetartifact. Existingdefault/methodsunchanged. Pythonbenchmarkfiniteclosure
factoredforlegacyandnewleaf. Runtimechecker requiredfornewproofschema; frozenoldLinux
runner lacksit and must beupdatedbefore any future reduced-bfsLinuxbenchmark.

13RustintegrationtestsPASS incl1176weightedconservative-net differentialcases,
macropositive, nestednegative bothverifiers, invalidboundrejection,budgetunknown;
25PythonreductiontestsPASS,Clippy+releasebuildPASS. Logsresearch/reduced-bfs-v1.
FulloriginalCloud311RC06 diagnostic5s+buffer: countportfoliooutertimeout;
reduced-bfsUNREACHABLEbothbranches, independentlytranslated/reconstructed/exhausted.
Solverwall0.654s/check14.669s(singleMacprobe). Source/binarysnapshot+originalauditPASS.
Allbuild/test/originaldiagnostic sessions terminal0.

NEW LOCAL FULL RUN LIVE exec66546, research/reduced-bfs-development-v1/run.log.
192propertiesx4=768rows: candidate(reduced-bfs)/native-counts/native-walk/native-frozen.
1spropertybudgetsharedbranches,sampled2GiB,separateboundedindependentchecks.
Candidateinternallycapped200kstates; othercontrolsunchanged2M. 8capabilitycasesPASS.
PlanSHAc89cf86d73a172fda3c91df1b130f69dc5a92039616fdb1f59a50657cd9e97eb.
Freeze results/solver-reduced-bfs-development-v1 includescurrentcheckerwithnewleaf.
Poll66546before otherlocalbuild/measurement/bulktransfer. Onterminal audit with
research/audit-reduced-bfs-development-v1.py then summarize-reduced-bfs-development-v1.py.
Scripts adapted but completeaudit not yetrun. Default unchanged; no noveltyclaim.

REMOTEpid1211679 exactidentitylastverifiedLIVE230/880 thisturn. Poll samejob with
research/poll-portfolio-counts-linux-v1.py; no remotebuild/measurements/transfers until
terminal. Remote frozen countportfolio run unaffectedbylocalchanges. CollectONLYwhen
bothmeasurementgatesclear; genericoriginal-inputauditor explicitpaths inREADME.
Goalactive: competitiveevidence,heldout/repeats,coherentnovelcontribution remain.


## Standalone reduced-BFS screen audited; combined portfolio tested and RUNNING

Previousgoalturnprogress: reducedBFSimplementation+originalCloudproof+fullscreenlaunch.
Thisturnlocal66546terminal0,768rows; auditPASS zero warnings/disagreements.
ReducedBFS90R60U42unknown=150/192; count/walk101R85U=186; frozen98R85U=183.
Candidate addsDoubleExponent003RC05/06/11 checkedpositives vsALLcontrols, loses39vs
count/walk(25negative). Diagnosticunion189/192 is not an implementedsolverresult.
Reportresearch/reduced-bfs-development-v1/report.md. PeakcandidateRSS237715456B,
1outerexpiration,0memorylimits. Keepallnegativeevidence. Localoldgateclear.

Added optionalCLIportfolio-reduced: existingwalk+countstages, thenreducedBFS
min(remaining/3,1s), acceptingpositiveorcheckednegative, unchangedfallbackafterwards.
Defaults andoldmethodsunchanged. Tests11PASS inclcombinednegativeproof+warmup+
restart andunderlying1176weightednetcomparisons; Clippy/releasebuildPASS.
research/portfolio-reduced-v1 contains fullsource/binaryfreeze,logs,report.
Matchedsamebuildoriginal5sdiagnosticsbothgapproperties: countandcombinedRefinepositive
(independentwitness); countCloudunknown, combinedCloudUNREACHABLEbothbranches,
independentlytranslatedandnestedproofchecked.4rowartifactauditPASS.
CountRefinetimingvaried1.103vscombined0.155 evenwithsharedstage: no stabletimingclaim.

NEW LOCAL FULL RUN LIVE exec45875, research/portfolio-reduced-development-v1/run.log.
PlanSHaf9bc9cae92da9b45ad20ebe5e3042a4ad3d264f9dcfd2d5a83be4bcf6ee2ffa4.
192x4=768rows,1spropertysharedbranches,sampled2GiB,separateindependentchecks;
candidateportfolio-reduced/native-counts/native-walk/native-frozen.8capabilitycasesPASS.
Frozenresults/solver-portfolio-reduced-development-v1. Pollsamehandle; no otherlocal
build/measurement/bulktransferuntilterminal. Then run audit-portfolio-reduced-development-v1.py
and summarize-portfolio-reduced-development-v1.py; completeaudit not yetrun.

REMOTEpid1211679 still exactidentityLIVE690/880 atlatestpoll. No remotechanges.
Pollresearch/poll-portfolio-counts-linux-v1.py; authoritative terminalrequired before
collection. Collectonlywhenbothmeasurementgatesclear. Newportfolio not inthisLinuxrun;
thatrunmeasures countportfolio alone. Newfiniteclosureproof requires updatedfrozen
Linuxcheckerforfuturecandidatecomparison. README has existing collection/auditcommands.
Goalactive: fullcohortcombinedoutcome, newLinuxcomparison, heldout/repeats, coherent
novelcontribution/substantialgeneraladvantage unestablished.


## BOTH comparisons finished and audited; no running jobs, all gates CLEAR

Previousgoalturnprogress: combinedportfoliointegration+fullscreenlaunch.
Thisturnlocal45875terminal0,all768rows. Combinedcandidate104R85U3unknown=189/192;
count/walk101R85U=186; frozen98R85U=183. GainsDoubleExponent003RC05/06/11 overcount/walk,
NO losses; +3TokenRingvsfrozen. AllauditPASS0warnings/disagreements. Report and
pairedcoverage/resourceevidence research/portfolio-reduced-development-v1.

REMOTEpid1211679 AUTHORITATIVELY TERMINAL0 at2026-09-28T14:41:32.230546UTC,livefalse,
880rows. Collected3873files/1822117bytes; archiveSHA
 afb1109483790f0b35bc0f76c87298593333393fcc0010a412977011171285c2.
Bothmeasurementgatesclear. DoNOTpoll/restart eithercompletedjob.

Linuxcountportfolio134/176(89R45U),frozenwalk133(88R45U),frozenexisting128(83R45U),
VerifyPN129(83R46U),SMPTMCC97(52R45U). Countvswalk1gainRefineRC11/0loss;
vsfrozen6gains0loss;vsVerifyPN6gains1lossCloud311RC06;vsSMPT37gains0loss.
41allmethodunresolved. AUDITPASS0issues/0warnings/0disagreements. Nativechecked,
externalsreported. One5sCPU8enforced2GiBrepeat; controlvariation1resultvsprior.
Newcombinedportfolio NOT in thisLinuxrun; do not mergeitslocalCloudresultintotable.

Auditmetadatafailure resolved TRANSPARENTLY: originalplan methods.native-counts
containsprose, whereas native_tools correctlypinsengineportfolio-walk-counts+binary.
Keptoriginalplanimmutable; analysis-plan.json normalizes ONLY that redundantfield.
analysis-plan-amendment.json links hashes+authority. Firstgenericfailure(prosefield)
andsecondgenericfailure(derivedplanhashvsoriginalexecutionidentity) preserved under
attempt-1/attempt-2 files. NEW research/audit-portfolio-counts-linux-v1.py checks exact
onefielddelta, originalexecution/capability/terminal hashes, then fullgenericaudit on
analysisview; PASS. Use this specializedauditor forreruns, notgenericalone.
Summary+report research/portfolio-counts-linux-v1. Fixfutureplans BEFOREfreeze:
methods[nativelabel] must equal native_tools[nativelabel].engine, descriptionselsewhere.

Prepared LOCALONLY results/runner-smpt-single-core-v3:24files, onlybenchmark.py
changedfromfrozenv2; addsfinite-closure-v1 andfactoredlegacyclosure. Preservev2's
signed-threshold/phase-pairhandlers (rootcurrentbenchmark.py lacks those). ArchiveSHA
2d0188faa1fe6475d2299525951fe46037fcb1d588a6bac6c647e64af4ef45f1.
15harness/identity/closuretestsPASS; actualfrozenboundedworkerchecks savedRefinepositive
andCloudnestednegativePASS. Evidence research/runner-smpt-single-core-v3.
Initialcopiedtestincludedobsoleteoldqualificationassertoutputdoesnotexist; failedlog
andsourcepreserved; removedunrelatedhistoricalplantest, all15runnertestspass.

NEXT: freeze/deploy/build combinedportfolioLinuxcandidate, with updatedfrozenv3runner,
matchedcount/walk/existing controls andVerifyPN/SMPTMCC. Buildscript prepared butNOT
executed/deployed: research/build-portfolio-reduced-linux-v1.py. UsesexplicitRust1.97.1,
testsreduced_bfs+count_cap, andsource/vendor/venvsymlink torealvenv(requiredbyCLItests).
Need prepare sourcepackage from results/solver-portfolio-reduced-development-v1,
pin allsource/binary/runtime identities, qualifynewclosureproof onLinuxpreflight,
thenfullcohort. OriginalSMPT dependenciesandstrongcontrols remainfrozen. Nojobactive.
Goalactive: generaladvantage,heldout/repeats,coherentnovelresearch stillunestablished.


## Combined portfolio Linux built, qualified, full1056rowcomparison RUNNING

Previousgoalturnprogress: bothscreensaudited, v3checkerprepared. This turn preserved
combinedsource fromresults/solver-portfolio-reduced-development-v1, deployedfresh
results/linux-solver-portfolio-reduced-v1 andbuiltwithRust1.97.1. Build78164terminal0;
6selectedtestspass incl1176weightedcomparisons,positive/nestednegativeCLIchecks,
countcapboundaries. PythonCLItestvenvlinkrecorded. Allbuildreceiptscollected.
LinuxbinarySHA777caa027eca5d5c846b39c49fc48ff8bf59d9675ffe50b49cbe93e3480a44b7.

Newplanmethods entriesmatch actualengine names; asserted beforefreeze andchecked
withregistered_native_tools againstfetchedcapabilityenvironment. No prosemetadata
amendment needed. Usesv3frozenrunner (closureextensiononly). Deployment1410runtime+
60preflightpinsverified.24EF/AGharnessrows59909terminal0,5SMPTcomponents48761terminal0.
Negativeharnessusescapacityproof, so separateCloudoriginalinputclosurecapability
26967terminal0 under5sCPU8enforced2GiBperf; bothfinite-closure-v1leaves checked through
frozenv3boundedoriginal-inputworker. Thisextracase is excludedfromfullcomparison.
Collected/auditedcapabilityarchiveSHA
 db7e14977afa2d109fe8e71108141b783f18266c66b0f01f0dba63a25e4fe3b1.
Maincapabilityaudit also checks closure receipt hash andnativeengines. No pendingtests.

NEW REMOTE JOB pid1393982,created1790607089.32,
boot17c1d989-ad9a-424e-9347-88bc5cb8e11b. Full1056rows=176propertiesx6methods,
5sCPU8enforced2GiBperf,separateindependentnativevalidation. Methods native-reduced,
native-counts,native-walk,native-frozen,VerifyPNdefault,SMPTMCCportable.
PlanSHA14ba740088129f3cd0b6d8f2e28c6dfb835ca03a29a409f0b51bb32b26b97978.
Folderresearch/portfolio-reduced-linux-v1; rawresults/linux-portfolio-reduced-v1.
Dispatchlocalexec22912terminal afterlaunch; remoteisdetached. Poll
research/poll-portfolio-reduced-linux-v1.py (exactidentity); doNOTrestart onpollfailure.
No remotebuild/measurements/deploy/bulktransferuntilterminal. Localgateclear.

Afterterminal usecollect-portfolio-reduced-linux-v1.py; genericoriginalinputauditor
explicitnewplan/results/output paths; summarize-portfolio-reduced-linux-v1.py.
READMEcontainscommands. AllolderrunsDONE; doNOTrestart1211679 oroldlocalruns.
No fullnewLinuxresultyet; defaultunchanged. Goalactive,publication/novelty/heldout/
substantialgeneraladvantage stillunestablished.


Follow-up: SMT dependency question and survivor sweep status
----------------------------------------------------------
Local session 8542 is terminal, exit 0. research/development-survivors-v1/terminal.json reports 18 rows. All three remaining properties were unknown at 1, 5 and 20 seconds in both combined and counts modes. These are raw observations; the sweep still needs an independent artifact audit and report. Script: research/probe-development-survivors-v1.py; log: research/development-survivors-v1-run.log. Local measurement gate is clear.
Remote exact job 1393982 was confirmed live at 137/1056 rows; do not restart, collect, deploy or run overlapping remote work.
User asks whether SMT is needed or an independent tool is possible. Current Rust portfolio needs no external SMT solver; Cargo includes embedded microlp and varisat. Fixed-word acceleration also has native arithmetic implementation in path_scheme.rs / scheme_search.rs. This establishes feasibility, not superiority or completeness of bounded search.


Survivor audits and execution-frontier diagnostic completed
----------------------------------------------------------
Previous goal turn was a verified wait (exact remote pid live). This turn made progress:
- research/audit-development-survivors-v1.py passes all18 property rows/30 branches. All18 properties unknown;24 branches unknown,6 independently checked negative RC07 branch1 answers.12 externally expired branches,24 wall-over-share branches,0 sampled memory excess. Report saved. No local job remains.
- Stage profiles: research/development-survivor-profiles-v1, all5 processes terminal0; audit/report/diagnostics saved. Session28052 DONE. Frozen combined executable,5s internal/7s external. Count stage on RC02 quickly gives one model then stops after68 execution edges; RC07 branch0 three models/138edges; TokenRing hits128 causal nodes with97 support cuts. Reduced BFS hits200k states on all5.
- Added examples/count_obstruction_diagnostic.rs (release build session20608 DONE). Frozen diagnostic binary/source/plan/logs in research/count-obstructions-v1. Source formatting occurred after build, documented. All5 diagnostic processes DONE.
- research/audit-count-obstructions-v1.py independently verifies integer models, greedy prefixes, and exhausts all count-bounded execution orders. DoubleExponent RC02 branch0/1 counts424/503, graphs69states68edges; RC07 branch0 counts253,70states69edges. No explored prefix satisfies target. Greedy prefixes end at28steps in actual deadlocks (no enabled original transitions).
- Strong actionable finding: all exits from those exhausted count-bounded graphs require t34 or t42 (RC02), only t34 (RC07 branch0); all have proposed count0. Thus necessary global count cuts x[t34]+x[t42]>=1 or x[t34]>=1, respectively. First-exit proof and general disjunction x[t]>=v[t]+1 described in report. Single deadlocked traces or interrupted closure do NOT authorize these cuts.
- Proposed next implementation: separate optional native count planner alternating integer models with full count-bounded closure, returning replayed target prefixes or learning execution-frontier cuts. Zero-bound frontier -> sparse sum>=1; general frontier -> disjunction, never incorrectly apply sum>=1 to positive bounds. Incomplete closure unknown. Keep frozen portfolios/defaults unchanged. Compare prior state-equation/increment-constraint work before novelty claims. Not implemented yet.
Remote1393982 confirmed LIVE at246/1056 during this turn; same identity, no restart/collection/deployment while live. Local gate now clear. New Linux comparison still incomplete. Goal remains active.


Execution-frontier count planner implemented; new local comparison running
-----------------------------------------------------------------------
Previous goal turn was progress (audited survivor graphs and derived sound first-exit constraints). This turn implemented/verified and measured a separate native solver.
- src/frontier_counts.rs, exported in lib.rs, optional CLI frontier-count-plan. Proposes integer models, explores full count-bounded graph, returns replayed target prefixes or necessary execution-frontier disjunction. Zero bounds -> sum>=1; singleton -> lower bound; general -> bounded integer selector variables. No cut after interrupted closure, no negative verdicts. MAX_MODELS128,MAX_CELLS16m,requested cumulative states. Candidate integer cap includes selector variables; no negative authority. Existing defaults/portfolios unchanged.
- Initial BFS variant: six tests passed (486 small weighted-net/count combinations checking all witnesses up to length6), Clippy and release build passed. v1 unit log contains preserved initial BigInt type compile error; v2 unit log passes.
- Five-branch/5sec paired pilot research/frontier-counts-v1:10rows audited, both new+frozen count planner5unknown,1expired candidate,0memoryexcess. report.md describes soundness, exact selector encoding, limitations and prior-art requirement. No novelty claim; Wimmel/Wolf already in research/related-work-audit.md.
- Completed full192x4 local screen research/frontier-counts-development-v1:all768rows audited,0warnings/disagreements. Candidate93R0U99unknown, frozen standalone count93R, combined104R85U, frozenexisting98R85U. Candidate gainTokenRing005RC08 (120models119cuts955states,checked6stepwitness); lossSharedMemory000020RC00 (BFSstorage cap33402states vs baseline18stepwitness). No main-portfolio gain; do not promote. Frozen binaries/source results/solver-frontier-counts-development-v1; raw results/frontier-counts-development-v1; report saved.
- Changed exploration order to DFS (same exhaustive-cut prerequisite), added independent18transition interleaving test, adjusted early-prefix test to avoid asserting shortest witness. Seven tests pass in frontier-counts-unit-v3.log; clippy-v2/build-v2 logs pass. Build session12236 terminal. Current root source/binary are DFS variant.
- Registered matched DFS/BFS ablation plus3controls: research/frontier-counts-development-v2,5modes,192properties,960rows,1sec shared per property,2mstates,sampled2GiB,30sec independent check outside timing. Modes candidateDFS,native-bfs(v1frozen),native-counts(frozenstandalone),native-combined(frozencombined),native-frozen(existing). PlanSHA a7b6278d25b57cededd87a9fc4bda399f5a55e75d608f50b2291fd77dc9ccaf3. Frozen artifacts results/solver-frontier-counts-development-v2; raw results/frontier-counts-development-v2. Ten smoke checks pass.
LIVE LOCAL session41242 runs research/run-frontier-counts-development-v2.py launch, log research/frontier-counts-development-v2-run.log. Poll exact session; do NOT launch duplicate. No local build/measurement/bulktransfer until terminal. After terminal run research/audit-frontier-counts-development-v2.py; write report with paired gains/losses including BFS ablation. Session59168(v1full),27820(pilot),34385(v2smoke) all terminal.
REMOTE exact pid1393982 was last confirmed LIVE at709/1056rows. Same boot/create identity and poll tool; no remote build/measurement/deploy/bulktransfer while live. Once BOTH relevant gates clear and remote terminal, collect/audit/summarize original-input Linux combined comparison as previously instructed.
Goal remains active: implemented native refinement is verified engineering, with no established net portfolio advantage, novelty, held-out evidence, or publication readiness.


Both full comparisons completed; no live work remains
---------------------------------------------------
Previous goal turn was progress (implemented/refined native frontier solver and launched matched ablation). This turn completed and audited that ablation and the Linux comparison, plus independently checked all logged frontier cuts.
- Local DFS/BFS screen session41242 DONE0. research/frontier-counts-development-v2 audit passes all960rows,0warnings/disagreements. DFS94R0U98unknown; BFS93R; frozen standalone counts93R; combined104R85U; frozenexisting98R85U. DFS gainsSharedMemory000020RC00 overBFS (172states,18stepcheckedwitness), retainsTokenRing005RC08 gain overcounts, no losses to either. No gains over either portfolio: do not promote. report.md saved.
- Added optional VASS_FRONTIER_PROFILE logging to root src/frontier_counts.rs; root/current binary now profiled-capable DFS, frozen v2 artifacts unchanged. Build49896 DONE. No algorithm change from profiling.
- Five survivor profiles research/frontier-sequences-v1 completed (session23065DONE),5sinternal/7sexternal. Frozenbinary/source/input/logpins. Independent Python checker research/check-frontier-sequence-v1.py reconstructs all368 logged frontiers/130940states exactly; five bounded60s checker processes pass (session60709DONE). audit.json/checks.jsonl/report.md saved. DoubleExponent cuts mostly general disjunctions; TokenRing128allzero cuts476states. All proofs limited to frontier correctness, no new property verdicts.
- Proposed further experiment, NOT implemented: expand permitted frontier counts before re-querying integer solver; complete enlarged closure can find witness or exclude larger count box. Arbitrary nonnegative bounds need not satisfy state equation. New cut need not imply old globally; do not drop old constraints assuming implication. Partial closure no cut. This proposal currently lower priority than repeated main comparison.
REMOTE pid1393982 DONE, authoritative terminal0 at2026-09-28T15:24:05.634939Z,1056rows. Do NOT restart/poll it again.
Collection session93606DONE:4809files2162687bytes,archiveSHA5a794950fd9c53ed16e96e0a1b73ee30e8ff645b2501b0e99d458123e5044cca. Generic audit30629DONE passed0issues. Summary/report saved research/portfolio-reduced-linux-v1.
MAIN LINUX VERIFIED RESULT (176 original properties/175distinct ordered-branch reps,5s,CPU8,2GiB): combined135=89R46U; counts134=89R45U; walk133=88R45U; frozen128=83R45U; VerifyPN129=83R46U; SMPT97=52R45U. Combined no solved-set losses to any. GainCloud311RC06 overcounts, plusRefine100101RC11 overwalk;7gains vsfrozen,6vsVerifyPN,38vsSMPT.41allunresolved. DuplicateDNAwalker09ringLR RC00/07 allunknown, so distinctrep solvedcounts unchanged. Nativeanswers independentlychecked; externalreported.
IMPORTANT SIX WARNINGS (not auditissues): threeSMPTtimeouts RERS5RC09,RERS5RC00,RERS9RC06 have interruptedperfexports/missinginstructions,cycles,taskclock. Partialraw retained,notimputed; rows retained. No answerdisagreements/invalidanswers. Singledevelopmentrepeat,no general/speed/novelty/publicationclaims.
NEXT MAIN ACTION: finalize/register repeated original-input comparison using research/repeated-comparison-protocol-v1.md (draft only):4frozenmethods combined,existing,VerifyPN,SMPT;5s/30s;3independentblocksperbudget,separatepredeclaredorderseeds;4224invocations. Frozenstrongcandidate/competitoridentitiesalreadyqualified. Need actualplan(s), runner/launchidentity/capability handling and balanced block order; don't relabel old capability as new without explicit audited derivation or fresh preflight. Keep all failedruns/partialperf; reserved-evaluation-v2families untouched. Could instead pursue justified frontier expansion research, but main repeatability/budget sensitivity is now missing evidence.
All local and remote measurement/build/transfer gates clear at turn end. Goal active,not complete.


Repeated five-/thirty-second Linux comparison registered, qualified and LIVE
------------------------------------------------------------------------
Previous goal turn was progress (bothfullrunsaudited, learnedfrontiers independentlychecked). This turn froze and launched the repeated matched experiment. No solver changes.
NEW LIVE REMOTE JOB pid1786482,created1790609624.42,boot17c1d989-ad9a-424e-9347-88bc5cb8e11b. Host jules@jules-b650-aorus-elite-ax-v2;root/home/jules/experiments/pvass-publication. Suite sequentially runs ALL SIX blocks; do NOT launch individual blocks or restart after poll failure. Latest exact poll confirmedlive,b1-5s14/704rows,allothers0.
Suitefolder research/repeated-comparison-linux-v1; masterSHA8ab24b5b7d3c7fdde01832cbcacd39908764da6ef7df55d10961a4cb9ac94d36. Plans in b1-5s,b2-30s,b3-30s,b4-5s,b5-5s,b6-30s. Each704rows=176x4;total4224. Orderseeds2026092807..2026092812inblockorder. Eachplanrepeat1. Methods native-reduced(maincombined),native-frozen(existing),verifypn-default,smpt-mcc-portable. Mainbinary,competitors,runnerunchanged. PRIMARYnative_binary changed to registered reduced binary (neededforregistration),matchinghash. CPU8/2GiB/perf/separatechecks. Reservedfamilies untouched.
Scripts: prepare-repeated-comparison-linux-v1.py (alreadyDONE,immutableplans),run-repeated-comparison-linux-v1.py (remotequalify/launch),manage-repeated-comparison-linux-v1.py (deploy/qualify/dispatch/poll). Syntax+all6commands/native registrations checkedbeforedeploy. Setupscriptbytes frozen ineachplan; doNOTeditthese withoutnewregistration.
Deployment20461DONE0,11files,allruntime/preflightpinsverified. Freshqualification98750DONE0 at5s+30s:32EF/AGharnessrows,10SMPTcomponentrows. Fourseed-onlyderivedcapabilities check exactalloweddiff(output,order_seed,suite_block,capability_preflight). Capability collection22910DONE:287files,archiveSHA8a1fb8a45993e62ec13c9d400c3b7be7d7f20751cc84babffe950be2ad125d39. check-repeated-capability-v1.py passes; qualificationSHAa5359c75394f7aa134a27c928a00b5cb8c194257f3d3ddda3904995b186f75e2.
POLL ONLY: vendor/venv/bin/python research/manage-repeated-comparison-linux-v1.py poll
No remote builds/measurements/deployments/bulktransfers while suite live, including gapsbetweenblocks. Localgateclear; independentlocalresearch is possible. Do notpoll/restart oldpid1393982 (DONEandcollected).
AFTER entire suite authoritative terminal and localidle: vendor/venv/bin/python research/collect-repeated-comparison-linux-v1.py (newcollector syntaxchecked,notyetexecuted). Collector preservespartialfailures and requiresnonliveexactjob+matchingterminal. --import-existing available ifdownloadalreadyexists. Then generic audit-general-development-v3-linux-v1.py separately perblockwith --plan research/repeated-comparison-linux-v1/BLOCK/plan.json --results results/linux-repeated-comparison-v1/BLOCK --output research/repeated-comparison-linux-v1/BLOCK/audit.json. Need future aggregation script implementing frozen suite.json analysis:pairedcoverage,perbudget3blocksolvedfrequency/timingmedianrange,PAR2,distinct175primary/all176secondary,nomissingcounterimputation. READMEcontainsdetails.
Nextindependentlocalalgorithmworkifuseful: bounded expansion of frontiercounts before newintegerqueries (proposal in frontier-sequences-v1/report.md). No claimedadvantage/newpublicationreadiness. Mainresearchgoal active and incomplete.


Frontier expansion tested; no coverage gain; repeated suite still LIVE
-----------------------------------------------------------------
Previous goal turn was progress (registered/qualified/launched six-block repeated comparison). This turn implemented and tested optional frontier-count-plan-expanded, completed its pilot and whole development ablation, and prepared repeated-run summary code.
- Root src/frontier_counts.rs now factors solve_with_expansion; original solve uses0rounds, solve_expanded uses3. Exhausted frontier bounds growmin(2*v+1,max_states), saturatingoverflow-safe; eachexpandedgraph startsinitial. Only completeclosure learns a cut; interruptedexpansion unknown. Integerconstraintsfrompreviousmodels retained. Profile events add expansion index and actualexplored bounds. Optional CLI wired inmain. No mainportfolio/default or frozenLinuxsolverchange.
- Ten frontier unit tests pass (including previous486arbitrarybound/netcombinations), Clippy/buildpass. Logs research/frontier-expansion-{unit,clippy,build}-v1.log; sessions25453/62522DONE.
- Pilot research/frontier-expansion-v1:10auditedrows,expanded+frozenDFS both5unknown,2expiredinvocations,0sampledmemoryexcess. ExpandedDoubleRC02branches~1.01m/1.03mstates,125/128models;RC07branch0~857kstates128models;TokenRing85,574states,1model2expansionsstorage cap. No survivorssolved. Pilot29955DONE. report.md saved.
- Full192x5screen research/frontier-expansion-development-v1:960rowsaudited,0warnings/disagreements. Expanded94R0U98unknown EXACT SAME solvedset asfrozenDFS94R; oldcount93R; combined104R85U; frozenexisting98R85U. No gains over eitherportfolio. DoNOTpromote expansion or justincreasedepth; further countrefinementneedsstrongerreason/priorartcomparison. Main methodsunchanged. PlanSHA426bc5d978ab74a821947fabf22367d52b7d110d7fadff293e0087202e716f91. Frozenresults/solver-frontier-expansion-development-v1;rawresults/frontier-expansion-development-v1;report.md saved. Smoke27749/full23958DONE. Localgateclear.
- Added research/summarize-repeated-comparison-linux-v1.py, notyetexecutedonrealrepeatresults (stillrunning). Requires suitecompletedall6blocks+collectedpins+all6audits. Checks row/audit/collectionhashagreement and cross-blockquery+duplicateverdictagreement. Computes175representativeprimary/176secondary solvedsets,pairedgains/losses,PAR2,perquery3blocksolvedfrequency/timingrange,validationcost,memory,validcountercoverage(noimputation),all3common-solvedmedianratios. Fourpuremetric tests pass research/test_repeated_summary_v1.py/log repeated-summary-unit-v1.log; finalscript syntaxcheckedafteraddingduplicate checks. Entirefutureaggregation stillneeds actualcompleteddataaudit; do notclaimtestedend-to-end.
REMOTE suitepid1786482 lastauthoritativepollLIVE,b1-5s269/704,others0. Samecreation/boot/suitehash asabove. Poll only manage-repeated-comparison-linux-v1.py poll. Allsixblocksqueued; no remote builds/measurements/deploy/bulktransferuntilwholejobterminal. No oldjobpoll/restarts. Local researchmaycontinue independently; no localjobsremain.
Goalactive: currentmain5scoverage135vs129VerifyPN/97SMPT/128frozen remainsoneauditeddevelopmentrun. Repeated5/30sresultsnotyetavailable; substantialgeneraladvantage,heldoutgeneralization,coherentnovelresearchcontribution allunproven. Optionalfrontiervariants areverifiedexperimentswithlimitedstandalonegain,notmaincontribution.


Repeated-summary integration checked; new Pro direction consultation LIVE
-----------------------------------------------------------------------
Previous substantive goal turn was progress (8 end-to-end synthetic summary tests); intervening SMT answer was explanatory only. This turn confirmed exact remote job LIVE and submitted a full-source algorithm consultation.
- research/test_repeated_summary_v1.py has 8 passing tests; research/repeated-summary-integration-v1.log confirms. Synthetic 6x704-row fixtures cover denominators, PAR2, solved frequencies, common-solved ratios, validation cost, missing counters and rejection of tampered rows/cross-block and duplicate disagreements. No real repeated results aggregated.
- New Pro conversation https://chatgpt.com/c/6aba8d9d-3b48-83ed-bfaf-936f54ae6962, verified6Pro visually before send, separate chat, full source attachment completed. research/pro-direction-review-v1 contains prompt.txt, development.zip (1781files,4250995bytes,SHAfd3ab9b15af454cc17183614657e031fc07e77a31930c6712cc611b074baa4b4),files-sha256.json,submitted.png,submission.json. Includes src/tests/examples/config/patchedvarisat/scripts/researchMarkdown+Python; excludes bulky datasets/binaries/logs. Asked independent reassessment, native-vs-SMT and ABMC tradeoffs, strongest falsifiable coherent contribution; latest failed frontiers and historical proposals provided. No answer yet.
- ACTIVE five-minute current-thread heartbeat review-vass-algorithm-direction created; saves answer.md, independently assesses into assessment.md, then stops itself. Prior pro-rust-petri-net-solver remains PAUSED for its completed older consultation. Browser1/tab2 marked deliverable; refresh binding when needed, never resubmit solely on observation failure.
- Remote exact pid1786482 confirmedLIVE at521/704 firstblock,remainingblocks0. Same six-block sequential job, poll only; no remote builds/deployments/measurements/bulktransfers until whole job terminal. No partial outcomes analyzed. Local measurement/build gate clear.
- User's native-tool question: actual Cargo embeds microlp and varisat; native portfolio has no external SMT requirement. No claim native constraint solving is faster than SMT.
Next: await Pro answer for direction-dependent solver changes; collect/audit/summarize all six benchmark blocks only after authoritative terminal. No solver changes this turn. Research goal remains active and incomplete.

Verified wait: exact remote pid1786482 confirmedLIVE at620/704 firstblock, otherfiveblocks0. Pro conversation6aba8d9d-3b48-83ed-bfaf-936f54ae6962 confirmedthinking via livebrowser (Working/Stop, reviewing survivor reports). No completed answer; no resubmission. Observation saved research/pro-direction-review-v1/observation.json. Previous turn was progress (full-source consultation submitted); this turn verified-wait. No new measurements, no solver edits, no outcomes analyzed; gates and next actions unchanged.


Readable repeated-comparison report implemented and tested
--------------------------------------------------------
Previous goal turn was verified-wait. This turn made progress on reporting while both jobs remain live.
- Exact remote pid1786482 confirmedLIVE at668/704 firstblock,remainingfiveblocks0; no collection/restart/remote interference.
- Pro conversation6aba8d9d-3b48-83ed-bfaf-936f54ae6962 confirmedthinking (Working/Stop, inspecting portfolio algorithms and arithmetic models). No completed answer. Browser1/tab2 markedhandoff; monitor remainsACTIVE.
- research/summarize-repeated-comparison-linux-v1.py now writes report.md only after its existing complete-six-block/hash/audit gates pass. Readable tables show allthree perbudget repeatcounts,175primary/176secondary,intersection/union,PAR2,perblockpairedgains/losses,common-all-three timingratios with selection caveat,all-row counterstatus counts, failureflags and everyauditwarning. Querylevelmemory/checkingcost/timingdetail remains in summary.json. No change to registered runners/plans, frozen algorithms or statistical metrics.
- Added meaningful synthetic report tests for variable coverage at5s vs30s,exactPAR2/denominators,pairedlosses,emptycommonset asunavailable and two missingcyclecounters retained. Ten tests pass research/repeated-summary-report-v2.log. v1log preserves initial failed assertion that abbreviated the auditor's actual missing-or-invalid-value label; test corrected to exactlabel. Removedtwo unused testimports. No real repeated-suite report generated or partial outcomes inspected.
Local gateclear. Next remains await Pro for direction-dependent algorithm work, and terminal whole-six-blocksuite before collect/audit/summarize. Goalactive; main novelty, heldout generalization and substantial demonstrated advantage remainunproven.

Verified wait: remote1786482 LIVE; b1-5s completed704rows exit0 at2026-09-28T15:57:47.788217Z; b2-30s live19rows; remainingfour0. Whole suite stilllive, so no collect/build/deploy/measurement/bulktransfer. Pro directionreview confirmedthinking via Working/Stop, no completeanswer. Previous goalturn progress(reporttests); current verifiedwait. No outcomeanalysis or solverchanges.

Source inventory completed independently while waiting: research/source-inventory-v1/{report.md,cloc.json,files-sha256.json,metadata.json}. cloc2.08: Rustsrc29686codeLOC/70files (includes source-tree/inlineunittests),Rustintegration11809/52,examples556/11; totalRust42051. Python scripts15869/125;Python tests514/3;shell382/8. Excludes vendor/research/builds/benchmarks. Not a production-only/minimalcore estimate. Cargo dependency/source inspection confirms embeddedmicrolp/varisat;optionalABMC QF_LIA encoder distinct from nativeportfolio;original-input frontendPython. Remote1786482 confirmedLIVE,b1complete704,b2live28,others0. Pro reviewconfirmedstillthinking, browser1/tab2handoff. Previousturnverifiedwait;thisturn inventoryevidenceprogress;no solver/runner changes or partialperformanceanalysis.

Latest verified wait: remote1786482LIVE, blockrows704/115/0/0/0/0; onlyb1terminalexit0. Pro directionreviewstillthinking withStop control, no completeanswer. Browser1/tab2handoff. Repeated goalturns sinceinventory havebeen verifiedwaits, no outages/restarts or analysis ofpartialoutcomes. observation.json refreshed. Same gates/nextactions; goalactive.

Heartbeat/goal continuation: remote1786482 confirmedLIVE with b1/b2both704rows exit0, b3live152, remaining0. b2finished2026-09-28T17:23:51.387234Z. No collection whilewholesuitelive. Pro existingconversation now shows HTML challengeerror plusRetry, no finalanswer and noStop. Normalreload ledto Justamoment challenge atchatgpt.com/. Thisis observationfailure, NOT proofreviewterminal; didnotpressRetry orresubmit. Saved sanitizedobservation.json. MonitorremainsACTIVE toobserve recovery; noanswer.md/assessment.md. Need restoreoriginalconversationonlyafterchallengeclears; donotbypasschallenge. Browser1/tab2handoff. Goalactive; benchmarkverifiedwait plusnewreviewobservationfailure.

Pro direction review COMPLETE saved and assessed: research/pro-direction-review-v1/answer.md full substantive DOM transcription withcitations (mathaccessibilitynotation),assessment.md independent source/report/mathchecks. UI46m6s; previouschallenge wasobservationfailure. Monitorreview-vass-algorithm-direction nowPAUSED aftersuccessfulsave/assessment. Recommends qualifyITS-Tools exactsymbolicclosure beforecustomrewrite; nofurtherfrontierexpansiontuning; seriousincrementalABMC remainssecondhypothesis. Confirmed sourcePythonrestartsZ3 eachbound, nativeFIFO schemecomparisonconfounds arithmeticandsearch, explicitclosurecheckerreexplores. Reviewer1000net/2697marking/3000targetprobes and69checks remainunreproduced; threeprobeartifactbuttons available butnotdownloaded. Exactmodelbounds andnewliterature remainunverified. Nextindependentwork: ITSdocumentation/sourcequalification andmechanicalsurvivorstructureaudit, noreservedfamilies orremoteinterference. Latestremotepoll1786482LIVE,b1/b2complete704each,b3live152,remaining0. Goalstillactive.

ITS qualification preparation continued under user “Do that” authorization.
research/its-qualification-v1/report.md and provenance.json record wrapper commit,
product build/hash and GreatSPN archive/hash. Product source correspondence unverified:
inspected main HEAD newer than binary202609112134. Neither package executed, no
native image pinned. Official strong config ITS+SMT/META/manyOrder; ITS-only separate.
scripts/its_adapter.py stages one EF/AG property, unchanged PNML, exact-ID conservative
result parser and polarity conversion. Three test methods pass adapter-tests-v1.log;
no ITS runtime/semantic/performance qualification claim. Next resolve exact runtime,
then known-answer Linux smoke only after full live suite terminal. Full future runner
and registration still needed, including staging/startup and process-tree limits.
Latest remote exact poll1786482LIVE:704/704/461/0/0/0. No remote interference.
All local calls terminal; no new solver changes. Goal remains active and incomplete.
