# Pro consultation — saved 2026-09-26

Source: https://chatgpt.com/c/6ab8245e-dd18-83e9-a7c6-0ac9cd28e682

This preserves the substantive answer. Sections through 5.1 are copied from the completed response; sections 5.2–10 are condensed from the full browser-visible response because the chat retrieval tool truncates messages at 20,000 characters. The full verbatim answer remains at the source link. Pro's proposals and literature claims are not independently verified implementation results. See `pro-assessment.md` for local evidence.

## Recommendation

**Build a portfolio around certified state-equation reasoning and accelerated witness search—not around a first implementation of full KLMST.** Add a continuous-reachability-inspired support refinement to strengthen unreachability, and retain KLMST as a separate completeness experiment.

The most promising opportunity is not simply replacing Python with Rust. It is to exploit the small, structured queries, reuse work across disjuncts, and replace expensive generic certificate validation with small, specialized arithmetic certificates.

**Inspection status:** I read the paper, inspected the Zenodo archive’s file listing, and inspected upstream SMPT’s state-equation and BMC implementations. The ZIP download failed, so I did **not** inspect the pinned Rust source files or execute the archived experiments. The manifest includes the experimental records and an `SMPT_certificate_fix_v2.patch`; those should be preserved when reproducing the baseline. The numerical triage below comes from the accessible paper PDF, which is v4, rather than a fresh run of the artifact. :chatgpt-content-reference{index="0"}

My recommended order is:

1. **State equation over exact rational/integer arithmetic, with independently checked refutations.**
2. **Your explicit Rust search, strengthened with count-vector guidance and exact word acceleration.**
3. **Target-sensitive, bidirectional support refinement of the state equation.**
4. **Two complementary fallback experiments:** finite threshold/congruence abstraction, and accelerated Presburger backward search.
5. **KReach on the residual cases before committing to a KLMST port.**

No speedup is established yet. The plan below is designed to discover quickly whether the gains come from arithmetic, search, process overhead, or proof checking.

---

## 1. What the existing results suggest targeting

The paper reports **45/47 solved** at a 500-second limit: 26/27 serializable and 19/20 nonserializable. Selected Table 4 entries are particularly informative; times below are seconds, converted from the reported milliseconds. :chatgpt-content-reference{index="1"}

| Benchmark | Expected result | Certificate generation | Total |
|---|---|---:|---:|
| `c1.ser` | Nonserializable | 356.195 | 356.299 |
| `c2.ser` | Serializable | 9.858 | 292.228 |
| `e4.ser` | Nonserializable | 273.062 | 273.351 |
| `g7.ser` | Serializable | 6.886 | 252.752 |
| `e2.ser` | Nonserializable | Timeout | Timeout |
| `g2.ser` | Serializable | Timeout | Timeout |

These suggest three separate experiments:

- **Witness-search experiment:** prioritize `c1`, `e4`, and `e2`.
- **Certificate/end-to-end experiment:** prioritize `c2` and `g7`. Their generation-to-total gaps are large, although the gap includes more than proof checking alone.
- **Unreachability-coverage experiment:** prioritize `g2`.

The approximately 13-place/13-transition averages are encouraging, but should not determine data-structure limits. Measure the distribution of actual exported queries, including auxiliary places and the largest sliced instances.

### Do not equate SMPT’s `STATE-EQUATION` with the bare state equation

The upstream implementation I inspected first tries the state equation, then adds **read-arc constraints**, then **useful marked-trap constraints**. Its negative certificate existentially quantifies transition-count variables and incorporates those strengthenings. This is upstream behavior, not confirmation of the artifact’s exact revision. 

Consequently, a rational state-equation solver alone might be very fast but lose coverage. Instrument the baseline to record the **winning method and strengthening stage**, not merely “SMPT solved it.”

Upstream BMC also has interactions with a separate induction result and a special fully reduced-net case; therefore, do not infer every negative result’s provenance merely from the configured method names. 

---

## 2. Fix the mathematical and implementation boundary first

Represent a net by

\[
m_0\in\mathbb N^P,\qquad
\mathrm{Pre},\mathrm{Post}\in\mathbb N^{P\times T},
\qquad C=\mathrm{Post}-\mathrm{Pre}.
\]

