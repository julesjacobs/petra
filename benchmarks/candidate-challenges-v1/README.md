# Candidate development challenges

104 queries unresolved by the recorded Rust candidate at five seconds, selected
from complete, audited single-core Linux comparisons with a 2 GiB limit.

| Source | Selected | Competitor solved | Joint unknown | Other Rust version solved | Parent denominator |
|---|---:|---:|---:|---:|---:|
| MCC applications | 50 | 34 | 16 | 0 | 368 |
| Boolean consistency | 10 | 0 | 10 | 0 | 34 |
| FastForward | 44 | 0 | 43 | 1 | 218 |

This retains all 69 queries in `hard-development-v2` and adds 35 cases that expose
candidate weaknesses. The MCC track now spans AutoFlight, CANConstruction,
CloudOpsManagement, DLCflexbar and JoinFreeModules. Every native definitive
answer in the source comparisons passed independent checking. Competitor
answers are tool-reported. No selected row has a reported setup/capability error.
Timeout diagnostics remain in the hashed source runs.

These are existing, outcome-selected development inputs. They are not 104 new
independent benchmarks, and five-second failures do not establish long-budget
hardness. Candidate versions differ across tracks. Use the full 620-query parent
denominators for headline comparisons, and report tracks and families separately.
No exact canonical-branch hash duplicate groups were found; this does not
establish semantic distinctness.

`manifest.json` works with `scripts/benchmark_smpt_classic.py --rust-original`.
Paths reference sibling frozen corpora. Original PNML/XML inputs, query hashes,
source comparison hashes, candidate identities and selection categories are
recorded. Rebuild into a fresh directory using
`scripts/build_candidate_challenges.py --output PATH`. Construction checks full
run matrices, disagreements, native proof checks, input hashes and reserved
family exclusion.

Keep the eight families in `benchmarks/reserved-evaluation-v2.json` untouched
until the candidate and competitor configurations are frozen for final
evaluation. That selection contains 256 property slots across 16 models; it
has not yet been collected or measured, and its hardness is unknown.
