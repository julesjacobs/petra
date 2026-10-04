# Backward relevance in delete-relaxed witness search

The previous engine rebuilt a delete-relaxed plan over every transition at
each expanded marking. Independent modules therefore cost time even when
they could not affect the property. The new engine statically retains all
transitions with nonzero incidence on a target-support place, then closes
this set under positive-incidence producers of each retained input guard.
Facts and actions are compacted once; witness edges retain original IDs.

Search markings retain target-support places and all retained input places;
other coordinates are projected away. These coordinates determine exact
enabling and target evaluation for the retained transitions. For ordinary nets over mathematical natural numbers it preserves
existential reachability of the target: delete every omitted transition from
a successful firing sequence. On every retained guard place, an omitted
transition has nonpositive incidence, so deleting it can only increase the
available marking. On target-support places, omitted incidence is zero.
Inductively the remaining sequence is enabled and has the same target
values, including signed and equality targets. Retained original transitions
themselves give the converse. The implementation still reports only replayed
positive witnesses; exhaustion, overflow and limits remain unknown.

An untimed structural inspection of the existing development cases gives:

| Query | Retained/original actions | Required/original places |
|---|---:|---:|
| JoinFreeModules-PT-1000 RC01 | 16/8001 | 10/5001 |
| DLCflexbar-PT-7b RC00 | 55507/55507 | 35101/35101 |
| AutoFlight-PT-48b RC01 | 3936/3936 | 3950/3950 |

These are graph sizes, not timing evidence. No expected benefit from this
reduction is claimed on the latter two properties. Original PNML parsing,
other portfolio phases and original-net witness checking remain unchanged.
