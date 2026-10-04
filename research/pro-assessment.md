# Assessment of Pro recommendations — 2026-09-26

Pro recommends certified arithmetic refutation, target-sensitive support refinement, and exact word acceleration; it recommends testing KReach on residual cases before implementing full KLMST. These remain proposals, not measured improvements to the Rust solver. Pro could inspect upstream SMPT and the artifact listing but could not download the pinned artifact.

## Independently checked against this workspace

The archived SMPT really does strengthen its state equation with read-arc constraints and marked traps (`vendor/SMPT/smpt/checkers/statequation.py`, lines 244–260). The supplied certificate patch is preserved at `vendor/SerializabilityChecker/scripts/SMPT_certificate_fix_v2.patch`; we have not applied additional changes to baseline source.

Our initial three-repeat comparison remains 202/218 solved by Rust versus 209/218 by SMPT, with 201 commonly solved queries, eight solved only by SMPT, and one only by Rust. No definitive verdicts disagree. The 17.89x median common-solved speedup includes process startup and parsing and does not establish end-to-end performance.

A new **diagnostic Z3 oracle experiment**, using the normalized exact query matrices, classified the eight SMPT-only queries. This does not add Z3 to the native solver. Reproduce with `vendor/venv/bin/python research/classify_gaps.py`; results are in `gap-classification.json`.

| Query | Rational state equation | Integer state equation | Local implication |
|---|---|---|---|
| d1_disjunct_0 | feasible | infeasible | Integer reasoning is sufficient; rational reasoning cannot refute it. |
| d3_disjunct_1 | feasible | infeasible | Same. |
| d4_disjunct_0 | feasible | infeasible | Same. |
| d4_disjunct_1 | feasible | infeasible | Same. |
| d4_disjunct_2 | infeasible | infeasible | Native elimination hits its row limit. |
| d4_disjunct_3 | infeasible | infeasible | Native elimination hits its row limit. |
| e1_disjunct_0 | feasible | feasible | Additional reachability constraints are needed. |
| e7_disjunct_0 | feasible | feasible | Additional reachability constraints are needed. |

For both d4 row-limit cases, direct native `--method state-equation --seconds 2` runs returned `elimination row limit` in about 0.05 seconds. Thus increasing time alone does not repair them.

The archived comparison logs for e1 and e7 show SMPT adding the marked-trap condition that the pending local-state place or `G___` remains positive, followed by an unsatisfiable result. This directly supports trying trap constraints on these two cases. The diagnostic integer classification also corrects the earlier broad attribution of the entire gap to read-arc/trap strengthening: four cases require integrality, and two are an elimination resource problem.

The 12-query ablation recorded no solved cases for greedy best-first, three reachable cases for BFS, seven unreachable cases for the state equation, and ten solved by the portfolio. That small selected ablation is not a universal ranking, but it provides no evidence that the current greedy heuristic contributes useful coverage. Its ordering can keep exploring low-violation regions while delaying paths requiring larger temporary violations.

## Recommended next experiments

1. Address the measured gap: integer split/congruence certificates for the four integer-only cases; more efficient rational feasibility or controlled elimination for the two row-limit cases; certified marked-trap constraints for e1/e7.
2. Add target-sensitive support refinement if residual negatives remain. Pro's forward/backward argument is plausible and clearly scoped to each target; it still needs a precise implementation and adversarial tests. The endpoint support must overapproximate every feasible endpoint, not one selected LP model.
3. Improve positive search with count guidance and exact repeated-word summaries, focusing on c1/e2/e4. Pro's repeated-word enabling condition follows by checking the most demanding repetition coordinatewise; a compressed-witness checker and boundary tests are still needed.
4. Measure end-to-end proof generation and validation on c2/g7. Their paper timing gaps and our frontend timeouts motivate this, but neither establishes that proof validation alone is responsible. The solver-only comparison intentionally excludes that phase.
5. Benchmark KReach through an independently checked linear-target-to-point-target adapter before committing to a full KLMST implementation. Pro reports that KReach's arithmetic uses SMT, so it is a useful algorithmic baseline rather than an SMT-free implementation.

No solver changes were made during this assessment. All initial benchmark results remain associated with their recorded source and binary hashes.
