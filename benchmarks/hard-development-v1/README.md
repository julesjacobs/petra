# Hard development view

26 existing queries selected from complete, audited five-second comparisons:

| Track | Selected | Full source corpus | Compared configurations |
|---|---:|---:|---|
| MCC application properties | 16 | 368 | Two frozen Rust versions, VerifyPN |
| Boolean consistency | 10 | 34 | Three Rust configurations, VerifyPN, SMPT |

Every selected query returned unknown in every compared configuration. No
selected row reported a setup error or capability failure. This establishes
difficulty only at the measured five-second budget and those configurations.
The MCC selection has not yet been qualified against SMPT.

`manifest.json` is directly usable as a corpus by
`scripts/benchmark_smpt_classic.py`. It retains the original PNML/XML, canonical
queries, properties, and hashes through relative references to the frozen
sibling corpora. Transfer those corpora with this view. All referenced solver
inputs were hash checked, and both complete source matrices were audited again.
`scripts/build_hard_development.py` reproduces the selection from the raw runs.

These are existing inputs, not 26 additional independent benchmarks. Report
the two tracks separately. Within MCC, 15 properties come from two DLCflexbar
instances and one from CloudOpsManagement; this is limited application diversity.
Keep the complete 368- and 34-query corpora for regression comparisons.

The prepared qualification in `research/hard-development-v1-plan.json` gives
each of focused Rust, symbolic Rust, VerifyPN and SMPT 60 seconds on one pinned
Linux CPU with 2 GiB, including parsing and preprocessing. It has not started.
This is a coverage screening pass; timing claims need repetitions. Subsequent
300-second qualification will retain every jointly unresolved case and distinguish
resource exhaustion from setup failures. Reserved evaluation families are untouched.
