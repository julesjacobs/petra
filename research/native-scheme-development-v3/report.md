# Root-guard native search comparison

All 960 rows pass audit, with no disagreements or validation failures. Native
singleton and cycle search reproduce exactly their previous positive sets: 61 and
60 of192. SMT cycle search remains69, native walk101reachable+85unreachable.
The unchanged frozen native control loses one near-budget negative answer,
SharedMemory-PT-000020__RC08, returning98reachable+84unreachable. This illustrates
why one shared-host repeat cannot establish stable timing.

Cheap root guards reject130283singleton and149324cycle word proposals in completed
branches. Arithmetic attempts fall only from58068to56883 and60155to59255, because
the search reaches other candidates. Prefix refutations remain44825and46564.
No additional property is solved. The representation/pruning improvement therefore
does not remedy the main coverage problem in uninformed breadth-first enumeration.
Further small guard optimizations should not be assumed to produce a competitive
method. The next architectural question is how to select/refine useful schemes
using target or feasible-trace information instead of enumerating the vocabulary.

Artifacts: audit.json,diagnostics.json,paired-comparison.json; complete previousv2
and newv3snapshots preserved. This is development evidence with canonical JSON,
one-second property budgets, sampled2GiB limits and independently checked positive
answers. It provides no novelty, superiority or publication-readiness conclusion.
The default native portfolio is unchanged.
