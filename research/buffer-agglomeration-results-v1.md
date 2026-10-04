# Buffer agglomeration: initial evidence

The opt-in uniform-buffer rule closes the motivating NoC3x3 RC12 gap in one local
same-binary comparison. Control timed out at 10.028 s; buffer agglomeration returned
a checked counterexample in 0.148 s. The 244-transition witness independently
replays on the original PNML net, whose AG property is therefore false. This is
one development query and repetition, not a stable speedup or competitor result.

The indexed reduction removes 8,755 initially empty, unqueried places, producing
385 places and 5,822 transitions from 9,140 and 14,577. Python independently
reconstructed both saved reduced nets byte-for-byte at the JSON value level.
Preparation took about 71 ms in the two local inspections. Exact transition arc
signatures number 755; possible duplicate elimination remains future work.

The first frozen implementation attempted expanding Cartesian products and hit
its cumulative transition cap. Both failed inspections are retained. Discovery
now skips merges that expand active transition count or exceed the cumulative
transition cap. The independent proof rule remains unchanged. Other preparation
failures still fall back; defaults remain unchanged.

Validation: 428 tests passed in the full Rust suite, with one preexisting ignored.
After the discovery change, 12 module tests and nine CLI tests passed, including
one additional regression test. Seventy Python tests passed. Formatting, Clippy
and release builds passed; existing vendor warnings remain in logs. The initial
compilation failure from an ambiguous test assertion is retained.

The first NoC timing launcher lacked --track-resources and failed before execution.
The second enabled profiling, whose stderr events were merged into the answer log;
the validator correctly rejected extra JSON. Both attempts remain unchanged. The
third run disables profiling and independently validates the witness. Recorded
solver time excludes the separately bounded validator.

Frozen candidate: results/solver-buffer-agglomeration-v2. Semantic contract:
research/buffer-agglomeration-contract.md. Structural evidence:
results/buffer-agglomeration-inspection-v2/report.json. Original-input comparison:
results/buffer-agglomeration-noc-v3 and its verification report.

Next: full 192-query application regression, both configurations on this frozen
binary. The separate Linux 464-slot/448-imported ladder screen still uses the
older frozen capacity-direct binary. These experiments answer different questions.
