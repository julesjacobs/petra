# Nonzero-bound control selection: completed ablation

Prioritizing certified nonzero bounds prevents zero-bound places from consuming
all 16 control slots. It changes proposal order only; proof semantics are unchanged.

The paired local comparisons completed at two seconds per original property,
one repetition and a sampled 2 GiB limit:

| Corpus | Queries | Before solved | After solved |
|---|---:|---:|---:|
| Classical SMPT | 37 | 20 | 20 |
| Hard development | 69 | 0 | 0 |

All 212 rows are present. All 40 definitive rows passed independent checks.
There are no coverage gains, losses, reported errors, or definitive disagreements.
Registered manifest, binary and archived runner hashes match. The hard unknown
reason distributions remain very similar. This experiment establishes no
performance improvement. The harder corpus remains outcome-selected development
data, with its complete 620-query parent denominator and reserved families retained.

Read-only structural diagnosis explains a separate obstacle. For DLC7b and DLC8b,
any projection of at most 16 places retains at least 53,490 and 73,638 stutter
edges respectively, already exceeding the 8,192-edge limit. Representative
backward relevance leaves these nets unchanged. In affected FastForward nets,
many independently certifiable zero coordinates produce the same graph as an
empty projection. Actual timed bound discovery/selection traces were not recorded;
structural reconstructions do not establish which subsets were discovered at runtime.

Next experiment: implicit stutter columns with certificate-guided column generation.
Restricted-master infeasibility must never count as a negative result until every
omitted eligible original edge satisfies the exact Farkas inequality. Preserve all
mode-changing edges in separation, including zero-count edges with infinite upper
bounds. This is an implementation proposal, not a measured gain.

Evidence: `nonzero-control-{classic,hard}-v1-analysis.json`, registered plans of
the same names, `nonzero-control-v1-verification.json`, and complete raw result
directories under `../results/`. Frozen candidate:
`../results/solver-nonzero-control-v1/`.
