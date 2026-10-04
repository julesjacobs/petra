# Double-lock gap diagnostic

The live Linux300s run reported a VerifyPN positive for
`ff_random_walk_double_lock_p2_vs_satabs_2_multi_100_0_c52c1204`, while both frozen
Rust configurations and SMPT returned unknown. This is preliminary external
output; the full Linux matrix and its audit are still pending.

Two subsequent local30s diagnostic runs used the frozen macOS capacity-direct
binary with original PNML/XML,2M states,2GiB sampled RSS,32s outer cap and separate
60s bounded validation. Both terminated normally with unknown. Inputs,
binary/source identities, runner snapshots, the complete two-row matrix,
profile events and saved validation responses were checked. There are no
definitive answers or witnesses to validate. No Linux workload was added.

| Phase | Focused | Symbolic |
|---|---:|---:|
| Original-input parse | 0.0075s | 0.0066s |
| Relaxed search | 17.65s /309,215 states | 17.64s /355,402 states |
| Reduced guided search | 1.81s /310,204 states | 1.83s /399,520 states |
| Guided search | 4.22s /1,509,701 states | 4.26s /1,524,304 states |

States are each phase's reported counts, not disjoint states or equal-work
throughput. The symbolic DAG phase returned in0.008s because it found no
certified one-token controller. Both configurations then followed essentially
the same portfolio, with causal, local-closure, arithmetic, backward and quotient
phases also inconclusive. This points to search/representation as the useful
next investigation; original-input parsing does not explain this gap.

This is a single outcome-selected mechanism diagnostic on macOS, not a fair
timing comparison with Linux or a coverage experiment. The older binary emits
portfolio phase events but no detailed relaxed events despite the profile flag;
there is no evidence here isolating relaxed-plan computation from queue or
successor costs. Preserve the broader application screen before changing
portfolio scheduling to fit this case.

Evidence:double-lock-gap-diagnostic-v1-{plan,analysis}.json and
results/double-lock-gap-diagnostic-v1. The plan references a live source-log hash;
double-lock-gap-selection-v1.log preserves the exact matching prefix, recovered
by matching its registered SHA256. The original plan remains unchanged.
