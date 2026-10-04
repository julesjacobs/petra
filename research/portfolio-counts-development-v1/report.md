# Walk portfolio with a count-planning stage

The candidate and frozen walk portfolio solved exactly the same 186 of 192
properties: 101 reachable, 85 unreachable and 6 unknown. Neither positive nor
negative coverage changed. The frozen existing portfolio solved 183 (98 reachable,
85 unreachable); the three walk gains were TokenRing-PT-015 RC08, RC14 and RC15.

All 576 rows passed the artifact audit with zero warnings or answer disagreements.
The complete canonical-input development cohort used one second per property
shared across branches, sampled 2 GiB limits and bounded independent answer checks
outside solver timing. Six capability cases passed before launch. The candidate
binary and sources and both baseline binaries were frozen before execution.

This is one shared-Mac repeat. It supports no observed coverage regression in this
cohort, not stable speed or general superiority. The separately checked original
RefineWMG-PT-100101 RC11 gain is outside this cohort; combining those observations
does not replace a complete harder original-input comparison.

Plan SHA256: `55930816fd6efbb35535d5a79d0ed08a56f06b7e90fd676a437d942107aaaf33`.
Frozen artifacts: `results/solver-portfolio-counts-development-v1`.
Raw rows: `results/portfolio-counts-development-v1/runs.jsonl`.
See `audit.json` and `diagnostics.json` for identities, checks and resource results.

The next experiment should compare the frozen candidate on the complete harder
176-property original-input Linux cohort with matched budgets and strong frozen
controls. Default promotion and a research contribution remain unestablished.
