# Raw stress comparison

18 selected sources; 1 repetition(s); 10.0s input-inclusive outer deadline.

| Source availability | Count |
|---|---:|
| pending-validation | 12 |
| timeout | 6 |

| Method | Selected sources | Verified positive in every repetition | Unknown / incomplete repetitions | Not run: export/input unavailable |
|---|---:|---:|---:|---:|
| raw-bfs | 18 | 1 | 11 | 6 |
| raw-search | 18 | 1 | 11 | 6 |
| raw-potential | 18 | 4 | 8 | 6 |
| raw-z3 | 18 | 0 | 12 | 6 |

| Method | Invocation status | Count |
|---|---|---:|
| raw-bfs | export-unavailable | 6 |
| raw-bfs | memory-limit | 7 |
| raw-bfs | solver-timeout | 4 |
| raw-bfs | verified-positive | 1 |
| raw-potential | export-unavailable | 6 |
| raw-potential | memory-limit | 4 |
| raw-potential | solver-timeout | 4 |
| raw-potential | verified-positive | 4 |
| raw-search | export-unavailable | 6 |
| raw-search | solver-timeout | 11 |
| raw-search | verified-positive | 1 |
| raw-z3 | export-unavailable | 6 |
| raw-z3 | solver-timeout | 12 |

Export failures remain in the selected-source denominator and are not solver unknowns. Input/schema failures, solver limits and verifier limits have distinct statuses in runs.jsonl.
Only replayed positives with every original serial component refuted by Z3 are accepted. Z3 unknown, killed workers, and unsupported negative proofs are unknown.
The single outer deadline includes interpreter startup, streamed hash checks, JSON/schema validation, solver startup/parsing/search, and independent checking. The solver phase receives 80% of remaining time by default; the remainder is reserved for checking. All worker/solver memory is counted together by sampled process-tree RSS.
Frozen input preparation is outside timing. Export construction is recorded separately. This is sampled portable accounting, not cgroup isolation. raw-z3 is the direct quantified BMC script, not SMPT. Source expectations and bridge duplicates are not additional verified outcomes.
