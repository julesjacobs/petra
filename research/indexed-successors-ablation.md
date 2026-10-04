# Indexed successor candidates

Each non-source transition is assigned one preset place as its anchor. A transition can fire only if its anchor has enough tokens, so the search collects candidates from satisfied anchors plus all source transitions. It still checks each complete weighted preset with `Problem::fire`. Candidate IDs are unique and sorted in original transition order, preserving exploration and overflow order apart from resource deadlines. The anchor is chosen deterministically from the least-read preset place.

The same incidence pass identifies active places in linear arc time, replacing guided search's place-by-transition scan. Guided and raw direct search use the index; there is no new proof rule or acceptance condition.

Verification: 214 Rust tests and all-target clippy passed. New differential coverage compares all enabled successors and overflow outcomes on 8,192 weighted markings, plus a 1,000-transition sparse fixture. Read-only review found no correctness blocker. Dense candidate sorting and rebuilding the index across potential attempts remain possible overheads; construction and sorting are charged to the surrounding timeout but are not internally interruptible.

Frozen source/binary: `results/solver-indexed-successors-v1`. All 36 rows of the two-repetition raw ablation completed under the same 10-second/2GiB envelope. Coverage remains five verified positives in both repetitions, seven valid unresolved queries, and six unavailable exports. The counter's mean observed time falls from 0.8442 to 0.6236 seconds; other common-case changes are smaller or mixed. Largest-monitor failures are now two memory limits, versus one memory limit and one timeout before. There is no additional coverage or broad performance claim.

Data: `research/raw-indexed-comparison.json`. Next, compact exact markings and projection keys to address storage per explored state; measure that as a separate variant.
