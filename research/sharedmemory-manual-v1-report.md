# SharedMemory survivors: checked manual answers

Both original SharedMemory-PT-000200 properties are false. The candidate generator
and all checking completed successfully in session48518. Evidence is retained in
`results/manual-sharedmemory-v1/verification.json`, with original-input and runner
hashes, bounded validation requests/responses, per-branch Rust verification logs,
and the manual certificates. These are manual diagnostic answers, not automatic
solver coverage or discovery timings.

RC03 (AG): the200Req_Ext_Acc transitions move all initially Active tokens into
Queue places. The resulting marking satisfies canonical counterexample branch3.
Rust replays the trace; the independent Python checker separately translates the
original PNML/XML, compares every canonical branch and replays the200steps.
The other three branches are explicitly left Unknown; one checked counterexample
suffices to falsify AG.

RC04 (EF): in each of its two target branches, row0requires sum(Active)>=2and
row2requires Ext_Bus>=sum(Active), hence Ext_Bus>=2. Every original transition
preserves Ext_Bus+sum(Ext_Mem_Acc), initially1. Nonnegativity gives Ext_Bus<=1,
a contradiction. The stored sparse Farkas certificate combines these two target
rows with every Ext_Mem_Acc nonnegativity row. Both Rust and independent Python
checkers accept both branches. Python also re-translates and reconciles the exact
original PNML/XML and property polarity.

All checks used separate60s and sampled2GiB limits. The original-property summary
uses zero timing fields solely to satisfy the existing validation schema; they
are not solver measurements. No new proof rule or model-specific production
solver code was introduced.

This diagnosis changes the interpretation of the old four300s survivors: two
TokenRing negatives now have automatic phase-pair proofs; the two SharedMemory
properties now have manual checked answers, but remain automatic-solver gaps.
None of these cases demonstrates intrinsic reachability hardness. The benchmark
set retains them because scalable parsing, proof discovery and witness discovery
are practical requirements. Old runs, failures and denominators remain intact.

General opportunities suggested by the manual constructions are target-guided
incremental witness search and combining target constraints before capacity
refutation. They remain proposals pending implementation and matched evaluation.

Subsequent full-cohort audit: the Linux walk portfolio independently checks RC03
automatically (branch0negative, branch1positive633step witness). Thus RC03 is no
longer a current automatic-solver gap. The manual branch3witness remains separate
evidence. RC04 remains Unknown in that5s native portfolio run.
