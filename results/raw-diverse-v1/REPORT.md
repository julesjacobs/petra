# Raw stress comparison

12 selected sources; 1 repetition(s); 10.0s input-inclusive outer deadline.

| Source availability | Count |
|---|---:|
| frontend-error | 10 |
| memory-limit | 2 |

| Method | Selected sources | Verified positive in every repetition | Verified negative in every repetition | Unknown / incomplete repetitions | Not run: export/input unavailable |
|---|---:|---:|---:|---:|---:|
| raw-portfolio | 12 | 0 | 0 | 0 | 12 |

| Method | Invocation status | Count |
|---|---|---:|
| raw-portfolio | export-unavailable | 12 |

Export failures remain in the selected-source denominator and are not solver unknowns. Input/schema failures, solver limits and verifier limits have distinct statuses in runs.jsonl.
Positives require original-net replay and every original serial component refuted by Z3. Negatives require an independently checked raw-component-invariant-v1 proof on the original query. Z3 unknown, checker limits, killed workers, and unsupported negative proofs are unknown.
The single outer deadline includes interpreter startup, streamed hash checks, JSON/schema validation, solver startup/parsing/search, and independent checking. The solver phase receives 80% of remaining time by default; the remainder is reserved for checking. All worker/solver memory is counted together by sampled process-tree RSS.
Frozen input preparation is outside timing. Export construction is recorded separately. This is sampled portable accounting, not cgroup isolation. raw-z3 is the direct quantified BMC script, not SMPT. Source expectations and bridge duplicates are not additional verified outcomes.
