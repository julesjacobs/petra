Review scope: src/main.rs portfolio-walk (100ms/min10% walk then legacy batched,
same PNML capacities and optional wrappers); src/raw_negative.rs exact sparse
interning via existing StoredMarking, fixed-dimension pool, dense transient
expansion and unchanged dense proof extraction; tests added/updated. No algorithm
claim beyond sound positive witness and same raw certificate semantics. Tests214
library plus7rawCLI/3diagnostics+1ignored/2schema/6walkCLI passed; Clippy passed with
existing vendor warnings. Stored-marking intern cost now8*dimension vs2*before,
so work-capped outcomes are not a pure storage ablation. Current freeze session18223
may still be building; no build/format/solver work in a read-only review. Check
immutable keys, dimensions, weighted updates, deadline handling and fallback
proof/witness consistency. Existing shared witness checker is non-interruptible;
outer enforcement remains necessary. No reserved or Linux work.
