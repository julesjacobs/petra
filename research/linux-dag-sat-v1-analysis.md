# First acyclic-control SAT comparison

The complete 34-query Linux development pilot solves 22 with the new symbolic
portfolio (15 positives, 7 negatives), 8 with the frozen Rust predecessor,
and 6 with VerifyPN. The candidate gains 14 answers and loses none from the
predecessor. All candidate positives and negatives passed the independent
Python checker. There are no definitive disagreements.

These are the small synthetic Boolean-consistency nets, whose source formulas
are easy for a dedicated SAT solver. This demonstrates progress on a known
representation weakness, not general application superiority or publication
novelty. The prior four-property application diagnostic remains a material
negative result: no stable native coverage gain and VerifyPN solves all four.

All 136 scheduled rows completed with original PNML/XML, a five-second solve
deadline, CPU 8, enforced 2 GiB and user-space instruction counters. Native
checking is separately bounded. SMPT failed on all 34 original property files
because it requires a description child before the formula; its errors are
not solver defeats. The shell exit status is 1 because those errors are
preserved. The matched comparison against SMPT is therefore still incomplete.

The new `boolean-consistency-v2` corpus adds only description metadata. Every
PNML net, source CNF, canonical JSON branch, and translated net hash matches
v1; source formulas are unchanged. This compatibility change and the later
control-derived encoding will be measured in a separate preserved run.

Full artifacts: `results/linux-dag-sat-v1`.
Machine-readable counts and exact gains: `research/linux-dag-sat-v1-analysis.json`.
