# Reduction-round ablation

All six registered branch/round combinations completed and passed artifact audit.
With three seconds and 200,000 BFS states per branch, zero rounds and one round
both hit the state limit on both branches. Two rounds prove both branches
unreachable, exhausting 101,476 and 74,840 states, respectively; independent
original-input reduction-chain and finite-closure checks pass.

This isolates the benefit of repeated buffer/relevance reduction at the registered
state limit. It does not establish that one round cannot succeed with a larger
state budget. No duplicate-transition elimination was used. See plan.json,
results.json, audit.json and the preserved source/binary snapshots.
