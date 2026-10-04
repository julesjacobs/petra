# Hard development view v2

69 existing queries selected from complete five-second comparisons:

| Track | Selected | Full source corpus | Compared configurations |
|---|---:|---:|---|
| MCC application properties | 16 | 368 | Two Rust versions, VerifyPN |
| Boolean consistency | 10 | 34 | Three Rust configurations, VerifyPN, SMPT |
| FastForward | 43 | 218 | Two Rust versions, VerifyPN, SMPT |

Every selected query remained unknown in every compared configuration and
repetition. This establishes difficulty only for those configurations at five
seconds. The MCC selection has not yet been qualified against SMPT. No selected
row reported a setup or capability failure; timeout interruption diagnostics
are preserved in the selection provenance.

This is an outcome-selected development view, not additional independent data
or held-out evaluation. Diversity remains limited: 15 MCC queries are from two
DLCflexbar instances, one is from CloudOpsManagement; the Boolean cases are
seven random-3SAT and three pigeonhole queries; all 43 FastForward cases are
from its random-walk suite. Report tracks separately and retain the complete
620-query parent denominators for regression comparisons. Indexed duplicate
audits do not establish graph-isomorphism or semantic distinctness.

`manifest.json` works with `scripts/benchmark_smpt_classic.py`. Original inputs,
canonical queries and hashes are retained through relative references to sibling
corpora. Transfer these corpora with this view. The builder validated 356 unique
referenced files (539,521,051 bytes). `builder.py` freezes the selection code;
`scripts/build_hard_development.py` rebuilds from the recorded complete runs.

`research/hard-development-v2-plan.json` registers 276 runs: focused Rust,
symbolic Rust, VerifyPN default and SMPT full portable, each at 60 seconds on
Linux CPU8 with instruction counts and a 2 GiB memory limit. Parsing and
preprocessing are timed; independent native validation is separately bounded.
The frozen Rust capacity-direct binary excludes the ongoing sparse token-flow
optimization. One repetition qualifies coverage, not precise speedup.

This plan supersedes the unexecuted 26-query v1 plan; v1 artifacts remain intact.
All eight reserved MCC families remain excluded from tuning. Longer-budget
results must distinguish timeouts, resource limits and setup failures before
promoting cases to a further 300-second qualification.

Completed local two-second screening (`results/relevant-finite-hard-v2`, 207
rows) solved 0/69 with the finite-control engine, 0/69 with its relevance wrapper,
and 3/69 with the focused portfolio. All three answers passed independent checks.
This is separate from the ongoing 60-second Linux qualification and does not
establish difficulty for competitors. See
`research/relevant-finite-hard-v2.md` for the audit and limitations.
