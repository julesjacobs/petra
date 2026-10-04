# Raw control storage and work accounting review

Read-only source comparison: current `src/raw_negative.rs`, `src/marking.rs`,
`src/successors.rs`, and `src/raw_negative.rs` in
`results/solver-raw-balanced-v1/source.tar.gz`. No builds, solver runs, or Linux
access. Findings below are static; the cause of n5 coverage loss still requires
the matched phase diagnostic.

## Verified changes

Let d be the control dimension and k the number of nonzero values. The archived
dense interner charges 2 max(d,1) for each intern attempt. The current interner
charges 8 max(d,1), including attempts that find an existing marking. Thus the
accounting alone adds 6 max(d,1) per attempted successor (and initial marking).
The actual reduction in explored nodes depends on other charges and deadlines.

`StoredMarking::new` scans all d values to count nonzeros, then scans them again
to construct either representation. Its sparse payload has 2k machine words;
the canonical selection rule ensures 2k<d. Dense payload has d words. The 8d
charge ignores this difference. Hash metadata adds a constant amount.

Expansion now restores a dense scratch marking per game node; previously it
cloned an Rc. Every enabled successor still allocates/copies d words before
compression. Even duplicate markings incur both compression scans and a
temporary allocation. `identities` also hashes the marking payload for each
transfer because `Rc<T>` hashes T, not its pointer. Transition indexing scans
anchor places, not the complete dense marking.

## Smallest recommended accounting change

Define and document work as logical coordinate/encoded-word operations, not
CPU instructions or a worst-case runtime bound. Keep the deadline as the time
limit. Neither the old 2d nor current 8d bounds actual HashSet work: collisions
and table growth are not instrumented.

Precharge 2 max(d,1) before conversion. After conversion, let h be encoded
payload words plus constant metadata. Charge 2h before lookup (hash plus an
equality allowance), and another 2h before insertion only on a miss. This
retains conversion charges, scales lookup to the representation, and charges
miss work only when performed. Use checked/saturating arithmetic, and perform
no insertion after a failed charge. It is a declared logical allowance, not
an exact count of hash-table operations. Count conversion words, encoded
lookup words, and miss insertion words separately in diagnostics.

For a strictly instrumented comparison budget, a larger redesign would need
explicit hash buckets and budgeted equality comparisons (including collision
candidates and growth). Simply changing 8d to 2d would conceal the new scans.
Keep existing non-interner charges unchanged in the first diagnostic patch,
so its effect can be isolated.

## Small representation improvements, separately measurable

1. Return an exact, stable integer control ID from the interner and key game
   identities by `(control_id, component)`. Keep canonical markings in a vector
   or handle for expansion and certificate extraction. Full marking equality
   in the interner establishes IDs; hash collisions must never establish
   equality. This eliminates repeated payload hashing per transfer and permits
   constant logical charges for game identity lookup.
2. If transfers are empty, record the losing edge and stop without constructing
   or interning its unused successor. Currently that work is discarded.
3. Avoid zero-initializing certificate vectors and then zero-filling them again
   through `write_to`; provide a dense export that clones Dense or initializes
   Sparse once. Certificate format and checker need not change.

Eliminating successor dense scans entirely requires a larger change: sparse
successor updates or maintaining nonzero positions while firing. Do not fold
that into an accounting repair. An owned-vector constructor can avoid the
second dense copy for Dense, but sparse construction still requires scanning
or maintaining nonzero positions. Preserve the canonical threshold and exact
values/positions throughout.

Any resulting coverage gain under the same numeric logical-work cap is not
by itself a speedup. Compare matched wall time/instructions separately and
retain independent certificate checking.
