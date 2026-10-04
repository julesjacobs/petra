# Stress development challenge sets

Outcome-selected development views. Unknown is not unreachability. Report the full corpus separately; these are not held-out evaluation.

Selection uses the completed 5-second, single-core Linux comparison, with a 2 GiB limit.
All filters operate on `benchmarks/mcc-stress-development`; inputs are not copied or modified.

| View | Properties |
|---|---:|
| candidate-unresolved | 70 |
| both-candidates-unresolved | 62 |
| all-unresolved | 12 |
| verifypn-only | 58 |
| candidate-only | 11 |
| any-unresolved | 87 |

Candidate means the Rust frontend in candidate-only/verifypn-only views.
Both candidate configurations use the same frozen engine with different frontends.

Pass a filter file as the existing benchmark runner’s `--filter` argument.
Use the full 368-property corpus for headline comparisons.

| Family | Total | Python frontend | Rust frontend | VerifyPN | All unresolved |
|---|---:|---:|---:|---:|---:|
| AutoFlight | 48 | 39 | 38 | 48 | 0 |
| CANConstruction | 48 | 39 | 38 | 43 | 0 |
| CircularTrains | 32 | 32 | 32 | 32 | 0 |
| CloudOpsManagement | 48 | 47 | 47 | 47 | 1 |
| DLCflexbar | 48 | 16 | 17 | 39 | 9 |
| Echo | 48 | 48 | 48 | 43 | 0 |
| GPUForwardProgress | 48 | 48 | 48 | 48 | 0 |
| JoinFreeModules | 48 | 30 | 30 | 45 | 2 |
