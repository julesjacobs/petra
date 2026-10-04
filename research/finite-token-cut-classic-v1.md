# Finite-control token-flow comparison

The full37-query classical SMPT corpus was run at2seconds,one repetition per
configuration,originalPNML/XML,2GiB sampled memory and independently bounded
Python verification. All111rows are retained.

| Configuration | Solved |
|---|---:|
| Frozen prior bounded-token-cut |13/37|
| Refactored bounded-token-cut |13/37|
| Finite-control token-cut |19/37|

No refactoring regression and six finite-engine gains, with no losses. All45
definitive answer rows passed independent checking; no disagreements or errors.
Four gains use nonempty finite controls: Expressiveness/CryptoMiner,
NTest/CryptoMiner,TokenTank/CryptoMiner-50 andCryptoMiner-10000. The other gains
are Sara/test12 (empty-projection refutation) andNTest/3u (replayed witness).

Three pairs have byte-identical ordered canonical branches: the two plain
CryptoMiner queries, the twoParity queries and the twoPGCD queries. Keeping
the lexicographically smallest representative gives34queries and13→18solves,
five gains and no losses. This limited duplicate check is not semantic or
graph-isomorphism deduplication.

These are local development coverage results, not isolated timing or competitive
superiority over the complete portfolio,SMPT orVerifyPN. Earlier portfolio
results must not be conflated with this specific bounded-token-flow baseline.

One actionable remaining failure: CryptoMiner-500 times out, while50 and10000
are solved. The50 proof selects[0,2,3,4] and enumerates204terminals; the10000
proof uses[2,3],three terminals and two flow cuts. At500 the selection policy
can still admit the large resource coordinate, whereas at10000 it exceeds the
domain-product cap and is skipped. A small-domain projection stage before
larger products is a proposed scheduling repair; causality and improvement
require a frozen ablation. The original timeout is preserved.

Plan: research/finite-token-cut-classic-v1-plan.json.
Audit: research/finite-token-cut-classic-v1-analysis.json.
Identity/proof/duplicate audit: research/finite-token-cut-classic-v1-verification.json.
Frozen binary: results/solver-finite-token-flow-v1/vass-reach.
All local measurement and build processes are terminal.
