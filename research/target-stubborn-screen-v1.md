# Target-directed stubborn-set screen

The target-directed portfolio and focused baseline each solved **47/104**
properties: 31 reachable, 16 unreachable and 57 unknown. There were three gains
and three losses, with 44 common solves and 50 properties solved by their union.
This screen establishes no net coverage improvement or stable speedup.

| Development track | Properties | Focused | Target-directed |
|---|---:|---:|---:|
| MCC stress | 50 | 28 | 30 |
| FastForward random walks | 44 | 19 | 17 |
| Synthetic | 10 | 0 | 0 |
| Total | 104 | 47 | 47 |

Gains were `AutoFlight-PT-96b__RC09`, `CANConstruction-PT-090__RC06`, and
`ff_random_walk_dekker_vs_satabs_2_multi_25_0_ce78db7b`. Losses were
`ff_random_walk_Function_Pointer3_vs_satabs_3_multi_40_0_6edcf2e4`,
`ff_random_walk_dekker_vs_satabs_2_multi_30_0_60ea6be9`, and
`ff_random_walk_lu_fig2_fixed_vs_satabs_3_multi_60_0_7e4914f0`.
The conditional median target-directed/focused wall-time ratio was 0.996 across
44 common solves; it excludes all unresolved properties and is not an overall
speedup estimate.

The complete matrix has 208 rows: one five-second repetition of
`portfolio-focused` and `portfolio-target-stubborn` using the same frozen Rust
binary on macOS arm64. Each original PNML/XML property includes startup, parsing,
preprocessing and solving inside the deadline, with zero outer grace, a
2,000,000-state cap and a 2 GiB sampled process-tree RSS limit. Independent
validation is separate from solver timing. All 94 definitive rows passed
original-input checking; no validation failures or exact branch duplicate groups
were found. Each method had 57 outer timeouts; neither had a memory-limit event.

All **36 native FastForward positive rows** additionally passed independent
replay on original LoLA nets and formulas, covering all positive rows of both
methods in that track. The first replay attempt used system Python and recorded
36 driver errors because `psutil` was unavailable; no witnesses were checked in
that attempt. Its complete outcomes remain preserved. The repository Python
retry verified 36/36, with zero unknown/error outcomes and no solver reruns.

This is an outcome-selected development subset of the **620-property parent
corpus**, not held-out evaluation. One repetition on a shared local host does
not establish robust performance; the 104-property denominator and all failures
are retained. The earlier visibility-based stubborn-set repeat plan remains a
separate obligation. No competitor run is part of this same-binary screen.

Evidence:

- [Registered plan](target-stubborn-screen-v1-plan.json),
  [analysis](target-stubborn-screen-v1-analysis.json), and
  [identity/resource/answer verification](target-stubborn-screen-v1-verification.json).
- [Complete measured rows](../results/target-stubborn-screen-v1/runs.jsonl) and
  [environment](../results/target-stubborn-screen-v1/environment.json).
- [Successful original-LoLA replay](../results/target-stubborn-screen-v1-lola-replay/venv-retry/report.json),
  [all successful replay rows](../results/target-stubborn-screen-v1-lola-replay/venv-retry/runs.jsonl),
  and [preserved environment-failure attempt](../results/target-stubborn-screen-v1-lola-replay/report.json).

Frozen solver SHA-256:
`370a39e384f8bae9ead849515c9d844b47bb63b784fd5ba19f334c665f6958e0`.
