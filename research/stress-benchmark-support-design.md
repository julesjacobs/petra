# Stress corpus benchmark support: source audit and proposed changes

No shared harness edits or tests were made for this audit.

## What already works

`benchmark_smpt_classic.py` already guards both startup file checks and solver dispatch with `query['status'] == 'imported'`. Thus the collector's failed slots lacking PNML/XML/net fields do **not** currently cause a KeyError: each becomes an `unsupported` row for every method and repetition. `query.get('kind')` safely records unknown polarity; unsupported gives `property_truth=None`. Full property ordering and the matrix denominator are preserved.

`analyze_instruction_counts.py` accepts unsupported rows and absent polarity/counters; they remain in coverage denominators and cannot enter instruction comparisons. However, these rows currently look like generic unsupported cases with missing counters. Explicit collection-failure attribution is needed so readers do not mistake unattempted solver runs for actual resource failures or missing perf instrumentation.

## Actual hazards

1. Startup `checked()` uses `read_bytes()` for every original net, canonical branch and translated net. A shared multi-gigabyte PNML is re-read for each of its sixteen properties. Hashing is outside solver timing but unbounded in parent memory.
2. `native_original()` parses and retains **every canonical branch** in a `problems` list, parses frontend branches again for equality, then verifies proofs in the parent without a resource deadline. This can kill the entire benchmark after a solver returned quickly. A one-query checker failure must not lose subsequent rows.
3. `native()` similarly parses canonical JSON before its timed solver invocation and verifies answers in the parent. This path is unsuitable for unbounded stress inputs without a bounded child.
4. Both external adapters read complete logs into the parent; VerifyPN additionally parses XML to find the requested index before timing. These should have explicit bounded treatment even though logs/property XML are normally smaller than nets.
5. The current all-method `status=imported` gate prevents SMPT and VerifyPN from attempting an original input whenever **our canonical importer** failed. Reporting this as competitive solver coverage would penalize competitors for our frontend limitation.
6. The collector records XML IDs before net import, but it writes per-property XML and records EF/AG polarity only after PNML parsing. A failed large-net import consequently lacks the certified original-property metadata needed for a fair original-input competitor run.

## Recommended staged implementation

### A. Safe complete-matrix support first

Keep all planned slots. Add a small metadata-only manifest validator that verifies unique names, exactly sixteen slots/model, expected total, suite, observed flag and status consistency. Validate path/hash/branch metadata **only for the capabilities that a row advertises**. Unknown slots need no actual ID, polarity or file paths. Do not repair malformed imported rows into unsupported silently: record an explicit input-validation failure, preserve the row, and abort definitive acceptance for that input.

Emitted rows should carry `collection_status`, `collection_observed`, `property_slot`, `input_available`, `execution_attempted` and a structured `failure_stage`. Copy the actual `property_id` only when observed. A failed-import placeholder yields `verdict=unsupported`, `execution_attempted=false`, `failure_stage=collection`, `resources=null`, `property_truth=null`; never invent elapsed time, instructions, exit codes or actual IDs. Report planned/observed/original-available/canonical-imported/executed/verified counts separately.

Replace preflight whole-file loads with streaming SHA256 in fixed-size chunks. Deduplicate `(resolved_path, expected_digest)` and recheck file identity/size/mtime before use; reject changes instead of trusting stale cached hashes. Run even this hashing stage in a bounded worker, so corrupt filesystem behavior or huge input volume cannot indefinitely block the driver. Hash mismatch is input error; hash-validation timeout is a validation resource failure. Neither can prove a verdict. Preserve limits and outcomes in environment/results.

### B. Bounded validation outside the timed solver interval

Move original-frontend metadata, canonical equivalence, witness and proof checks into a separate worker. Proposed explicit defaults: 30s wall, 2GiB RSS/address-space cap, and capped JSON response/log size. Use a separate runner invocation after the timed solver has fully stopped and before the next solver starts. Record verifier wall/CPU/RSS separately; do not add verifier instructions to solver instructions. No simultaneous verifier and solver processes.

