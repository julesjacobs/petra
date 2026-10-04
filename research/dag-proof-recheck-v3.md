# Higher-budget independent DAG checking

Two of the three previously proposed negative answers now pass independent
original-input translation, CNF regeneration and Python RUP checking:

- random3_n72_r480_s2026092702
- random3_n96_r426_s2026092702

random3_n96_r480_s2026092701 reaches the 30-second checker deadline and remains
unknown. No answer from it is credited.

This experiment rechecks preserved outputs from
results/dag-limits-diagnostic-v2; it does not rerun any solver. Each proof is
copied into a new directory with its SHA256 recorded. Checker bounds are
200 million work,30 seconds,16 MiB response/output metadata allowance and 2 GiB
sampled process-tree RSS. The Rust outputs were generated with the larger
standalone DAG work budget in that earlier diagnostic. These results must
not be added to the 24/34 headline from the differently configured full run.

The default checker work allowance remains 20 million. The new optional
--validation-dag-work setting records and propagates an explicit work budget.
Internal checker exhaustion is now unknown/checker-resource-limit; malformed
proofs remain errors. External deadline termination is unknown/timeout.

Complete requests, proof hashes, checker snapshots and bounded results:
results/dag-proof-recheck-v3. Reproduction script:
research/recheck-dag-proofs-v3.py. Earlier failed experiments are retained.
