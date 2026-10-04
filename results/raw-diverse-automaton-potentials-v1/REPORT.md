# Raw stress comparison

12 selected sources; 2 repetition(s); 5.0s input-inclusive outer deadline.

| Source availability | Count |
|---|---:|
| pending-validation | 12 |

| Method | Selected sources | Verified positive in every repetition | Verified negative in every repetition | Unknown / incomplete repetitions | Not run: export/input unavailable |
|---|---:|---:|---:|---:|---:|
| raw-search | 12 | 5 | 0 | 7 | 0 |
| raw-potential | 12 | 6 | 0 | 6 | 0 |

| Method | Invocation status | Count |
|---|---|---:|
| raw-potential | solver-timeout | 11 |
| raw-potential | solver-unknown | 1 |
| raw-potential | verified-positive | 12 |
| raw-search | solver-timeout | 12 |
| raw-search | solver-unknown | 2 |
| raw-search | verified-positive | 10 |

Export failures remain in the selected-source denominator and are not solver unknowns. Input/schema failures, solver limits and verifier limits have distinct statuses in runs.jsonl.
Positives require original-net replay and serial nonmembership independently checked by Z3: component equations for v1, connected integral automaton flow for v2. Negatives require an independently checked raw-component-invariant-v1 proof on a v1 query. Z3 unknown, checker limits, killed workers, and unsupported negative proofs are unknown.
The single outer deadline includes interpreter startup, streamed hash checks, JSON/schema validation, solver startup/parsing/search, and independent checking. The solver phase receives 80% of remaining time by default; the remainder is reserved for checking. All worker/solver memory is counted together by sampled process-tree RSS.
Frozen input preparation is outside timing. Export construction is recorded separately. This is sampled portable accounting, not cgroup isolation. raw-z3 is the direct quantified BMC script, not SMPT. Source expectations and bridge duplicates are not additional verified outcomes.