A transition \(t\) is enabled precisely when

\[
m\geq \mathrm{Pre}_t,
\]

and produces \(m+C_t\).

Represent a target as a union of conjunctions:

\[
G=\bigvee_j G_j,\qquad
G_j(m)\equiv A_jm\leq b_j\ \land\ E_jm=f_j.
\]

The solver’s meaning is

\[
\exists m\in\mathbb N^P.\ m_0\longrightarrow^*m\land G(m).
\]

Preserve existential variables or their auxiliary-place encoding exactly. Normalize strict integer inequalities before rational relaxation: for integer-valued \(a^\top m\),

\[
a^\top m<b \iff a^\top m\leq b-1.
\]

**Keep `Pre` and `Post`, not just the incidence matrix.** A transition consuming and reproducing a token has zero net effect on that place but still needs the token.

Use three verdicts:

```text
REACHABLE(witness)
UNREACHABLE(certificate)
UNKNOWN(reason)
```

For a disjunction, one checked witness suffices for `REACHABLE`; **every disjunct must be refuted** for `UNREACHABLE`. An unfinished disjunct means `UNKNOWN`, unless another supplies a witness.

### Recommended portfolio

| Engine | Positive result | Negative result | Priority |
|---|---|---|---|
| Structural facts + rational/integer state equation | Count candidate only | Exact arithmetic refutation | First |
| Explicit search | Checked firing sequence | Exhausted finite reachable graph only | Already underway |
| Support-refined state equation | Candidate only | Certified support pruning + arithmetic refutation | Next |
| Exact word/path-scheme acceleration | Checked compressed witness | Not by failure of selected schemes | Next |
| Finite threshold/congruence abstraction | Candidate abstract path only | Exhausted abstract graph avoiding target | Experimental |
| Presburger backward search with acceleration | Witness, when construction is exact | Checked backward-closed separator | Experimental |
| Karp–Miller | Generally not an exact witness | Disjointness from coverability overapproximation | Gated |
| Full KLMST | Exact reachability | Exact unreachability | Separate completeness track |

I would not initially implement a new general-purpose SMT solver, full polyhedral PDR, a decision-diagram package, and KLMST simultaneously.

---

## 3. First unreachability engine: certified state-equation reasoning

### 3.1 Start with the strongest cheap necessary condition

Every real firing sequence has a nonnegative integer transition-count vector \(x\) satisfying

\[
m=m_0+Cx.
\]

For one target conjunction, construct

\[
\begin{aligned}
x&\geq0,\\
m_0+Cx&\geq0,\\
A_j(m_0+Cx)&\leq b_j,\\
E_j(m_0+Cx)&=f_j.
\end{aligned}
\tag{SE}
\]

This eliminates the marking variables if convenient.

There are three distinct outcomes:

- **Infeasible over \(\mathbb Q\):** target unreachable.
- **Feasible over \(\mathbb Q\), infeasible over \(\mathbb Z\):** target unreachable, but integer reasoning is necessary.
- **Feasible over \(\mathbb Z\):** only a candidate count vector. Its firings may be impossible to order.

The last distinction is fundamental.

### 3.2 Use specialized refutation certificates

Put the rational relaxation into the form

\[
Dz\leq e.
\]

An infeasibility certificate is a vector \(\lambda\) satisfying

\[
\lambda\geq0,\qquad
\lambda^\top D=0,\qquad
\lambda^\top e<0.
\tag{F}
\]

After clearing denominators, checking this requires only exact integer arithmetic.

The implementation architecture should be:

```text
possibly complicated arithmetic search
                 ↓
small exact certificate
                 ↓
independent Rust checker
```

The checker does not need to understand simplex pivots or trust floating-point tolerances. A floating-point solver may propose a dual certificate, but the answer becomes `UNREACHABLE` only after exact reconstruction and checking.

This also avoids asking a generic Presburger checker to rediscover why an existentially quantified state-equation formula excludes the target. You are checking a direct proof that **every execution induces a count vector, but no such count vector exists**.

### 3.3 Separate two implementation tracks

**Fast experimental track: Rust + existing ISL.**

