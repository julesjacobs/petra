# Higher logical-work diagnostic: no new native-gap coverage

All 20 outcome-selected rows pass the saved-artifact audit. Raising the
logical-work cap from 2 million to 100 million, while keeping the frozen binary,
runner and 5s solver deadline, solves none of the eight historical native-walk
gaps. Parent denominators remain 656 source slots / 640 imports / 16 unavailable.
The diagnostic also includes the two previously unary-only answers.

Binary now checks SharedMemory-50 RC04: 0.840s solver plus 0.939s checker.
Unary already checked it, and takes 0.046s plus 0.240s in this run. Binary still
loses TokenRing-40 RC04 to the separate 60s checker deadline; unary checks it
in 0.531s plus 28.515s. This is one repetition, not a stable timing comparison.

The final matrix is binary 1 checked negative / 10 selected queries and unary
2 / 10, with every other row Unknown. Six of binary's eight historical-gap rows
hit the outer wall limit; NoC3x3-8B RC12 exhausts bounded discovery, and
SharedMemory-200 RC04 still reaches the logical-work cap. Native-walk already
answers both recovered/retained negatives; no integrated coverage gain was
measured. Empty outputs after process termination are retained as timeout
evidence, not parsed as answers.

This does not rule out a more efficient threshold engine or richer candidate
language. It does rule out attributing all eight existing gaps solely to the
initial 2-million cap. Keep the engine opt-in; prioritize the acquired new
cohort and the measured walk-first scheduling overhead before further investment.

Evidence: `signed-threshold-workcap-v1-audit.json`,
`signed-threshold-workcap-v1-comparison.json`, frozen plan/selection and all
20 original rows. No full-cohort gain, novelty or superiority claim.
