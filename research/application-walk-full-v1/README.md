# Full ordinary-cohort walk comparison

Full cohort prepared only: **no build, deployment or benchmark is performed by registration**.
`template.json` deliberately has no candidate binary hash. Complete `plan.json`
can be registered only after the frozen Linux build and actual smoke evidence
are available locally. Nothing in the existing comparison is modified.

The authorized8-row Linux capability smoke completed and passed saved-evidence
audit. Walk solved4/4and batched3/4; five positives have Python witness checks and
two negatives have Python buffer-agglomeration checks. The TokenRing walk case
was positive while batched timed out. This is capability evidence, not a full
comparison or stable speed claim. See `smoke-verification.json`; the full cohort
has not been launched.

The matrix retains **656 slots,640 imports,16 collection failures** and five
configurations: **3280rows,3200 solver invocations**. It uses the exact existing
union manifest, both192/464-slot parent cohorts,629ordered-branch representatives
and630kind-preserving representatives. No difficulty filter or reserved inputs.

| Configuration | Binary | Engine | Buffer |
|---|---|---|---|
| native-walk | linux-solver-walk-sparse-v2 | portfolio-walk | enabled |
| native-batched | same new binary | portfolio-batched | enabled |
| native-frozen | linux-solver-repeated-search-v1 | portfolio-batched | enabled |
| verifypn-default | previous frozen VerifyPN | unrestricted default | tool default |
| smpt-full-portable | previous repaired SMPT environment | full portable | tool default |

The frozen native baseline is the prior comparison's strongest native
configuration,618/640checked answers. Selecting it from development evidence is
explicit. The same-binary pair isolates the portfolio walk addition; comparing
the new binary to the old baseline measures all intervening code changes.
All native feature flags other than buffer are off. Walk uses compiled seed0,
restart10000and trace limit100000, verified from the frozen source archive.
No seed search, selected-seed wrapper or changed shared harness is needed.

Limits match the previous comparison: CPU8 affinity, aggregate cgroup2GiB,
perf user-space counters,5s strict outer deadline,2M state/step parameter,
one repetition, and60s/2GiB/64MiB/200M DAG-work independent native checking
outside solver timing. Retain checker failures as unresolved. External verdicts
remain tool-reported. The new seed and resulting rotated method order are frozen.
Affinity is not isolation; instruction counts do not remove timeout censorship.

## Registration and launch gate

Retrieve (do not rebuild in place) these candidate artifacts under
`results/linux-solver-walk-sparse-v2`: `vass-reach`, `source.tar.gz`,
`source-files-sha256.json`, `provenance.json`, `tests.log`, `build.log`, and
`packaging-provenance.json`. The identical source archive was copied locally
from `results/solver-walk-sparse-v2/source.tar.gz`; no new network transfer was
needed for that file.
The provenance schema follows the existing Linux freezer and must match all
binary/source/test/build hashes. The helper verifies every archive member.
Supply an actual bounded original-input smoke report containing
`{"status":"passed","binary_sha256":"ACTUAL_CANDIDATE_HASH"}` plus its
real evidence. Include checked positive replay and a negative certificate,
buffer lifting, and confirmation that both candidate engine names are accepted.
The two fields are an attestation gate, not an independent rerun of those checks.

```sh
vendor/venv/bin/python research/application-walk-full-v1/register.py \
  --smoke-evidence research/application-walk-full-v1/smoke-verification.json
vendor/venv/bin/python research/run-application-walk-full-v1.py
```

Registration refuses an existing plan or any mismatch in the previous frozen
22-file runner closure. If the runtime has changed, stop and explicitly freeze
and review a new closure; do not silently overwrite the registered scripts.
The helper preserves original inputs/tools/repair identities and adds the new
candidate, registration files, smoke report and audit/analyzer identities.
Its inherited identity set also includes previous source and smoke artifacts;
these must remain available at preflight. Audit/analyzer snapshots are evidence,
not timed solver components.

Deployment is intentionally not implemented. After all measuring/build sessions
are terminal, copy only the new files and any missing registered evidence;
verify member paths and hashes, refuse divergent overwrites, and retain old
artifacts. The previous `deploy-application-portfolio-comparison-v1.py` shows
safe archive-member and identity checks, but its hardcoded archive hash/member
count must not be reused for this package. The new candidate directory is
separate. Complete deployment and all capability checks before measurement.

Launch explicitly on Linux, recording the output log:

```sh
vendor/venv/bin/python research/run-application-walk-full-v1.py \
  --launch --terminal-predecessor CONFIRMED_COMPLETED_SESSION_ID
```

The launcher checks workload/output absence, every registered file and the
existing1136-file MiniZinc repair preflight. The predecessor argument records
operator confirmation; it cannot independently inspect a session. Build,
transfer and engineering work must remain absent from the measuring host.

After confirmed terminal completion and complete retrieval, use:

```sh
vendor/venv/bin/python research/audit-linux-application-expansion-v2.py \
  --plan research/application-walk-full-v1/plan.json \
  --results results/linux-application-walk-full-v1 \
  --output research/application-walk-full-v1/verification.json
```

Report all native gains/losses against both baselines, every family and parent
cohort, imported and failed slots, representatives, contradictions and missing
counters. Keep strict accepted totals distinct from reported totals. Unknown
cannot establish intrinsic difficulty. This is a previously used development
corpus and a single seeded repetition, not held-out or stable speed evidence.

## Runtime estimate

The previous full run's saved rows sum to3039s solver wall time plus532s bounded
validation, about60minutes before orchestration overhead. Budget **roughly1–2h**
for this run if behavior stays similar; this is an estimate, not a promise.
If every invocation hits5s, solver time alone is16000s (4h27m). All1920native
checks hitting60s would add32h in the extreme, so there is no1–2h hard cap.
Collection-failure slots produce80nonexecuted rows. Long checks, witness output,
process shutdown and shared-host contention can extend elapsed time. Do not
drop expensive rows or relax limits mid-run to fit the estimate.
