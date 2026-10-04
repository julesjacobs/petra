# Independent mathematical and implementation review

Reviewed `v2/diagnostic.py`, `v2/test_diagnostic.py`, and `theory.md` without
editing the diagnostic implementation. No soundness blocker was found in the
reviewed v2 closure checker or antichain exploration.

The exploration preserves incomparable remaining-count vectors, replaces only
vectors dominated at the exact same marking, skips stale worklist entries, and
reconstructs the final frontier from the retained representatives. Exact
remaining-vector deduplication is compatible with this replacement: a removed
vector remains dominated through any later chain of replacements. Stored parent
records still describe actual executable prefixes for positive replay.

The v2 checker independently checks nonnegative bounded counts, exact markings,
the state equation for each retained pair, initial inclusion, target exclusion,
and every enabled original transition's exhausted-budget or dominated-successor
obligation. These are the sufficient conditions proved in `theory.md`. Additional
coverage of original prefixes and the frontier-subset comparison are useful
differential checks. Incomplete exploration or checking remains incomplete.

The original v1 checker omitted explicit initialization and representation
checks and used Python assertions. The implementation author preserved v1 and
created v2 with explicit `require` checks. The v2 tests cover omitted initial
states, malformed count vectors, incorrect markings and state equations,
missing successors/frontier entries, and the 1-safe cycle separation. Assertions
in `unittest` methods remain active under Python optimization; certificate
obligations no longer depend on language-level `assert`.

The input is a pinned, previously validated canonical net, not arbitrary new
JSON. This diagnostic is not a production certificate format, a solver
comparison, or an independent implementation of the complete search algorithm.
Its closure checker uses separate direct integer operations and does not trust
the antichain search's dominance decisions.

The completed v2 replay reports 368 complete pairs and 130,940 prefixes, with a
distinct marking for every prefix within each count box. All 368 checks pass;
none is incomplete. The reviewer independently verified the result's plan and
event hashes and all four pinned source hashes. Same-marking dominance removes
no recorded prefix and changes no frontier. This result rejects the proposed
mechanism for these recorded boxes; the synthetic separation is not evidence of
a benefit on the survivor inputs.