Construct the integer set defined by `(SE)` and ask for emptiness or a sample point. ISL supports exact integer sets with affine constraints and existential variables; `isl_set_is_empty` tests integer emptiness. This is a useful no-Z3 experiment, but it is **not an all-Rust arithmetic implementation**, and an ISL emptiness result is not itself a small independently checked certificate. :chatgpt-content-reference{index="4"}

**Native certified track: Rust arithmetic kernel.**

Implement exact rational feasibility/refutation, followed by limited integer strengthening. For this workload I would begin with a rational phase-I simplex implementation or a deliberately budgeted elimination procedure, with arbitrary-precision arithmetic and a checked fixed-width fast path.

Do not postpone the workload experiment until a sophisticated native ILP solver exists. First measure how many queries fall into:

```text
rationally infeasible
integer-only infeasible
requires topology/support reasoning
requires genuinely deeper reachability reasoning
```

That classification should drive the arithmetic investment.

### 3.4 Add structural facts before expensive branching

Useful directly checkable facts include:

**Conservation laws.**

\[
y^\top C=0
\quad\Longrightarrow\quad
y^\top m=y^\top m_0.
\]

For nonnegative \(y\), these can also prove global bounds. If \(y_p>0\),

\[
m_p\leq
\left\lfloor\frac{y^\top m_0}{y_p}\right\rfloor.
\]

**Congruence information.** Integer lattice constraints can reject cases that rational arithmetic cannot. The one-place example \(m_0=0\), transition \(+2\), target \(1\), should be an early regression test.

**Marked traps.** For a trap \(Q\), every transition that consumes from \(Q\) also produces into \(Q\). If initially marked, it remains marked:

\[
\sum_{p\in Q}m_p\geq1.
\]

**Initially empty siphons.** These remain empty. Their certificates can justify both marking constraints and removal of transitions requiring their tokens.

At small place counts, enumerating subsets to discover small traps/siphons is worth testing. Gate it by actual size rather than the average.

**First-use/read requirements.** One useful necessary implication, derived directly from the marking before the first firing of \(t\), is

\[
x_t>0\Rightarrow
m_{0,p}+
\sum_{\substack{u\neq t\\C_{pu}>0}}C_{pu}x_u
\geq \mathrm{Pre}_{pt}.
\tag{R}
\]

Before the first \(t\), no production by \(t\) is available; ignoring consumption by other transitions only increases the bound. This can reject self-enabling algebraic cycles.

Do not encode `(R)` with an invented big-\(M\) bound. Split the integer cases \(x_t=0\) and \(x_t\geq1\), or use an appropriate exact disjunctive representation.

### 3.5 Integer refutation without Z3

A practical certificate format is a branch tree. Each internal node splits an integer-valued linear expression \(h(z)\):

\[
h(z)\leq k
\quad\lor\quad
h(z)\geq k+1.
\]

Every leaf has a rational refutation of its accumulated constraints. The checker verifies that each split is exhaustive and each leaf satisfies `(F)`.

This gives sound integer unreachability without trusting an ILP solver. However, **a naïve branch-and-bound implementation is not automatically a terminating decision procedure for unbounded ILP**. Apply budgets and return `UNKNOWN` when necessary.

---

## 4. The most promising strengthening: target-sensitive support refinement

This is the next method I would implement after plain state-equation refutation.

The literature behind it is the continuous Petri-net characterization using the state equation plus forward and backward firing-support conditions. Continuous reachability overapproximates discrete reachability, so a negative continuous result is useful even though a positive result is not a discrete witness. Fraca–Haddad’s characterization is restated in Section 3 of Blondin–Esparza’s *Separators in Continuous Petri Nets*. :chatgpt-content-reference{index="5"}

For your implementation, I recommend the following **necessary-condition elimination procedure**, with its own simple soundness argument. This avoids depending on a claim that the implementation is already a complete continuous-reachability solver.

### 4.1 Maintain a target-conditioned relaxation

For a remaining transition set \(S\), define

\[
\mathcal P_S =
\left\{
(x,m):
\begin{array}{l}
x\geq0,\ m\geq0,\\
m=m_0+Cx,\\
G_j^{\mathbb Q}(m),\\
x_t=0\text{ for }t\notin S
\end{array}
\right\}.
\]

Additional constraints known to hold for every discrete successful run may be included.

Compute two possible-positive supports:

