# Development comparison

256 original properties; 5.0s common outer deadline; 1 repetition(s).

| Method | Reachable | Unreachable | Unknown | Error/unstable |
|---|---:|---:|---:|---:|
| frozen-v2 | 69 | 111 | 76 | 0 |
| portfolio-causal | 73 | 155 | 28 | 0 |
| smpt-full-portable | 77 | 108 | 71 | 0 |

Definitive disagreements: [].

Every complete property in the interrupted segment was retained regardless of outcome. Incomplete and unvisited properties were rerun in full. The only execution-path runner change catches a macOS process-environment API error during cleanup. Source snapshots and segment provenance remain available.

All definitive native property answers have independently checked proofs or witnesses; per-branch verification status is recorded in runs.jsonl. External SMPT proofs were not independently checked. SMPT uses the documented portable plain-WALK compatibility patch with automatic reduction. This is one shared-host exploratory pass, not publication-grade timing.

Input-cost boundary: native solvers received pretranslated JSON branches, while SMPT received original PNML/XML with parsing and reduction inside timing. This run does not establish matched original-input end-to-end superiority.

Causal portfolio vs frozen v2: 48 additional solves, 0 lost solves.

| Family | Additional solves | Lost solves |
|---|---:|---:|
| AutoFlight | 0 | 0 |
| CANConstruction | 13 | 0 |
| CircularTrains | 3 | 0 |
| CloudOpsManagement | 0 | 0 |
| DLCflexbar | 13 | 0 |
| Echo | 19 | 0 |
| GPUForwardProgress | 0 | 0 |
| JoinFreeModules | 0 | 0 |

Runs with dependency/interface failures: 0.
