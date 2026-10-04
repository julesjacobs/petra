# Repeated original-input Linux comparison

Registered and launched: 4,224 original-property invocations, four frozen methods,
176 properties (175 distinct ordered-branch representatives), three separately
ordered blocks at each of five and thirty seconds. The main combined solver,
frozen existing solver, unrestricted VerifyPN and qualified SMPT MCC portable
configuration are unchanged from the audited preceding comparison.

| Block | Seconds | Query-order seed |
|---|---:|---:|
| b1-5s | 5 | 2026092807 |
| b2-30s | 30 | 2026092808 |
| b3-30s | 30 | 2026092809 |
| b4-5s | 5 | 2026092810 |
| b5-5s | 5 | 2026092811 |
| b6-30s | 30 | 2026092812 |

Each block has one repeat and 704 rows. Method rotation and each query order are
determined by the frozen runner and recorded seed. Native random seeds are fixed.
CPU 8 affinity, enforced 2 GiB memory, performance counters, and separate bounded
native validation remain unchanged. No new solver, held-out family, or frontier
count experiment is included.

Fresh qualification at both budgets passes 32 EF/AG harness rows and ten SMPT
SMT/CP/WALK component rows. Four seed-only capability derivations explicitly check
that only output location, order seed, block name and receipt location differ.
Fetched artifacts and native binary registrations pass check-repeated-capability-v1.py.

Suite SHA256: 8ab24b5b7d3c7fdde01832cbcacd39908764da6ef7df55d10961a4cb9ac94d36.
Qualification SHA256: a5359c75394f7aa134a27c928a00b5cb8c194257f3d3ddda3904995b186f75e2.
Capability archive SHA256: 8a1fb8a45993e62ec13c9d400c3b7be7d7f20751cc84babffe950be2ad125d39.

Remote job: pid 1786482, creation 1790609624.42, boot
17c1d989-ad9a-424e-9347-88bc5cb8e11b, on jules-b650-aorus-elite-ax-v2.
Observe it with:

    vendor/venv/bin/python research/manage-repeated-comparison-linux-v1.py poll

Do not restart after observation failures. Do not build, benchmark, deploy or
transfer bulk data on the remote host until the suite is authoritatively terminal.
All six blocks are already queued by the same sequential process. Launching a
later block manually would duplicate work and invalidate measurement isolation.

After authoritative suite termination and with the local measurement gate clear:

    vendor/venv/bin/python research/collect-repeated-comparison-linux-v1.py

The collector also preserves partial failed suites, without declaring them complete.
It refuses to collect a live job. For a successfully downloaded but not imported
archive, inspect the failure and use --import-existing rather than retransferring.
Run the existing generic artifact auditor separately for each registered block,
using its plan.json, results/linux-repeated-comparison-v1/BLOCK, and BLOCK/audit.json.
Then aggregate only audited blocks under the analysis rules frozen in suite.json.

The registered analysis reports per-block solved sets, paired gains/losses, three-run
solved frequencies and timing ranges, and PAR-2 over the full denominator. Missing
counters are never imputed. Three blocks assess repeatability; they do not establish
precise population-level uncertainty. Native answers are independently checked;
external verdicts are tool-reported. No repeated-run result is available at launch.
