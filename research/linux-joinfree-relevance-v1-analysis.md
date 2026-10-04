# Full JoinFree development-family comparison

The relevance reduction increases checked coverage from **35/48 to 46/48**,
with eleven gains and no losses in this matched pilot. VerifyPN also solves
46/48. The two sets differ: each solver handles two queries the other leaves
unresolved. Standalone sliced search also solves the same 46 as our portfolio.

| Method | Checked/tool-reported answers | Unknown |
|---|---:|---:|
| Frozen predecessor, portfolio-focused | 35 | 13 |
| Relevance reduction, portfolio-focused | 46 | 2 |
| Relevance reduction, relaxed-focused | 46 | 2 |
| VerifyPN default | 46 | 2 |

All native answers have independently replayed original-net witnesses;
VerifyPN answers are tool-reported. Some aggregate positives follow unknown
earlier branches; one checked positive branch suffices for reachability.
There are no definitive disagreements. All 192 planned rows completed.

Among the 44 properties solved by both the new portfolio and VerifyPN, the
median native/VerifyPN wall ratio is 1.38 and the geometric mean is 1.11;
the median instruction ratio is 1.71. The portfolio therefore does not show
a general speed advantage. Standalone sliced search on those same 44 has
median wall ratio 0.73, geometric mean 0.59, and median instruction ratio 0.47.
These conditional timing summaries exclude unresolved queries; the full
48-property counts remain the primary comparison. Earlier portfolio phases
are now a material overhead on this family.

The native-only queries are JoinFreeModules-PT-2000 RC15 and
JoinFreeModules-PT-5000 RC00. The VerifyPN-only queries are
JoinFreeModules-PT-1000 RC14 and JoinFreeModules-PT-5000 RC04.

This is one repetition of a development-family experiment, selected after
diagnosing that family. It is not independent generalization evidence.
CPU 8, enforced 2 GiB, perf counters, original PNML/XML parsing inside a 5s
deadline; native checking separately bounded. The method order is shuffled.
Plan: research/linux-joinfree-relevance-v1-plan.json. Full artifacts:
results/linux-joinfree-relevance-v1. Audited per-query results and exact gains:
research/linux-joinfree-relevance-v1-analysis.json.

The full 368-property stress regression comparison is a separate experiment
under research/linux-stress-relevance-v1-plan.json. Its running matrix must
finish before reporting full-corpus coverage.
