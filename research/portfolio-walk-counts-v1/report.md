# Count planning inside the walk portfolio

The experimental `portfolio-walk-counts` method solves the complete original
RefineWMG-PT-100101 RC11 property with a 29,381-firing witness on branch 0.
The bounded independent Python validator translates the original PNML/XML,
checks agreement with every canonical branch, and replays the witness. The
matched existing walk portfolio exceeded the outer 5.3-second limit and returned
no answer; its empty output and termination evidence are preserved as unknown.

The candidate keeps the existing walk warmup, then runs the remaining-state
count planner for at most one fifth of remaining time, capped at 250 ms, before
the existing relevant/causal/batched fallback. The existing sparse-construction
work guard limits eligibility. Only a reachable count result is accepted.
Original-input capacity and buffer preprocessing remain enabled as for walk.
The default method and existing walk method are unchanged.

All eleven targeted tests pass, including a 9,000-firing count-stage witness,
positive walk warmup, independently checked negative fallback and invalid restart
configuration. Targeted Clippy and release build pass. Frozen source/binary,
original-input plan, raw output, validator receipts and artifact audit are in this
folder. Candidate observed wall time was 0.173 seconds in this single local probe;
this is not a stable timing estimate or comparison with Linux competitor results.

A separate complete 192-property canonical-input development comparison completed under `research/portfolio-counts-development-v1`, with frozen candidate,
walk and existing-portfolio binaries. All 576 rows passed audit: candidate and walk solved the same 186/192 properties,
with no coverage gains or losses.
This integration is an engineering improvement; a coherent novel algorithm and
substantial general performance advantage remain unestablished.
