# Direct symbolic simulation into the serial automaton

**Next hypothesis: replace serial-schema enumeration and explicit control games
with a checked symbolic simulation into the original serial automaton.** Use
sparse linear relations over original places, with response credits for operations
whose serial effect has already occurred but whose response has not returned.
This is an implementation proposal, not a demonstrated transfer proof or novelty
claim.

Read-only inspection covered the corrected v2 source description, four-slot path
strict/early-release sources, and the raw schema, component discovery and checker
code. No exported JSON was parsed, algorithms run, or pinned files modified.
The source description's original “no export” statement is historical: the parent
reports six successful n4 exports and two strict n6 export timeouts, with collection
still active. Export failure is separate from solver difficulty.

## Why this is the useful generalization

Current `raw_schemas` enumerates certified path/cycle sublanguages, capped at256
schemas by its caller. `raw_negative` then constructs an explicit product of
projected markings and those components, requiring uniform affine base/period
maps. It can lose precision from incomplete serial sublanguages and spend memory
on concurrent control configurations. Control interning changes storage, not this
proof language.

A direct simulation keeps the serial automaton's states and transitions, avoiding
its semilinear expansion. Sparse predicates summarize sets of original markings
instead of enumerating their product. This can exploit protected intermediate
updates without proving a source-level locking theorem or trusting place names.
It remains an incomplete sufficient method for response-Parikh inclusion.

## Exact proof obligations

Let R extract original response coordinates, Z be the declared completion-zero
places, and d_t be an original transition's signed incidence vector. The proposed
certificate contains a nonnegative integer credit matrix C supported only on Z,
and finitely many regions (s, I), each pairing an actual serial-automaton state s
with a conjunction of sparse integer linear inequalities I(m). Define
F(m) = Rm + Cm. The certificate must establish:

1. **Initial inclusion.** The original initial marking satisfies an initial
   region. An explicit path from the automaton's initial state to that region's
   state has Parikh vector F(m_initial). Usually both are zero and the path is
   empty; do not assume that in the checker.
2. **Universal closure.** For every region and every original transition t,
   all nonnegative integer markings satisfying I and the original weighted
   enabling guard are covered by finitely many checked branches. Each branch
   supplies a destination region and an explicit serial path from s to its
   state, and proves I_destination(m+d_t). That path's exact Parikh vector must
   equal (R+C)d_t. Empty paths implement stuttering. Every enabled branch must
   be covered; proposing one feasible branch is insufficient.
3. **Completion.** In every region whose serial state is nonaccepting,
   I(m) together with m[Z]=0 is infeasible. At completion C contributes zero,
   hence the constructed accepting serial path has exactly the actual response
   vector. No fairness or termination assumption is needed.

Induction constructs a serial path for each original execution. Completion then
proves target exclusion. Supporting invariant facts must be part of I or have
separate checked initialization and closure proofs; lock exclusivity is never an
assumption. All arcs, initial values, response IDs and accepting states come from
the raw input. A negative credited increment cannot match a serial path: reject
that candidate rather than canceling past emissions. Limits yield Unknown.

This requires a **new certificate and independent checker**. Existing
`raw-component-invariant-v1` and `raw-automaton-invariant-v1` do not express these
obligations; preserve their formats and acceptance unchanged.

## Why strict transfers might fit

The corrected strict source holds both endpoint locks across debit/yield/credit.
A candidate relation can interpret a resource in a pending transfer as already
at its destination: virtual occupancy is actual occupancy plus selected pending
control tokens. Linearize the successful transfer at debit, and attach its future
response credit there. Deposit and response then preserve virtual state or F.
Failed transfers and count results need their own serial-edge obligations. Count
must be unable to inspect a pending protected update, proved from raw incidence
and region invariants. Disjoint transfers can share the same compact relations.

Early release should defeat the relevant closure implication: count can observe
a missing resource while the virtual occupancy includes it. This is a useful
counterexample-guided discovery signal, not a source-based verdict. A net with
multiple indistinguishable pending requests may require more relation detail;
the proposed affine credit scheme is not guaranteed to capture it.

## Small implementable first step

Implement the checker before ambitious inference. Represent closure coverage as
finite decision trees splitting an integer affine term at k into <=k and >=k+1.
At each leaf, either check an explicit successor/path and all required linear
implications, or check infeasibility. Sparse rational nonnegative linear-combination
certificates (Farkas certificates) suffice for these leaf implications over the
real relaxation and therefore over integer markings. Exact arithmetic validates
all coefficients and constants. This is deliberately incomplete for integer-only
facts; failed proof search cannot justify pruning. Branching and duplicated
regions may also grow exponentially.

Initially propose nonnegative place invariants and pending-credit columns from
incidence, and short serial paths from the supplied automaton. Use bounded search
or SMT only to propose regions and proof coefficients; the arithmetic checker is
the trust boundary. Do not begin with a generic quantified relation solver or
transaction-name recognizer. Even a manually proposed *raw-place* relation, fully
checked on every transition, is a useful first feasibility experiment. It is not
a complete automated solver result.

## Evidence required to proceed

After collection and the current pilot finish, inspect phase data first. Schema
truncation/period search or many concurrent control markings would justify this
experiment; parsing/export domination would not. On the smallest successful
strict export, require one independently checked direct-simulation certificate,
then apply the same discovery configuration to all six n4 exports and preserve
all12 source slots and export failures. Keep early-release witnesses checked by
the existing original-query verifier. Mutate credits, omit a transition branch,
weaken a lock fact, alter a path response and acceptance to test rejection.

Compare with the frozen structural and balanced baselines at matched whole-query
wall/memory limits, including relation inference and independent checking. Report
regions, predicate nonzeros, closure branches, serial-path lengths, certificate
bytes and checking cost against schema counts and explicit game size. A checked
strict proof with materially fewer product states and lower end-to-end resources
would support further implementation. No measured gain, transfer-net invariant,
source-to-query equivalence or publication novelty is established here.
