# Capacity combinations close SharedMemory RC04 automatically

The opt-in general `capacity` method proves SharedMemory-200 RC04 unreachable
in 0.625s solver wall time, with a separate 4.027s independent check. Both
branches use `checked-capacity-combined` and ordinary sparse Farkas certificates.
This reproduces the earlier manual invariant argument automatically from net
incidence and target constraints. No model-name matching is used. The two proofs
occupy 933,114 bytes in compact JSON; checker cost remains significant.

All eight native-walk Unknowns from the audited Linux parent were retained.
The local pilot contains all 16 planned rows at 5s and sampled 2GiB, with separate
60s/2GiB validation. Capacity solves 1/8; the same-binary walk portfolio solves
1/8, a different query (NoC3x3-8B RC12, reachable, 244-step checked witness from
causal state-equation search). Both methods leave the other six unknown.
The parent remains 656 slots, 640 imports and 16 unavailable imports.

The NoC answer is a local rerun of an existing portfolio, not evidence that the
capacity method improved positive search. Neither result updates the historical
Linux coverage count. Single-row capacity discovery already refutes some branches
of RC01 but cannot settle its whole disjunction. All unsuccessful rows are kept.

The pilot exited 0 and passed saved-artifact reconciliation of all 16 rows,
frozen solver source, runner closure, original input translations, validation
requests/responses, branch coverage and resource failures. The audit reconciles
previously executed independent checks rather than executing them again.

Capacity remains opt-in. Pairwise target-row addition is a limited existing
linear proof technique; this result establishes neither novelty nor broad
superiority. Full-cohort cost and regression measurement is required before
portfolio promotion. Development tests, formatting and Clippy passed before
freezing the binary. See `capacity-combinations-gap-v1-audit.json`, its plan,
execution/terminal receipts, and `capacity-combinations-v1-design.md`.
