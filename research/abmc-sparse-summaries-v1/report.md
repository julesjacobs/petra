# Sparse accelerated-BMC summaries

The previous development screen hit the dense words×places summary cap on 48
properties. The candidate constructs exact hurdle/effect summaries in ordered maps
by visiting original transition arcs. It retains read guards even when the total
effect cancels. A per-place index of nonzero word effects replaces the encoder's
places×words scan. The dense compressed-witness checker remains separate.

The driver bounds sparse construction using vocabulary size, total word length,
and twice the visited arc count. This conservatively bounds stored hurdle/effect
entries and visits; ordered-map operations additionally have logarithmic cost.
The existing depth-dependent encoding-cell, output-byte, whole-query deadline,
and outer process-tree memory limits remain. Direct library callers have the same
unbounded interface as before; the production experiment uses the bounded driver.

Verification: 5,832 three-transition words compared placewise against dense
composition, including weighted/read arcs, cancellation, sparse untouched places,
and effects beyond 64 bits; a separate cancellation/read-guard regression; 12
integration tests; 66 real Z3 semantic queries, with all 51 satisfiable models
independently checked; three-mode discovery ablation; six driver cases. A 500-place,
500-transition regression solves despite the old 250,000-cell dense footprint,
and rejects two smaller budgets as summary/encoding limits. Targeted Clippy and
formatting pass; existing vendored varisat warnings remain.

This is implementation and semantic evidence, not a demonstrated competitive
improvement. The full 192-property, five-configuration screen is being repeated
under a separate frozen plan in research/abmc-mcc-sparse-v1. Historical evidence
is preserved. No default portfolio change.
