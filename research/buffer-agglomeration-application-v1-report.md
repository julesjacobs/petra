# Buffer agglomeration: application regression audit

The complete local comparison solves **191/192 with buffer agglomeration versus 189/192 for control**, gaining two queries and losing none. Both labels use the same frozen binary; the only command difference is `--buffer-agglomeration`. There are no definitive disagreements, including across duplicate queries.

| Population | Control | Buffer |
|---|---:|---:|
| All 192 properties | 189 | 191 |
| 187 exact ordered branch representatives | 184 | 186 |
| Reachable property queries | 129 | 131 |
| Unreachable property queries | 60 | 60 |
| Unknown property queries | 3 | 1 |

The reachability verdict is for the canonical target; an AG property inverts counterexample reachability. Representatives are the lexicographically first query for each exact ordered branch SHA256 tuple. All five duplicate pairs have consistent outcomes; this is not semantic or isomorphism deduplication.

| Gained query | Control | Buffer | Saved independent check |
|---|---|---|---|
| `NoC3x3-PT-8B__RC06` | Unknown, 3.363 s | Reachable, 0.168 s | `python-witness` |
| `NoC3x3-PT-8B__RC12` | Outer timeout, 5.030 s | Reachable, 0.201 s | `python-witness` |

Both gained answers use the causal-state-equation engine on branch 0. Positive engine labels alone do not prove which reductions applied. Profiling was registered off. NoC coverage rises from 30/32 to 32/32. CircadianClock remains 31/32; BART, IOTPpurchase, RobotManipulation and SmallOperatingSystem each remain 32/32.

**The remaining shared unknown is `CircadianClock-PT-100000__RC12`.** Both processes exit 0 but exceed the strict five-second outer deadline (5.038 s control, 5.034 s buffer). Neither has saved validation. The buffer raw output contains negative answers for branches 2, 6 and 10, but those late raw answers are not independently checked evidence. NoC RC06 control returns within budget with two unresolved branches and one saved checked sparse-Farkas refutation; its aggregate remains unknown.

All three outer timeouts are retained. There are no nonzero exits, recorded memory-limit events, collection failures, capability failures or saved checker failures. Memory monitoring samples macOS process-tree RSS; it is not a hard cap and does not exclude transient spikes.

## Saved certificate evidence

The audit reconciles 381 saved validation requests/responses with raw answers and result rows. All 380 definitive rows have saved successful checks; the additional validated unknown is NoC RC06 control. No solver or proof checker was rerun during this audit.

| Negative outer certificate / saved check | Control branches | Buffer branches |
|---|---:|---:|
| `causal-state-equation-v1` / `python-causal-state-equation` | 41 | 26 |
| `sparse-farkas-v1` / `python-sparse-farkas` | 54 | 53 |
| `relevance-v1` / `python-relevance` | 10 | 0 |
| `buffer-agglomeration-v1` / `python-buffer-agglomeration` | 0 | 25 |
| Total checked negative branches | 105 | 104 |
| Positive branches / `python-witness` | 129 | 131 |

Control's negative total includes the one branch inside the unknown NoC query. Its 10 relevance wrappers contain causal-state-equation proofs. Buffer's 25 wrappers contain 12 direct causal-state-equation proofs and 13 relevance wrappers around causal-state-equation proofs. These are branch counts, not solved-property counts.

## Identity and budget checks

The reproducible auditor verifies the complete 384-row matrix and randomized order; all original-input commands, input identities and EF/AG polarity; solver and validation budgets; raw answers and saved validation records; and all 892 unique input files (174,726,804 bytes).

It verifies all 1,009 plan-pinned file identities through frozen snapshots or current paths, the frozen binary and source archive, exact archive membership and hashes for all 160 source files, all 52 patched `vendor/varisat` files, and 16 frozen review artifacts. The source archive's Cargo patch points to the included varisat directory. Recorded build/test logs are identity-checked evidence, not newly executed tests.

All 19 measured runner snapshots match environment hashes. Eighteen are also plan-pinned; `requirements.txt` was not plan-pinned. The other 94 registered scripts are checked at their current paths and are **not** claimed to be measured snapshots. The current `scripts/benchmark_smpt_classic.py` differs from its registered hash after subsequent development; its measured snapshot matches. The frozen source archive, binary and runner snapshots are authoritative for this comparison.

Each process has five seconds, two million states and 2,048 MiB sampled memory monitoring. Independent validation has a separate 60-second budget, 2,048 MiB memory monitoring, a 64 MiB response limit and 200 million DAG-check work units. Validation time is excluded from solver timing. The launcher disables both profiling environment variables.

Reproduce with `python3 research/audit-buffer-agglomeration-application-v1.py`. Detailed evidence is in [the verification JSON](buffer-agglomeration-application-v1-verification.json); stdout is saved in [the audit log](buffer-agglomeration-application-v1-audit.log).

This is one local development regression after an outcome-selected NoC diagnostic. It is not held-out evaluation, competitor evidence or evidence to promote the flag by default. The common-solved median wall ratio is approximately 0.996, conditional on 189 shared solved properties; one repeat cannot establish a stable speed advantage.