The parent passes paths plus small query metadata and consumes only a bounded verdict summary. The worker loads at most one canonical branch and its frontend counterpart at a time, checks equality, verifies that branch's outcome, then frees both before proceeding. Unknown/unattempted branches need translation equality if retaining the existing all-branches validation contract, but they do not need proof parsing. Reject unexpected branch indices/counts/IDs/polarities. Every definitive outcome still requires the independent checker. Checker timeout/OOM produces final `unknown` with the original proposed verdict preserved in `unchecked_verdict`; malformed or rejected proof produces `error`. A full solver matrix still gets written.

The pretranslated native path should likewise move canonical loading/checking into bounded workers. For the upcoming fair stress comparison, require `--native-original`; that avoids extending both native paths before the primary track is safe.

Stream external FORMULA-line scanning with a cumulative byte cap, retaining the full log on disk only within a separate output quota. Avoid `read_text()` of arbitrary solver logs. VerifyPN should use the collector-certified single-property XML index1, validated by a bounded metadata worker, rather than parsing arbitrary XML in the parent. Do not assume index1 from a filename alone.

### C. Separate original-input availability from canonical import success

This is necessary before claiming comparative coverage on the harder set. In the collector, immediately after bounded XML parsing, write and hash each single-property original XML, extract actual ID and EF/AG outer polarity, and record original PNML/hash. Do this **before** PNML-to-canonical import. Publish only fully written and hashed paths via progress metadata so an interrupted worker never advertises partial files.

Each planned slot then has independent capability fields:

- `original_available=true`: actual unique ID, validated EF/AG outer polarity, complete PNML and single-property XML paths/hashes.
- `canonical_available=true`: all successfully imported canonical branches and translated net/property paths/hashes.

Original SMPT/VerifyPN runs require only original availability. Native original frontend should also attempt these inputs within the same solver deadline even when canonical import failed. A native answer without canonical validation cannot yet be accepted: either rederive and check its translation in a bounded independent original-input checker, or retain it as `unknown/unchecked` with explicit reason. This limitation must appear in the comparison. An interim run that requires canonical availability for every method is an **imported-subset backend comparison**, with all omitted planned slots counted separately; it cannot claim best-tool original-input superiority.

Missing downloads, unobserved property IDs and unknown polarity remain unattempted for every tool. No synthetic RC slot index becomes an actual external property ID.

## Tests before collecting/benchmarking

- A sixteen-slot wholly failed model creates exactly sixteen × methods × repetitions rows without reading any absent files or launching a solver.
- Mixed observed/unobserved slots keep actual IDs only where known and never infer polarity.
- Imported-but-missing/changed artifacts produce explicit validation failures and no accepted solver answer.
- Original-available/canonical-unavailable cases execute external original-input tools, while native definitive acceptance requires a successful independent translation/proof check.
- Streaming hash reads bounded chunks, hashes a shared PNML once, and detects a subsequent file identity change.
- A checker timeout/OOM leaves the complete matrix intact and downgrades only the relevant answer; malformed certificates fail explicitly.
- Checker responses and solver logs exceeding their size quota cannot exhaust the parent.
- Check two large branches sequentially rather than retaining both; inspect child resource accounting.
- Legacy imported corpora retain their current results and original-input timing scope.

The existing frozen remote baseline should remain unchanged. These revisions belong in a new source snapshot/configuration and are required before timing the stress corpus. First collect under the existing bounded collector to establish how much original input/canonical import succeeds, then preserve that attempt when improving metadata handling or the frontend.

## Immediate scope after collector launch

Collection is now live (session15635), so implementation/testing must wait for coordination. The smallest robust next revision is A+B: keep the existing nonimported-query gate, add explicit frontend-failure rows/counts, stream/deduplicate hashes, and move `native_original` post-run validation into one bounded child with sequential branch processing and a small response. Preserve the current validation semantics and record checker limits separately. This makes the current imported-subset experiment resource-safe without pretending canonical-import failures were attempted by competing tools. Original-availability separation (C) remains a subsequent fairness improvement if the collection exposes material frontend loss.
