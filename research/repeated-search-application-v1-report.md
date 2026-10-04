# Repeated search: application regression audit

**The complete 384-row comparison passes its evidence audit: batched solves 192/192 properties, control 190/192, with two gains, no losses and no definitive disagreements.** Both labels use the same frozen binary and enable buffer agglomeration. The only command difference is `portfolio-focused` versus `portfolio-batched`.

| Population / outcome | Control | Batched |
|---|---:|---:|
| All 192 properties solved | 190 | 192 |
| All 187 exact ordered branch representatives solved | 185 | 187 |
| Reachable queries | 130 | 132 |
| Unreachable queries | 60 | 60 |
| Unknown queries | 2 | 0 |

Five duplicate pairs have consistent verdicts. Representatives are the lexicographically first query for each exact ordered branch SHA256 tuple; no semantic or isomorphism deduplication is claimed. The reachability verdict concerns the canonical target, with AG property truth inverted accordingly.

## Gains and mechanism evidence

| Query | Control | Batched | Accepted branch engine |
|---|---|---|---|
| `CircadianClock-PT-100000__RC12` | Unknown, outer timeout at 5.022 s | Reachable, 0.137 s | `relaxed-batched` |
| `NoC3x3-PT-8B__RC12` | Unknown, outer timeout at 5.015 s | Reachable, 0.183 s | `causal-state-equation` |

Both gains have saved successful `python-witness` checks against original inputs. CircadianClock branch 0 records 62 search states and an expanded 400,003-transition witness; its longest identical-transition run is 100,000. NoC branch 0 records eight states and a 244-transition witness with no adjacent repeated transition. Thus CircadianClock provides direct engine-level evidence for repeated search; the NoC result does not establish that repeated successors caused its gain. Profiling was off.

CircadianClock and NoC each improve from 31/32 to 32/32. BART, IOTPpurchase, RobotManipulation and SmallOperatingSystem each remain 32/32. No query remains unresolved by batched in this cohort.

Control's two timed-out processes exit 0; the strict runner correctly retains unknown because wall time exceeds five seconds. Neither has saved validation. CircadianClock's raw timeout output contains three negative branches, but they are not counted as independently checked evidence. There are no nonzero exits, recorded memory-limit events, collection/capability failures or saved validation failures. Sampled RSS does not rule out transient peaks between samples.

## Saved certificate evidence

All **382 definitive rows** have successful saved validation requests/responses reconciled with raw answers and result rows. This audit checks identities and saved evidence; it does not rerun any solver, witness or proof checker.

| Checked branch evidence | Control | Batched |
|---|---:|---:|
| Positive / `python-witness` | 130 | 132 |
| Negative outer `sparse-farkas-v1` | 53 | 53 |
| Negative outer `causal-state-equation-v1` | 26 | 25 |
| Negative outer `buffer-agglomeration-v1` | 25 | 25 |
| Total checked negative branches | 104 | 103 |

Each label's 25 buffer certificates contain 12 direct causal-state-equation proofs and 13 relevance wrappers containing causal-state-equation proofs. The corresponding saved labels are `python-sparse-farkas`, `python-causal-state-equation` and `python-buffer-agglomeration`. Branch totals differ from solved-property totals because disjunctive properties may stop after a positive branch.

## Reproducibility and scope

The auditor verifies the full matrix, seeded property shuffle and rotated method order; exact commands and original-input metadata; property polarity; solver and checker limits; and all 892 unique input files (174,726,804 bytes).

Frozen identities verified: binary, source archive, exact archive membership and hashes for all 170 source files, all 52 patched varisat files, and 13 review artifacts. Cargo's patch points to the archived vendor directory. Historical build/test logs are hash-checked, not rerun.

All 1,011 registered file identities pass through measured snapshots or current paths. Nineteen measured runner snapshots match environment hashes; 18 also match plan registration. `requirements.txt` is environment-pinned but was not plan-pinned. The other 96 registered scripts match their current paths and are not claimed to be measured snapshots. No current drift was observed in the snapshotted runners at audit time.

Each solver has five seconds, two million states and sampled 2,048 MiB process-tree RSS monitoring. Separate validation has 60 seconds, sampled 2,048 MiB, a 64 MiB response limit and 200 million DAG-check work units. Checking is excluded from solver timing. The launcher disables both profiling environment variables; geometric scheduling and other optional reduction flags are off.

Reproduce with `python3 research/audit-repeated-search-application-v1.py`. [Verification JSON](repeated-search-application-v1-verification.json) retains raw-answer hashes, saved sidecar hashes, every unknown, branch-proof counts, duplicates, changes and source hashes. [Audit log](repeated-search-application-v1-audit.log) contains the summary.

This is one local development regression after an outcome-selected repeated-firing diagnostic. It supports coverage on this cohort, not held-out performance, competition, novelty or default promotion. The common-solved median wall ratio is approximately 0.990 over 190 shared solved properties; one repeat does not establish a stable speed advantage.
