# Repeated reductions plus BFS: complete development screen

All 768 rows passed artifact audit, with no validation warnings or answer
 disagreements. The complete 192-property cohort gives:

| Method | Reachable | Unreachable | Unknown |
|---|---:|---:|---:|
| Reduced BFS | 90 | 60 | 42 |
| Frozen count portfolio | 101 | 85 | 6 |
| Frozen walk portfolio | 101 | 85 | 6 |
| Frozen existing portfolio | 98 | 85 | 9 |

Reduced BFS adds three independently checked reachable properties over every
control: DoubleExponent-PT-003 RC05, RC06 and RC11. It misses 39 properties solved
by the count/walk controls, including 25 negatives. It is therefore a complementary
component rather than an evidence-supported replacement. The diagnostic union with
the count portfolio solves 189/192, but that union is not an implemented solver.

The three new positives completed in approximately 0.11–0.14 seconds each in this
single local run. These observations motivate testing a bounded portfolio stage;
they do not predict performance under a different stage allocation. Reduced BFS
attempted 279 branches, with one outer expiration and no sampled memory-limit
failures; maximum sampled RSS was 237,715,456 bytes.

One second per property was shared across canonical branches. All methods used
sampled 2 GiB limits and separate bounded independent validation; reduced BFS's
internal 200,000-state cap is lower than the other solvers' 2,000,000-state cap.
This is one shared-Mac development repeat, with no stable speed, original-input
whole-cohort or general superiority claim. The separate Cloud original-property
result is outside this cohort.

Plan SHA256: c89cf86d73a172fda3c91df1b130f69dc5a92039616fdb1f59a50657cd9e97eb.
Frozen artifacts: results/solver-reduced-bfs-development-v1.
Raw evidence: results/reduced-bfs-development-v1.
Audit and diagnostics in this folder retain every paired loss, failure and check.