\[
U=\{t:\exists(x,m)\in\mathcal P_S.\ x_t>0\},
\]

\[
V=\{p:\exists(x,m)\in\mathcal P_S.\ m_p>0\}.
\]

These are supports over **all feasible count vectors and all feasible target markings**.

That distinction matters. Using the support of one LP model would be unsound: another feasible endpoint might enable a different backward path.

Each support test can be implemented by maximizing the relevant nonnegative coordinate. An exact upper bound of zero proves absence; a positive feasible value or an unbounded objective proves possible positivity.

For rational reasoning, do not replace “\(x_t>0\) is possible” by “\(x_t\geq1\) is possible.”

### 4.2 Compute optimistic firing support

```text
fireable_support(pre, post, transitions U, initially_positive W):
    positive = W
    fireable = {}

    repeat:
        changed = false
        for t in U:
            if support(pre[t]) ⊆ positive:
                add t to fireable
                add support(post[t]) to positive
                update changed
    until not changed

    return fireable
```

This deliberately never removes a positive place. It is an optimistic support analysis, not a simulation of discrete firing.

Compute

\[
F=\operatorname{fireableSupport}
(\mathrm{Pre},\mathrm{Post},U,\operatorname{supp}(m_0))
\]

and

\[
B=\operatorname{fireableSupport}
(\mathrm{Post},\mathrm{Pre},U,V).
\]

The second call uses the reversed net.

### 4.3 Main loop

```text
support_refutation(net, target):
    S = all transitions
    proof = []

    loop:
        P = state_equation_relaxation(net, target, allowed=S)

        if P is certified infeasible:
            return UNREACHABLE(proof + infeasibility_certificate)

        U = possible_positive_transition_support(P)
        V = possible_positive_final_marking_support(P)

        F = fireable_support(Pre,  Post, U, support(m0))
        B = fireable_support(Post, Pre,  U, V)

        S_next = F ∩ B

        record forced-zero certificates and support computations

        if S_next == U:
            return UNKNOWN(relaxation_candidate)

        S = S_next
```

Subject to finishing the arithmetic calls, each nonterminal iteration eliminates a transition that was still possibly positive. There can therefore be only finitely many strict eliminations.

### 4.4 Why a negative result is sound

Maintain this invariant:

> Every actual run from \(m_0\) to the target uses only transitions in \(S\).

Initially it is trivial.

Suppose a successful run exists using only \(S\). Its firing counts and endpoint belong to \(\mathcal P_S\). Therefore its used transitions lie in \(U\), and its endpoint support lies in \(V\).

Replay the run in order, considering only whether places have ever become positive. Every used transition is admitted by the forward support closure, so its support lies in \(F\).

Now replay the actual run backwards in the reversed net. Every used transition is admitted by the backward support closure, so it also lies in \(B\).

Thus the run uses only \(F\cap B\), preserving the invariant. If the restricted state equation eventually becomes infeasible, no successful run exists.

This argument handles the **entire linear target**, not just a selected target marking.

### 4.5 Certificate and implementation details

The certificate needs:

- Exact proofs for variables declared forced zero.
- The remaining transition set at each round.
- Recomputable forward/backward support closures.
- A final arithmetic refutation.

The crucial scope rule is:

**Backward-support eliminations are query-local.** A transition impossible on a run to one target may be essential for another disjunct. Never install those removals into a global shared net.

Your frontend already performs bidirectional slicing. The potential additional value here is that **linear constraints and the state equation force counts or endpoint places to zero, which then enable further support pruning**. Measure its marginal contribution rather than assuming it will help.

Blondin–Esparza also develop efficiently checkable continuous separators. Their set-to-set extension requires care: the direct singleton certificate-checking result does not simply transfer unchanged to arbitrary linear targets; Section 7 handles this through an altered net. That is a useful later certificate-compression direction, not something to assume in the first implementation. :chatgpt-content-reference{index="6"}

---

## 5. Strengthen the positive engine with counts and exact acceleration

Your independently checked explicit baseline is the right foundation. I would add two things before sophisticated symbolic search.

### 5.1 Try to realize promising integer count vectors

For an integer state-equation solution \(x\), search for an ordering of exactly that multiset:

