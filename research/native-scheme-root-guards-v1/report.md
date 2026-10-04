# Exact root guards before native arithmetic

The complete v2 screen shows that 113 unresolved cycle-search branches never reach
multiword schemes, spending 27,313 arithmetic attempts on 25,656 impossible root
prefixes. The new candidate computes each root word's exact hurdle and compares
it with the initial marking before issuing an integer query. Disabled roots are
rejected without consuming an arithmetic scheme attempt. Enabled roots admit one
execution, so their target-free prefix query is skipped. Full target queries and
non-root prefix feasibility checks retain the previous exact semantics.

Root scans/refutations are recorded separately. They remain subject to vocabulary
and whole-query limits; the 256-attempt bound now limits arithmetic candidates
rather than known-disabled root words. No executable scheme is removed. Bounded
failure still returns unknown. This is a standard enabling check motivated by the
measured waste, not a novelty claim.

Four unit tests pass, including a disabled leading transition followed by a witness
within one arithmetic attempt, prefix pruning, retained unknown prefixes, automatic
compound acceleration and budget cases. Four production-CLI mechanism checks with
independent positive checking pass. Targeted Clippy/release build pass. Ten frozen
capability cases pass. The 960-row v3 development comparison is running; there is
no performance result for this candidate yet.
