# Harder original-input count-portfolio comparison

Registered 176 properties (175 distinct ordered-branch representatives), five
configurations, 880 rows. Each invocation gets five seconds, CPU 8, enforced 2 GiB
and perf counters. Native outputs are independently checked outside solver timing.
Competitor verdicts are tool-reported. All inputs and failures remain in the matrix.

Configurations: experimental native-counts; frozen native-walk; frozen existing
native-frozen; VerifyPN default; SMPT official MCC portable. The latter was selected
by whole-cohort coverage in the completed prior screen. Same original PNML/XML,
preprocessing policy for native methods, seeded property order and frozen runner.
No reserved-family queries are included. One repeat does not establish stable speed.

The initial build failed before compilation because default Rust 1.78 lacks edition
2024. Its script, log and receipt are preserved. The second build explicitly used
Rust 1.97.1, matching frozen walk provenance, and passed all 11 targeted tests.
Linux candidate source, binary and build receipts are preserved under
results/linux-solver-portfolio-counts-v1. Original Mac sources match the frozen
portfolio-counts-development-v1 source manifest byte for byte.

All 20 harness cases and five SMPT component checks passed; fetched receipts passed
an independent artifact consistency check. Deployment verified all 1,158 runtime
and 45 preflight pins. The full comparison was dispatched only afterwards.

Plan SHA256: de15c42faa62b3dffd6a8a27a6d922b7691fe1fbc51edf54b19cdb903cb38f40.
Use research/poll-portfolio-counts-linux-v1.py to observe the exact process identity.
Do not restart because polling fails or times out. No remote builds, competing
measurements or bulk transfers while the job is live.

After terminal receipt, use research/collect-portfolio-counts-linux-v1.py to fetch
all artifacts, then:

    vendor/venv/bin/python research/audit-general-development-v3-linux-v1.py --plan research/portfolio-counts-linux-v1/plan.json --results results/linux-portfolio-counts-v1 --output research/portfolio-counts-linux-v1/audit.json
    vendor/venv/bin/python research/summarize-portfolio-counts-linux-v1.py

The generic auditor accepts explicit plan/results/output paths. Inspect all issues
and disagreements before reporting coverage. The frozen existing solver and strong
competitors are rerun here; historical timings are not substituted for matched runs.