```text
realize(marking m, remaining counts r):
    if r == 0:
        return success iff target(m)

    for enabled t with r[t] > 0:
        recursively try realize(m + C[t], r - unit(t))
```

Memoizing the remaining-count vector is sufficient for a fixed initial count vector, because it determines the current marking.

Minimizing \(\sum_t x_t\) supplies short candidate counts. Even unsuccessful attempts may guide ordinary search toward relevant transitions.

But:

- Greedy scheduling failure does not prove the count vector unrealizable.
- Exhaustive failure proves only that particular count vector unrealizable.
- It does not exclude solutions with additional cycles or a different target marking.

The Sara work is directly relevant: Wimmel and Wolf develop state-equation CEGAR with justified refinements and an `lp_solve` arithmetic backend. Their method is incomplete; it is a practical design reference, not a substitute for proving your own cuts sound. :chatgpt-content-reference{index="7"}

### 5.2 Exact acceleration of a fixed transition word (condensed)

For a transition word \(w=t_1\cdots t_\ell\), let
\[
\delta_w=\sum_i C_{t_i},\qquad
r_w(p)=\max(0,\max_j[\mathrm{Pre}_{p,t_j}-\sum_{i<j}C_{p,t_i}]).
\]
Then \(m\xrightarrow{w}m+\delta_w\) exactly when \(m\ge r_w\).
For \(n\ge1\), \(w^n\) is executable exactly when
\[
m_p\ge r_w(p)+(n-1)\max(-\delta_w(p),0)
\]
for every place; the endpoint is \(m+n\delta_w\). The zero-repetition case is identity.

Use these exact conditions for selected path schemes \(u_0v_1^{n_1}u_1\cdots v_k^{n_k}u_k\). Integer exponent solutions yield compressed witnesses that can be checked without expanding every firing. Mine short/repeated words rather than enumerate all schemes. Failure for selected schemes does not prove unreachability.

## 6. Complementary unreachability experiments (condensed)

**Finite threshold/congruence abstraction.** Abstract counters as \(0,\ldots,K-1,\ge K\), optionally with residues; keep proven bounded control places exact. Include an abstract edge whenever some concrete marking in its source can fire to its destination. Cartesian interval/residue edge feasibility is coordinatewise. Target-cell intersection may use a conservative interval test. Exhaustion without a potentially bad cell proves unreachability; an abstract bad path requires concretization. A decrement from the high bucket can leave it: retaining only the high-bucket successor is unsound. Projection onto a subset of places is also useful if both transitions and target are projected existentially.

**Accelerated Presburger backward search.** With ISL, compute
\[
\operatorname{Pre}_t(B)=\{m:m\ge\mathrm{Pre}_t,\ m+C_t\in B\}.
\]
Exact predecessor construction with provenance can produce witnesses. A candidate backward barrier, including a heuristically widened one, proves unreachability after checking
\[
G\subseteq B,\quad m_0\notin B,\quad \operatorname{Pre}_t(B)\subseteq B
\]
for every transition. Overapproximate positive membership is not a witness. ISL's general transitive closure can be approximate: inspect its exactness flag. Keep the trusted-ISL boundary distinct from independently checked native certificates.

## 7. Karp–Miller, KLMST, and point-target adapters (condensed)

Karp–Miller can prove a linear target disjoint from the downward closure of reachable markings. Intersection generally means UNKNOWN for exact reachability. Use it for upward-closed targets, boundedness, coverability-based refutation, or later pumpability subproblems. Treat omega markings as sets of finite markings; do not use informal mixed-sign omega arithmetic.

KReach (Dixon–Lazić, TACAS 2020) implements Kosaraju's complete procedure in Haskell. Its Diophantine/ILP component uses SBV and SMT solvers, so it is not SMT-free. Benchmark it on residual queries before undertaking a native port. A serious KLMST implementation needs generalized VASS sequences, SCC decomposition, characteristic integer systems, bounded-variable refinements, forward/backward pumping, bounded-coordinate unfolding, a well-founded refinement argument, and proof/witness extraction. Lasota's “VASS reachability in three steps” is an explanatory starting point, not a complete implementation specification. Recent theoretical complexity improvements do not demonstrate practical speedups here.

