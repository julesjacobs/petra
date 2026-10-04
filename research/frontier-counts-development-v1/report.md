# Complete development comparison: frontier-count refinement

All 768 rows pass artifact audit, with no answer disagreements or validation
warnings. Every accepted definitive answer has a bounded independent checker
receipt. This is one local development repeat, not held-out or stable timing evidence.

| Method | Reachable | Unreachable | Unknown |
|---|---:|---:|---:|
| Frontier count planner, breadth-first execution | 93 | 0 | 99 |
| Frozen state-budget count planner | 93 | 0 | 99 |
| Frozen combined portfolio | 104 | 85 | 3 |
| Frozen existing solver | 98 | 85 | 9 |

The candidate gains TokenRing-PT-005 RC08 and loses SharedMemory-PT-000020 RC00
against the standalone count planner. It adds no positive over either portfolio.
Consequently this experiment does not establish a coverage advantage, and it is
not being added to the main portfolio.

TokenRing's gain uses 120 integer models, 119 frontier cuts, 955 explored states,
and a checked six-step witness. The old count planner reaches its 128-attempt
support-refinement limit without a witness. These are single-run diagnostics.

The SharedMemory loss has a direct cause: the candidate's breadth-first execution
graph reaches its storage bound after 33,402 states without finding a witness.
The baseline realizes an 18-step witness in 18 execution steps. Enumerating many
interleavings before reaching a full execution is avoidable for witness search.
The next registered version changes execution order to depth-first while retaining
complete closure as the prerequisite for learning any frontier constraint. The
v1 executable and all v1 results remain frozen.

Plan SHA256: 3b162ff210ddedb12691e0f3fdcdae70046b3b4076ac767183bbfa4a92acdc88.
Raw rows: results/frontier-counts-development-v1/runs.jsonl.
Frozen source and executables: results/solver-frontier-counts-development-v1.
Audit: audit.json, produced by ../audit-frontier-counts-development-v1.py.
