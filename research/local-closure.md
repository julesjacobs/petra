# Necessary local targets

`local-closure` proves unreachability using a threshold closure over selected places. For a target inequality a·m>=b and selected coordinates S, retain the inequality only if all omitted coefficients are nonpositive. Nonnegative markings imply that replacing those omitted terms by zero increases the left-hand side, so the resulting local inequality is a necessary condition for the original target. Equality constraints supply two directions; a direction requiring an unrepresentable i64 negation is omitted. Discarding a direction weakens the target and is safe for refutation.

Project transitions onto S, dropping foreign guards. Every concrete run induces a projected run, possibly with stuttering steps. A checked projected threshold closure excluding the necessary local target therefore proves original unreachability. Positive projected outcomes are never accepted. The certificate contains only selected coordinates and the threshold closure; Rust and an independent Python implementation reconstruct the projection and necessary target from the original net.

Discovery partitions the transition-support graph after ignoring transitions with identical input/output multisets. This discovers small candidate projections; the proof rule itself does not assume component independence. It is a general projection method, with no hard-coded benchmark names, place identifiers, bounds or witness traces.

On the development case JoinFreeModules0005 RC09, the selected places p16..p20 have 103 reachable states. Among these, p19>=3 and p20>=3 hold only at (0,0,0,3,5), where p17=0. The original target also requires p17-p12>=1, hence necessarily p17>=1. The exported abstract closure excludes that local target. `research/joinfree-local-closure.json` contains the automatically generated certificate; `research/joinfree-local-diagnostic.json` records the earlier manual enumeration. Debug solve time is diagnostic only and is not a competitive timing result.

The experimental `portfolio-local` keeps the causal arithmetic prefix, then gives local closure 5% of the remaining budget capped at 100ms, then uses the relaxed witness search and existing fallback schedule. Previous frozen portfolios remain available. Full comparisons must measure scheduling regressions instead of taking the union of standalone results.

This is an instance of projection and finite abstraction. Neither novelty nor publication readiness follows from solving the diagnostic.
