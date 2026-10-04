# Harder original-input Linux count-portfolio comparison

All 880 rows completed, were collected, and pass the artifact audit with zero issues
or warnings. This is 176 properties, or 175 distinct ordered-branch representatives.

| Method | Reachable | Unreachable | Solved |
|---|---:|---:|---:|
| Native count portfolio | 89 | 45 | 134 |
| Frozen native walk | 88 | 45 | 133 |
| Frozen existing solver | 83 | 45 | 128 |
| VerifyPN default | 83 | 46 | 129 |
| SMPT official MCC portable | 52 | 45 | 97 |

Count vs walk: one checked gain (RefineWMG-PT-100101 RC11), no losses. Count vs frozen
existing: six gains, no losses. Count vs VerifyPN: six gains and one loss, the
CloudReconfiguration negative case. Count vs SMPT MCC: 37 gains, no losses. Native
answers were independently checked; external competitor answers remain tool-reported.

This comparison measures the count portfolio. The newer combined portfolio including
reduced BFS is not represented here: its separate local development screen solves
189/192, and its Cloud negative result is currently an independently checked local
original-input diagnostic. Neither result may be substituted into this Linux table.

Every invocation used five seconds, CPU8, enforced2GiB, perf and separate bounded
validation on the original PNML/XML. Strong competitor configurations were selected
using the completed prior whole-cohort screen. This is one development repeat;
several controls differ by one result from the previous run. No stable timing,
substantial general advantage, held-out success or publication-readiness claim.

The initial artifact audit exposed a plan metadata inconsistency: methods.native-counts
contains descriptive prose, while native_tools.native-counts correctly records the
CLI engine portfolio-walk-counts and its pinned binary. The original plan remains
unchanged. analysis-plan-amendment.json records the sole analysis-only normalization.
The specialized audit verifies exact equality of every other field, original
execution/terminal/capability identities, environment registration and every native
command. Both failed generic audit attempts are preserved: the first rejected the
prose field, the second correctly rejected using the derived view's hash as the
execution plan hash. No run, limit, verdict or configuration was changed.

Original plan SHA256: de15c42faa62b3dffd6a8a27a6d922b7691fe1fbc51edf54b19cdb903cb38f40.
Raw results: results/linux-portfolio-counts-v1. Collection contains 3,873 files.
Run research/audit-portfolio-counts-linux-v1.py for the complete audit, then
research/summarize-portfolio-counts-linux-v1.py. The generic auditor alone expects
one plan identity and is insufficient for this documented interpretation correction.

Next qualify the combined portfolio on Linux using the locally prepared v3 checker,
then compare full cohorts with matched frozen controls, repeats and held-out families.
