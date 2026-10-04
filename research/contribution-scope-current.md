# Contribution scope

User clarification, 2026-09-28: **a general Petri-net reachability solver,
with serializability as an application**.

Prioritize mechanisms applicable to general weighted nets and exact reachability
queries. Raw automaton-target serializability remains a separate application
track with its own semantics, checker and denominators. Application-only gains
cannot establish general solver superiority.

The next empirical decision should use the complete frozen ordinary comparison
in `application-walk-full-v1/plan.json`, preserving both native baselines,
VerifyPN, SMPT, full parents and all failures. No claim of novelty, publication
readiness, broad competitive superiority or stable timing follows from a
selected witness-search pilot or the corrected raw-work accounting.

User priority, 2026-09-28: **coverage and speed first**. Independently checkable
proofs remain a correctness requirement and useful engineering support. Do not
make certificate representation or proof compression the main research objective
unless it produces measured coverage or end-to-end cost benefits. Prioritize
automatic discovery and matched empirical comparisons before optional proof-path
or dependency-cache sophistication.
