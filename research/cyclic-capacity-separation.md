# A live cycle separating bounded and unbounded token flow

The new `capacities_separate_a_live_cycle_with_all_transitions_reachable` test
in `tests/bounded_token_cut.rs` embeds the exact problem from
`research/cyclic-capacity-query.json` (semantic JSON equality checked). No
production code changed.

Exhaustive original-net exploration verifies exactly five reachable markings:
`A+x -> A+y -> B+y -> C+y -> C+x -> A+x`. All five transitions fire in this
cycle; none of the reachable markings satisfies the target `B >= 1 && x >= 1`.
The example has no initial deadlock or transition-support obstruction.

With the explicitly certified control projection `{A,B,C}`, transition counts
`[1,2,1,1,1]` produce the spurious endpoint `B+x` in the state equation. The
test verifies an explicit exact model of the entire unbounded token-moment
relaxation, including original enabling constraints:

| Transition | Count | Source x moment | Source y moment |
|---|---:|---:|---:|
| convert-at-A | 1 | 1 | 0 |
| advance-to-B | 2 | 1 | 2 |
| advance-to-C | 1 | 0 | 2 |
| convert-at-C | 1 | 0 | 1 |
| return-to-A | 1 | 1 | 1 |

Control moments are the edge count at the source control place and zero at
other control places. The unbounded per-place separator also reports every
place feasible for this model.

The original-net potential checker verifies weights `x:1, y:1`, establishing
`x+y <= 1` and individual capacities `x <= 1`, `y <= 1`. At terminal B, the
bounded cut for y requires

`y_final + count(advance-to-C) - count(advance-to-B) >= 0`.

Control balance requires one more arrival than departure at B, so this cut
implies `y_final >= 1`. But the target requires `x_final >= 1` and conservation
gives `x_final+y_final=1`, a contradiction. Equivalently, the unbounded model
puts two units of source y moment on one departure from B; the certified
capacity prohibits this.

The test checks that bounded separation returns a violated cut, that the
unbounded cut checker rejects that cut without its capacity assumption, and
that exact checked rational refutations exist for the full bounded relaxation
at **every terminal control mode**, without fixing transition counts. Thus it
proves more than rejection of the displayed candidate model.

Validation: `cargo test --locked --test bounded_token_cut` completed with
**6 passed, 0 failed**. Log: `research/cyclic-capacity-separation-tests.log`.
The Cargo process is terminal. This establishes a strict separation for this
fixed abstraction on this instance; it makes no performance or broad solver
superiority claim, and another control projection may change the comparison.
