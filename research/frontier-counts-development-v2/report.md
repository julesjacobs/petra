# Complete development ablation: depth-first execution

All 960 rows pass artifact audit, with no disagreements or validation warnings.
Every accepted definitive answer has a bounded independent checker receipt.

| Method | Reachable | Unreachable | Unknown |
|---|---:|---:|---:|
| Frontier count planner, depth-first execution | 94 | 0 | 98 |
| Frozen breadth-first frontier count planner | 93 | 0 | 99 |
| Frozen state-budget count planner | 93 | 0 | 99 |
| Frozen combined portfolio | 104 | 85 | 3 |
| Frozen existing solver | 98 | 85 | 9 |

Depth-first execution gains SharedMemory-PT-000020 RC00 over breadth-first, with
no losses. It finds the checked 18-step witness after creating 172 states, whereas
the breadth-first version hits its storage bound. Relative to the old count
planner, it retains the TokenRing-PT-005 RC08 gain with no losses.

The candidate adds no positive over either portfolio. It remains an optional
experimental solver; this result does not justify adding another portfolio stage
or establish a substantial advantage. The main portfolio remains unchanged.

The change only affects execution order. Both variants require a complete
target-free count-bounded graph before learning a frontier cut. Seven tests,
Clippy and the release build passed before freezing the candidate, including an
18-independent-transition fixture that checks witness discovery without requiring
enumeration of every interleaving. All control binaries were frozen before this run.

This is one shared-Mac development repeat with a one-second budget shared across
canonical property branches and sampled 2 GiB memory. It establishes these paired
coverage results, not stable timing, held-out generalization or novelty.

Plan SHA256: a7b6278d25b57cededd87a9fc4bda399f5a55e75d608f50b2291fd77dc9ccaf3.
Raw rows: results/frontier-counts-development-v2/runs.jsonl.
Frozen source/executables: results/solver-frontier-counts-development-v2.
Audit: audit.json, produced by ../audit-frontier-counts-development-v2.py.
