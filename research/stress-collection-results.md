# Stress input collection, 2026-09-27

All 23 selected MCC models / 368 properties imported successfully. Selection used published instance order rather than solver outcomes. This is correlated stress-development data; solver difficulty has not yet been measured.

| Model | Places | Transitions |
|---|---:|---:|
| DLCflexbar-PT-7b | 35101 | 55507 |
| DLCflexbar-PT-8a | 3971 | 32571 |
| DLCflexbar-PT-8b | 47560 | 76160 |
| JoinFreeModules-PT-1000 | 5001 | 8001 |
| JoinFreeModules-PT-2000 | 10001 | 16001 |
| JoinFreeModules-PT-5000 | 25001 | 40001 |
| CircularTrains-PT-384 | 768 | 384 |
| CircularTrains-PT-768 | 1536 | 768 |
| AutoFlight-PT-48b | 3950 | 3936 |
| AutoFlight-PT-96a | 2251 | 2225 |
| AutoFlight-PT-96b | 7894 | 7868 |
| Echo-PT-d03r07 | 4209 | 3518 |
| Echo-PT-d04r03 | 1019 | 850 |
| Echo-PT-d05r03 | 3717 | 3222 |
| CANConstruction-PT-080 | 13762 | 26240 |
| CANConstruction-PT-090 | 17282 | 33120 |
| CANConstruction-PT-100 | 21202 | 40800 |
| CloudOpsManagement-PT-05120by02560 | 27 | 29 |
| CloudOpsManagement-PT-10240by05120 | 27 | 29 |
| CloudOpsManagement-PT-20480by10240 | 27 | 29 |
| GPUForwardProgress-PT-36b | 720 | 757 |
| GPUForwardProgress-PT-40a | 168 | 209 |
| GPUForwardProgress-PT-40b | 796 | 837 |

The raw SER frontend probe exported all five selected sources using `--export-raw --no-viz`. These exports still need bounded structural validation and solver/checker runs.

| Source | Frontend seconds | Query bytes |
|---|---:|---:|
| counter_d31_s16_racy | 2.233 | 4501868 |
| counter_d31_s16_locked | 8.569 | 8749833 |
| replicas_n8_racy | 0.687 | 2407768 |
| replicas_n8_locked | 1.395 | 4674245 |
| monitor_d4_c64 | 0.142 | 737557 |

MCC collection: 120s/model, 2GiB sampled RSS, 3GiB counted artifacts. Raw probe: 60s/source, 2GiB sampled process-tree RSS, 3GiB sampled artifacts. Local safeguards are not Linux cgroup/disk quotas. Archive hashes, frozen selections, source/runtime snapshots and complete outcomes are retained in the respective corpus directories.

## Full raw collection and validation

All 18 selected sources were attempted at 120 seconds/source. Twelve exported and all twelve passed bounded structural validation; six timed out in frontend construction (counter 63/32 and 127/64, both locked/racy; replicas 12, both locked/racy). These six are unavailable backend inputs, not solver unknowns. Validation results: `results/raw-stress-validation-v1/validation.json`.

| Source | Places | Transitions | Serial components |
|---|---:|---:|---:|
| counter_d31_s16_racy | 590 | 15439 | 84 |
| counter_d31_s16_locked | 621 | 30846 | 84 |
| replicas_n8_racy | 1314 | 8708 | 24 |
| replicas_n8_locked | 1570 | 16900 | 24 |
| replicas_n10_racy | 5162 | 43012 | 50 |
| replicas_n10_locked | 6186 | 83972 | 50 |
| monitor_d4_c64 | 528 | 2070 | 11 |
| monitor_d4_c128 | 1040 | 4118 | 11 |
| monitor_d4_c256 | 2064 | 8214 | 11 |
| monitor_d5_c128 | 1297 | 6426 | 13 |
| monitor_d5_c256 | 2577 | 12826 | 13 |
| monitor_d5_c512 | 5137 | 25626 | 13 |

The 18 sources include four explicit bridge duplicates of earlier scaling programs. All are correlated extensions of existing families, not independent held-out families. Raw solver and original-input MCC pilots remain separate from collection.

## Completed raw solver pilot

At a 10-second input-inclusive deadline and a sampled 2 GiB memory limit, the four approaches together produced five independently checked positive answers among the twelve valid raw queries. Seven valid queries remain unresolved by every tested approach. This is one development repetition; it is not a general performance record.

| Approach | Verified positives / 12 valid queries |
|---|---:|
| raw-bfs | 1 |
| raw-search | 1 |
| raw-potential | 4 |
| raw-z3 | 0 |

The unresolved inputs are:

- `counter_d31_s16_locked`
- `monitor_d4_c256`
- `monitor_d5_c256`
- `monitor_d5_c512`
- `replicas_n10_locked`
- `replicas_n10_racy`
- `replicas_n8_locked`

The six frontend timeouts are separate from these solver unknowns. Current raw engines cannot certify negative results, so the locked cases expose a capability gap as well as a benchmark challenge. `raw-z3` denotes the direct quantified BMC implementation, not SMPT. Detailed report: `results/raw-stress-v1-pilot/REPORT.md`; exact analysis: `research/raw-stress-v1-analysis.json`.

The complete 368-property MCC pilot is running on Linux, pinned to CPU 8 with instruction counters, a 5-second original-input deadline and a 2 GiB cgroup. Its final coverage is not yet available.
