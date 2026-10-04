# Sparse token-flow comparison

Full37-query classical SMPT corpus,148runs,2seconds,one repetition per configuration,originalPNML/XML and independent bounded proof validation. Frozen versions differ only in production src/token_cut.rs; binaries/sources and runner snapshots are preserved.

| Engine | Before | Sparse implementation |
|---|---:|---:|
| token-cut |12/37|12/37|
| bounded-token-cut |13/37|13/37|

No coverage gains or losses. All50 definitive answer rows independently checked, no disagreements or validation failures. Local single-repetition timing does not establish a speedup. Sparse construction is a verified implementation improvement, not a demonstrated competitive advantage.

Each candidate reports24 unknown branch outcomes with no certified one-hot control abstraction. That measured limitation motivates extending the same token-flow algorithm to exact finite projections of certified bounded counters. This extension is in progress, not part of the measured binary.

Plan: research/sparse-token-flow-classic-v1-plan.json. Full audit: research/sparse-token-flow-classic-v1-analysis.json. Identity and reason audit: research/sparse-token-flow-classic-v1-verification.json. All local measurement processes are terminal.
