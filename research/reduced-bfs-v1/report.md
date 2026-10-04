# Checked repeated reductions followed by BFS

Added optional CLI method `reduced-bfs`. It alternates existing checked buffer
agglomeration and backward relevance for at most four rounds, stopping when neither
changes the net. Preparation uses at most one fifth of the time budget, capped at
200 ms; completed sound reductions are retained if further preparation runs out of
resources. BFS receives 90% of remaining time, reserving the rest for witness lifting
and proof wrapping. Its state budget is capped at 200,000, matching independent
finite-closure validation. Exhausted preparation/search/lifting yields unknown.

Positive witnesses are lifted through every reduction in reverse order. Negative
answers contain nested existing reduction proofs ending in `finite-closure-v1`,
which records the reachable-state count. Both the Rust verifier and independent
Python verifier re-explore that finite closure and check the count. Verification
cost scales with the reduced reachable state space; the proof does not store an
explicit invariant state set. The existing methods and default remain unchanged.

Evidence for repeated reductions comes from the complete six-case Cloud ablation:
zero/one round hit 200,000 states on both branches, while two rounds exhaust 101,476
and 74,840 states. This is specific to that resource bound; larger bounds for one
round were not tested. No duplicate-transition removal is used by this solver.

Thirteen Rust integration tests pass, including 1,176 weighted conservative-net
comparisons against direct BFS, positive macro-trace lifting, nested negative proof
checks in Rust/Python, malformed closure-bound rejection, and budget exhaustion.
Twenty-five existing Python reduction-checker tests, targeted Clippy and release
build also pass. Preserved logs are in this folder.

On the complete original CloudReconfiguration-PT-311 RC06 property, with five seconds
and buffer preprocessing enabled for both methods, the count portfolio times out;
reduced-bfs proves both branches unreachable. The bounded original-input validator
independently retranslates PNML/XML, checks canonical branch agreement, reconstructs
the reductions and exhausts both reduced closures. Artifact audit passes. Observed
solver wall time was 0.654 seconds and independent validation 14.669 seconds in one
local diagnostic. No stable timing or matched Linux comparison is claimed.

Source and binary snapshot, original-input plan/results and validation receipts are
preserved under this folder. The complete 192-property canonical-input comparison
completed under `research/reduced-bfs-development-v1`, with the new method and three
frozen native controls. Eight capability cases passed before launch. The method solved 150/192, adding three checked positives but losing 39 solved
properties against the count portfolio. It remains an optional component; a bounded
portfolio integration is being tested separately.

This composes established reductions and explicit search. It is a verified
engineering improvement on one original property, without an algorithmic novelty,
publication-readiness or general superiority claim. Next inspect the full cohort
and design portfolio allocation from that evidence, preserving the frozen controls.
