# Linux row-limit diagnostic

The new build moves the exact original-row count check ahead of dense matrix allocation in rational and integer state-equation solving. A regression test checks that over-limit sparse inputs never call the dense constructor, while exact-limit certificates remain independently valid. The prior code allocated places×transitions BigInts and transitions×transitions rational rows before inevitably rejecting models above max_rows.

The completed diagnostic selects the first lexicographic native OOM query per family from the previous stress run: four properties, three methods, two repetitions. It uses original inputs, CPU8, user-space perf counters, an enforced 2 GiB limit and a 5-second deadline, with separately bounded candidate proof checking. All 24 rows completed. These are outcome-selected development diagnostics, not full-corpus or held-out results.

| Build/tool | Stable solves / 4 | OOM runs / 8 | Timeout runs / 8 |
|---|---:|---:|---:|
| Frozen predecessor | 1 | 6 | 0 |
| New build | 1 | 0 | 6 |
| VerifyPN | 4 | 0 | 0 |

No definitive disagreement was reported. The CANConstruction case now solves in both native builds, although its earlier run was an OOM; that is variability, not an improvement attributable to this change. The new build still peaks around 1.3–2.0 GiB on the other cases and gains no answers. It includes earlier compact-search improvements as well as the row-limit guards, so this is not a pure guard-only ablation.

The source-level allocation defect is verified and fixed. There is no demonstrated ordinary-net coverage improvement here. The separate dense incidence construction in count_plan remains a risk and should be replaced with sparse processing or a bounded dispatch before another full competition run. Frozen artifacts and hashes are retained remotely in results/linux-solver-raw-negative-structural-v1; report, runs and environment have been copied locally.