A sound adapter from linear target conjunctions to exact point reachability can freeze the original net with phase control, then consume each original marking token into accumulators for **all** target rows. For \(a^\top m\le b\), accumulate \(a^+{}^\top m+b^-\) in L and \(a^-{}^\top m+b^+\) in R. Pairwise cancellation plus disposal of excess R checks the inequality; equality allows no one-sided disposal. Require all original/accumulator places empty at the exact final marking. Phase control and leftover-token requirements prevent early switches from admitting false positives. Audit KReach's input conventions; never silently replace inequalities with equalities.

## 8. Soundness regressions (condensed)

- Final bounds are not bounds on intermediate markings.
- Componentwise marking dominance does not justify exact-state subsumption for arbitrary linear targets.
- Arithmetic overflow requires checked promotion or UNKNOWN.
- An incidence-matrix basis change does not automatically preserve VASS nonnegativity semantics.
- Partial-order reduction needs a reachability-preservation argument, including target-satisfying intermediate states.
- Overapproximations prove negatives; their positive paths need lifting. Underapproximations produce witnesses; failure proves nothing.
- Preserve guards on auxiliary places.
- Keep target-conditioned support pruning and caches query-local.
- Validate witnesses and certificates before publishing definitive verdicts.

## 9. Implementation sequence (condensed)

1. Preserve the frontend and exact queries, canonical hashes, disjunct identities, source mappings, and proof-aware result interface.
2. Add target simplification, structural invariants/proven one-hot groups, optional ISL integer state-equation classification, and native rational certificates.
3. Add traps, siphons, first-use constraints, target-sensitive support refinement, and budgeted integer split certificates. Measure each strengthening's added coverage.
4. Add count-guided witness realization and exact word acceleration; validate compressed witnesses directly.
5. Try threshold/residue abstraction, ISL backward search, and KReach via a verified target adapter. Let residual cases determine investment in stronger arithmetic, path-scheme discovery, invariant synthesis, or full KLMST.

The proposed mapping onto the existing Rust frontend's modules is only a proposal; Pro did not inspect the pinned source archive.

## 10. Benchmark methodology (condensed)

Keep fixed-query backend measurements separate from end-to-end runs through all 47 source benchmarks. Record frontend, startup/parse, preprocessing, solve+certificate generation, validation, and lifting separately, plus wall time, total worker CPU, peak memory, and core budgets.

Pin the artifact, supplied patch, SMPT/Z3/ISL versions, Rust toolchain/build flags, and invocation. Compare both existing certificate validation and specialized checkers. Preserve the artifact's STATE-EQUATION+BMC configuration. Keep short exploratory budgets distinct from the paper's 500-second experiment.

Report cold isolated calls, warm/batched calls, and whole-benchmark timings separately. All disjuncts must be refuted for a serializable case; one witness can end a nonserializable case, making query order significant. Report coverage and incorrect-answer counts before common-solved speed ratios; separate timeouts. Use repeated runs and ablations, and retain held-out variants.

## Pro's conclusion (condensed)

Prioritize explicit search plus certified algebraic refutation, strengthened by support reasoning and exact word acceleration. Hypotheses to test: arithmetic/topological refutations cover many negatives; specialized certificates reduce validation cost; exact loop summaries help difficult positives; batching amortizes shared preprocessing. Evaluate KLMST on residual workloads before committing to a full port.

## Sources visible in the completed answer

- Paper: https://arxiv.org/pdf/2601.02251 (Pro reports consulting v4).
- Artifact listing: https://zenodo.org/records/17253581/preview/ser_artifact.zip?include_deleted=0
- ISL documentation: https://libisl.sourceforge.io/user.html
- Blondin–Esparza, Separators in Continuous Petri Nets: https://arxiv.org/pdf/2209.02767
- Wimmel–Wolf / Sara: https://arxiv.org/pdf/1208.2159
- FAST/acceleration bibliography: https://www.labri.fr/perso/leroux/publi/index.html
- KReach: https://wrap.warwick.ac.uk/id/eprint/134045/1/WRAP-KReach-tool-reachability-petri-nets-Lazic-2020.pdf
- Lasota, VASS reachability in three steps: https://arxiv.org/pdf/1812.11966
- Pumpability paper referenced by Pro: https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.CONCUR.2026.24

