# Automatic native scheme search

Implemented src/scheme_search.rs and examples/native_scheme_search.rs, using the
native exact fixed-scheme solver. The method discovers singleton/cycle words,
enumerates schemes breadth-first with lazy child generation, and merges adjacent
identical words by omitting that redundant choice. Each candidate gets a bounded
native integer-arithmetic target query. If it fails and extension is possible, a
second query removes the target and asks whether any positive repetition counts
can execute the prefix. Only exact prefix infeasibility prunes extensions;
arithmetic unknown retains them. All accepted compressed witnesses are checked.

The search is bounded by depth, attempted schemes, agenda entries, construction
entries, per-query arithmetic time/rows/nodes, discovery work and whole-query time.
No bounded exhaustion or pruning result is exposed as global unreachability.
There is no external SMT invocation in either native search configuration.
Discovery, target-query and prefix-query times are recorded separately.

The first version uses deterministic breadth-first scheme enumeration and rebuilds
arithmetic systems per candidate. These may be expensive. This is an experimental
complete pipeline for measuring native scheme search, not a competitive algorithm
claim or new default. No novelty is claimed for acceleration or enumeration.

Three unit tests cover automatic trillion-step loop discovery, singleton bounded
failure, exact prefix pruning, preservation under arithmetic resource failure,
initial-marking success and budget exhaustion. Four end-to-end cases pass, with
positive witnesses checked using the production independent-checker CLI. Targeted
Clippy and the release build pass; vendored varisat warnings remain.

The initial benchmark smoke failed because the native CLI omitted the final
marking required by the checker. Its source/binary/plan/logs remain preserved in
results/solver-native-scheme-development-v1 and
research/native-scheme-development-v1. No benchmark rows were launched for v1.
The corrected CLI includes the independently recomputed marking; tests now exercise
the checker CLI contract. The corrected v2 freeze passes all ten capability cases.

Full development comparison is running under native-scheme-development-v2:
192 properties, native-singleton/native-cycles/frozen SMT cycles/two native controls,
one second per property across canonical branches, separately bounded independent
checking. Native scheme limits are depth4,256schemes,200kentries,4096arithmetic
rows/nodes,50ms per arithmetic query; SMT retains its frozen depth16 configuration.
Whole-property time and outer sampled2GiB limits match. This compares algorithms
with their registered internal bounds, not identical bounded path languages.
One shared-Mac development repeat cannot establish stable timing or superiority.
