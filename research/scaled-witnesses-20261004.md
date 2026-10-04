# Witness search from a divided initial marking

Let the initial marking be `m0 = k a` for an integer `k > 1`. Keep every transition input and output arc unchanged. If the ordinary transition word `w` takes `a` to `b`, monotonicity makes the concatenation of `k` copies of `w` executable from `k a`, ending at `k b`.

After `j` copies the marking is `(k-j) a + j b`. To fire the next copy, use the enabling of `w` from `a` with the nonnegative context `(k-j-1) a + j b`. This argument preserves weighted input guards and read arcs: only the initial marking changes, never the transition relation.

For a signed target row `c m >= d`, search the reduced net for `c b >= ceil(d/k)`. Multiplying by positive `k` gives the original inequality. For equality, choose `k` dividing `d` as well as all initial coordinates, then require `c b = d/k`. Signed bounds use mathematical ceiling, including negative values. Compute the common divisor with unsigned magnitudes so `i64::MIN` is represented exactly.

The implementation in `src/scaled.rs` only transfers positive results. Failure to reach the reduced target cannot refute the original problem: copies can follow different words or interact. In particular, a transition requiring two tokens may be usable from the original marking and disabled from one copy. Every expanded witness is replayed on the original net and complete target, with a one-million-transition trace cap and the original deadline.

`scaled-relaxed` uses batched relaxed search on the divided initial marking. `scaled-walk` uses guided walk. Both remain separately selectable for diagnostics. The integrated portfolio tries divided-marking guided search and original guided search before reductions, then divided-marking relaxed search and the prior fallbacks. Each stage receives only part of the remaining deadline. The arithmetic reduction and lifting argument are standard consequences of Petri-net monotonicity and additive composition; no novelty claim is made.

Tests cover signed rounding, equality divisibility, read guards, nondivisible arcs, exact original replay, and a case where a reduced refutation must return unknown on the original problem. Timed results and source hashes belong to their individual diagnostic campaigns, not this mutable design note.


In the third selected diagnostic, divided-marking guided walks solved 25 of the 31 grouped-only survivors, versus 14 for original guided walks. Their union was 26, all independently checked. The integrated candidate reproduced all 26 in its own separate survivor screen. These diagnostic counts do not establish whole-cohort coverage; the final comparison records every original property and two complete repeats.
