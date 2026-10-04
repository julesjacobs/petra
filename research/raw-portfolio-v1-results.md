# Credited component invariants: measured raw stress results

The deployed `raw-portfolio` verifies all 12 valid stress queries in both repetitions, up from the earlier positive-only solver's 9/12. It produces nine checked witnesses and three independently checked negative certificates. This is one sequential invocation with one shared solver deadline, not a union of best answers from separate runs. The negative phase receives at most one quarter of remaining solver time; the positive phase receives the remainder if needed.

All 18 selected source programs remain in the benchmark denominator. Six failed during export and are still unavailable. The 10-second outer deadline includes input hashing/parsing, solver startup and work, and independent verification. RSS is sampled with a 2 GiB cap on a shared Mac; these are exploratory development measurements, not Linux hardware instruction results or held-out evaluation.

| Newly proved negative | Repeat 1 seconds | Repeat 2 seconds | Largest sampled RSS MiB |
|---|---:|---:|---:|
| counter_d31_s16_locked | 0.742 | 0.694 | 194.3 |
| replicas_n8_locked | 0.227 | 0.224 | 70.2 |
| replicas_n10_locked | 0.932 | 0.927 | 288.5 |

The initial invariant implementation solved the small examples, but no full stress query passed all timed stages. Indexed controller transitions then verified the eight-cell locked replica. Replacing conservation synthesis with the direct structural controller projection removed a substantial discovery cost, and the Python checking work limit was made explicit at 100×max_states (20 million by default), matching the Rust budget scale. Neither change relaxes checking obligations; the same wall and memory limits remain. The larger counter proof already checked in a separate diagnostic with that higher operation cap. These combined revisions are not an isolated algorithm-only ablation.

The complete positive and negative modes were rerun separately with the structural discovery version: nine stable positives and three stable negatives, no disagreements. The subsequent single portfolio run preserved all 12 answers. Source archives, binaries, runner snapshots, input hashes, intermediate failures and full selected-source denominators are retained in each result directory. The final binary is `results/solver-raw-portfolio-v1/vass-reach`; see its SHA256SUMS and the machine-readable analysis beside this file.

This proves progress on the raw serializability development workload. It does not establish a complete decision procedure, novelty of the invariant construction, or superiority over VerifyPN/SMPT on ordinary Petri-net benchmarks. The six failed exports and fresh evaluation remain outstanding.
