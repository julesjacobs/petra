# Staged finite projection comparison

Full37-query classical SMPT corpus,296runs,2seconds,2repetitions,originalPNML/XML,
2GiB sampled memory and separately bounded independent validation.

| Method | Stable solves |
|---|---:|
| Finite projection v1 |19/37|
| Staged finite projection v2 |20/37|
| Full focused portfolio |37/37|
| Full symbolic portfolio |37/37|

Staging adds CryptoMiner-500 in both repetitions with no losses. The new policy
tries domain products16,256,4096 and deduplicates selected prefixes; certificates
and arithmetic are unchanged. Focused9finite tests,4token-cut unit tests and
Clippy passed; the preceding implementation has334passing full Rust tests.

All226definitive answers independently checked. No errors or disagreements.
After removing the three exact canonical duplicate pairs, stable coverage is
18/34,19/34,34/34,34/34. These are local coverage results, not precise speedups.

The new engine adds no solve beyond either full portfolio on this suite.
Consequently the classical corpus is a regression/diagnostic set for the full
solver, not evidence of a new competitive advantage. Evaluation on the hard
69-query development view is the next coverage test.

Plan and audits: research/staged-finite-token-cut-classic-v1-{plan,analysis,verification}.json.
Frozen candidate: results/solver-finite-token-flow-v2/vass-reach.
All local run/build handles are terminal.
