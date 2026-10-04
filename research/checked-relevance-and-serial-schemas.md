# Checked relevance and serial sublanguages

Two changes share a principle: construct a smaller mathematical object, record
how it relates to the original query, and independently check that relation
before accepting a negative answer. These implementations do not establish a
novel research contribution by themselves.

## Shared relevance reduction

The positive search already discarded irrelevant transitions. The new shared
preprocessing applies the same exact reduction before `portfolio-focused`
and the focused fallback of `portfolio-symbolic`. Other CLI methods and the
default selection remain unchanged.

Retain target-support places, every transition changing one of those places,
the input places of retained transitions, and recursively every producer of a
retained input place. Each retained transition keeps all its guards. Every
omitted transition has nonpositive incidence on retained places and zero
incidence on target-support places.

From any original execution, delete the omitted transitions. Retained guard
counts can only increase and target coordinates remain equal, so the retained
sequence is enabled and reaches the same target values. Conversely, reduced
transitions have exactly the original retained guards; their firing sequence
lifts to the original net. Thus reachability of signed/equality linear targets
is preserved over mathematical natural-number markings. The implementation
checks u64 replay and returns unknown on overflow.

Positive results use lifted original transition IDs and original-net replay.
Negative results carry a `relevance-v1` wrapper with retained place/transition
IDs and an inner proof. Rust and Python independently reconstruct and check
the reduction from the original arcs before verifying the inner proof on the
reconstructed net. Plain state-equation certificates have an explicit
`state-equation-v1` adapter; a negative without a supported certificate is
not accepted. Nesting is limited to32 wrappers. Outer checking deadlines still
bound older inner checkers that do not offer fine-grained interruption.

Exhaustive tests cover2,048 bounded original-net/target combinations, plus
forged mappings, omitted read guards, signed targets, dropped outputs,
arithmetic/resource limits, and CLI lifting/checking of both verdicts.
Independent Python tests cover structural forgery and nested proof dispatch.

## Serial sublanguage certificates

For an automaton target, a path schema consists of consecutive path segments
with finitely many closed walks at each segment's endpoint. Any listed closed
walk can be repeated independently a nonnegative number of times. Starting
at the automaton initial state, the skeleton must finish at an accepting state.

Its Parikh image is exactly one linear set: the sum of skeleton labels is the
base, and each closed walk contributes one period vector. Thus every vector
in the derived linear set belongs to the original automaton's Parikh image.
Several schemas form a certified serial sublanguage. They need not cover the
whole language: proving all completed reachable responses lie in this subset
is already sufficient to prove serializability.

`raw-automaton-invariant-v1` contains explicit original automaton edge paths
and the existing component-invariant certificate for the derived subset.
Rust and Python both regenerate the linear sets from these paths, validate
continuity, cycle closure and acceptance, and check the component invariant
against the original Petri net. Neither supplied period vectors nor claims
about exhaustive automaton coverage are trusted. Changed original nets,
non-closing loops and nonaccepting endpoints are rejected.

Discovery is deliberately incomplete and separately bounded. It proposes
skeleton walks with fundamental closed walks at visited anchors, retaining
return visits when they add useful independent periods. Exact decomposition
can remove redundant generators/bases; inconclusive decomposition retains
them. The current256-schema cap and finite control-invariant search can both
limit coverage. See research/raw-schemas-discovery.md for details.

The component-invariant proof uses credited in-flight responses as before.
This work extends its applicability to the compact serial-automaton target;
it does not require constructing that automaton's full semilinear image or its
complement. Unknown remains the answer whenever discovery or checking fails.

## Validation and measurements

Combined full Rust suite:300passed,0failed,1preexisting ignored. The later
resource-accounting adjustment passed focused schema and raw-negative CLI
tests. Python raw suite45passed; schema checker tests also pass with `-O`.
Python relevance tests12passed, including the legacy Farkas adapter's explicit
rejection under `-O`. Clippy/release completed; retained upstream Varisat
warnings are unrelated to these changes.

The full Linux stress comparison already running uses the earlier relevance
inside search only. It cannot measure this shared preprocessing or the new
serial certificates. Freeze and label subsequent runs separately. Do not
attribute previous35→46 JoinFree coverage to the unmeasured shared change.

The first full twelve-source negative-only pilot completed in
`results/raw-diverse-schemas-v1`: zero verified negatives, twelve unknowns.
The three validated optimistic cases exhaust invariant-discovery work; the
pairlocked cases fail to find a closed component invariant. The new proof
interface passes tests but has not yet improved measured negative coverage.
See `research/raw-diverse-schemas-v1-analysis.json`; keep this negative result
separate from the prior positive guidance gains.
