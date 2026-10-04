# Pro consultation

Source: https://chatgpt.com/c/6ab917b7-99a8-83ea-8cb3-13a53675ff43
Retrieved: 2026-09-27. Rendered substantive response; mathematical markup preserved in pro-publication-answer.html. Proposals are not independently verified results.

Recommendation

I would stop expanding the portfolio and build one refinement engine around a control-indexed token-flow relaxation of the state equation.

The particularly useful observation is this:

After fixing the firing counts and endpoint, the extra token-accounting constraints decompose into one network-flow problem per place, provided the abstract edge guards are boxes. An infeasible flow produces a compact, checkable linear cut. The dual certificates are control-dependent affine invariants.

That gives a coherent connection between several things you already have: state equations, finite control abstraction, interval information, firing-count scheduling, and relational invariants. It also gives a principled reason to refine the abstraction, rather than another heuristic that occasionally returns a proof.

I would make direct inclusion of completed behaviors in a supplied semilinear specification the strongest application of this engine. For raw SER, that means proving serial membership constructively, without first complementing the serial set. It should remain a general semilinear-contract interface, not a special procedure for your locked examples.

There are two substantial reservations:

The current measurements do not establish a broad improvement. They show useful small-net engineering progress and essentially no improvement on the larger held-out workload.
Neither control-dependent affine invariants nor refinement guided by failed schedules is new. The research contribution must be the particular relaxation, its efficient separation and refinement, its proof interface, and demonstrated advantages—not a claim to have invented conditional linear invariants.

I assessed the description, snippet, and measurements you supplied, examined related work, and implemented small independent algebraic probes. I did not inspect your full sources or rerun your benchmarks.

1. What the current evidence actually supports

Your results support the following interpretation.

Workload	Old → new	Interpretation
Classical small-net suite	27/37 → 37/37	A substantial improvement on that suite; likely a useful proof-language/discovery improvement.
MCC development	140/192 → 142/192	Small net gain, including a positive-answer regression caused by scheduling.
MCC evaluation	175/192 → 175/192	No demonstrated generalization benefit from v2.
Simplified SER backend disjuncts	217/218 → 217/218	No incremental coverage; the remaining example is informative about expressiveness.
Raw SER	Counterexamples, but no negative proofs	An important capability gap, and potentially a differentiated research opportunity.

These are your reported measurements, not independently reproduced results.

The 37-property result should not dominate the paper narrative. It has only 35 distinct properties, uses very small nets, and is precisely where your current control-candidate enumeration is applicable. The MCC result is the stronger warning: a technique that completes a classic toy suite can still contribute almost nothing to realistic workloads.

The absence of held-out improvement does not establish that relational control reasoning is unhelpful. It could reflect poor control discovery, insufficient relational expressiveness, overhead, or simply the wrong workload. But it does mean the next experiment must distinguish these explanations.

The comparison against the available SMPT installation is not suitable for a superiority claim. SMPT’s documented setup includes preprocessing and auxiliary tools that materially affect its portfolio; its repository explicitly documents dependency installation and different PDR configurations. Compare the artifact version and a fully installed, pinned current version separately. 
GitHub

For NTest3u, preserve a minimal reproducible report containing the original property, net, exact command, commit, dependencies, seed/environment, output, and independently replayed contradicting trace. Treat it as a correctness problem in that exact toolchain/configuration until localized—not as evidence against all SMPT versions or against PDR as a method.

The most important architectural diagnosis

Your current negative reasoning largely has two forms:

global arithmetic over firing counts
global arithmetic over firing counts

and

finite control partition
×
nonrelational data bounds
.
finite control partition×nonrelational data bounds.

The missing connection is arithmetic about how tokens move through the control partition.

Merely replacing boxes with polyhedra would address some of this, but would immediately put you in a crowded invariant-generation literature and could substantially increase discovery cost. The approach below makes that connection explicitly and exposes a cheaper graph-theoretic implementation.

2. Related work that constrains the novelty claim

These are the comparisons I would regard as essential.

Related work	What is already established; implication for your project
Wimmel & Wolf, Applying CEGAR to the Petri Net State Equation, TACAS 2011 / LMCS 2012	Solving the state equation, trying to realize the firing-count solution, and refining after failure is established. “Counts → schedule → refinement” is not a new central idea. 
arXiv

Esparza & Melzer, Verification of Safety Properties Using Integer Programming: Beyond the State Equation, 2000	Strengthening arithmetic reachability reasoning with additional structural constraints has a long history. 
Springer

Amat, Dal Zilio & Hujsa, Property Directed Reachability for Generalized Petri Nets, TACAS 2022; SMPT, FM 2023	Direct reasoning about general linear properties, PDR variants, acceleration/hurdles, and certificates already exist in the closest tool family. Your comparison must isolate a contribution beyond implementation language and startup cost. 
Springer
+1

Colón, Sankaranarayanan & Sipma, Linear Invariant Generation Using Non-linear Constraint Solving, CAV 2003	Farkas-based invariant synthesis is established. Importantly, synthesizing arbitrary inductive affine inequalities generally introduces nonlinear constraints. 
Theory of Computation

Ke et al., Affine Disjunctive Invariant Generation with Farkas’ Lemma, VMCAI 2025	Particularly close: control-flow transformations, affine disjunctive invariants, and Farkas-based synthesis. A paper whose main idea is “split control, then synthesize affine invariants” would need to explain the difference carefully. 
arXiv
+1

Zuleger, Ranking Functions for Vector Addition Systems	Control-state offsets, affine functions of counters, linear programming, and graph structure already interact in VASS analysis. Your safety potentials are not ranking functions, but the algebraic resemblance is substantial. 
arXiv

Trace partitioning, including Rival–Mauborgne and Trace Partitioning as an Optimization Problem, SAS 2024	Partitioning and automatically searching for useful partitions are established abstractions. Novelty must concern the particular refinement objective and implementation, not partitioning itself. 
ACM Digital Library
+1

van Dongen, Efficiently Computing Alignments—Using the Extended Marking Equation, BPM 2018	Strengthened marking equations also appear in process conformance, outside the usual model-checking citations. This deserves a targeted formulation-level comparison. 
Springer

Occupation-measure/moment relaxations for hybrid systems	Aggregating state values along executions and dualizing to functions on states has a broader optimization literature. Do not claim that primal/dual pattern itself as new, or transfer convergence results from different system assumptions. 
arXiv

For the raw-SER direction, your TACAS 2026 paper already constructs serial semilinear behaviors, complements them, and connects the resulting reachability problem to certificates. The new claim would have to be avoiding the complement at that interface and producing direct membership witnesses, not “first certified serializability checking.” 
arXiv

My novelty assessment: I have not established priority for the exact control-indexed token-flow formulation developed below. Its ingredients are established. Its combination, separation algorithm, and adaptive refinement are a plausible research direction, but require a direct comparison against strengthened marking equations and disjunctive invariant synthesis before being presented as new.

3. The central relaxation: count firings and the tokens carried through control
3.1 A finite control abstraction

Start with a certified finite partition of markings into cells 
𝑞
∈
𝑄
q∈Q.

The simplest useful case is a set of exactly represented bounded control places. The remaining places form a counter vector

𝑥
∈
𝑁
𝑑
.
x∈N
d
.

An original transition induces an abstract edge

𝑒
:
𝑞
⟶
𝑟
e:q⟶r

with counter update

𝑥
′
=
𝑥
+
Δ
𝑒
.
x
′
=x+Δ
e
	​

.

Its domain must include the original enabling condition. More generally, let

𝐷
𝑒
=
{
𝑥
:
𝐻
𝑒
𝑥
≤
ℎ
𝑒
}
D
e
	​

={x:H
e
	​

x≤h
e
	​

}

include:

the source cell;
the original precondition 
𝑥
≥
pre
⁡
𝑒
x≥pre
e
	​

;
the condition that 
𝑥
+
Δ
𝑒
x+Δ
e
	​

 belongs to the destination cell;
any independently certified background facts used to restrict the domain.

The abstraction must represent every original firing. It may contain spurious edges. An edge may be omitted only with a checked proof that its original-domain intersection is empty.

Crucially, retain transitions that stutter on the selected control coordinates. Their effects on the other counters are the entire point of this construction.

3.2 Two quantities per abstract edge

For a concrete execution, define

𝑛
𝑒
=
number of occurrences of edge 
𝑒
n
e
	​

=number of occurrences of edge e

and

𝑦
𝑒
=
∑
occurrences 
𝑘
 of 
𝑒
𝑥
𝑘
,
y
e
	​

=
occurrences k of e
∑
	​

x
k
	​

,

where 
𝑥
𝑘
x
k
	​

 is the counter vector immediately before that firing.

Thus 
𝑦
𝑒
y
e
	​

 is not another marking. It is the sum of the source markings at which that edge fires.

For a fixed initial mode 
𝑞
0
q
0
	​

 and candidate final mode 
𝑞
𝑓
q
f
	​

, introduce 
𝑛
𝑒
≥
0
n
e
	​

≥0, 
𝑦
𝑒
≥
0
y
e
	​

≥0, and final marking 
𝑥
𝑓
x
f
	​

. Initially solve their rational relaxation.

Control-flow balance

For every control state 
𝑞
q,

	
∑
𝑒
∈
out
⁡
(
𝑞
)
𝑛
𝑒
−
∑
𝑒
∈
in
⁡
(
𝑞
)
𝑛
𝑒
=
[
𝑞
=
𝑞
0
]
−
[
𝑞
=
𝑞
𝑓
]
.
		
(1)
e∈out(q)
∑
	​

n
e
	​

−
e∈in(q)
∑
	​

n
e
	​

=[q=q
0
	​

]−[q=q
f
	​

].
(1)
Token-moment balance

For every control state 
𝑞
q,

	
∑
𝑒
∈
out
⁡
(
𝑞
)
𝑦
𝑒
−
∑
𝑒
∈
in
⁡
(
𝑞
)
(
𝑦
𝑒
+
𝑛
𝑒
Δ
𝑒
)
=
[
𝑞
=
𝑞
0
]
𝑥
0
−
[
𝑞
=
𝑞
𝑓
]
𝑥
𝑓
.
		
(2)
e∈out(q)
∑
	​

y
e
	​

−
e∈in(q)
∑
	​

(y
e
	​

+n
e
	​

Δ
e
	​

)=[q=q
0
	​

]x
0
	​

−[q=q
f
	​

]x
f
	​

.
(2)
Aggregated enabling and cell constraints

Every occurrence satisfies 
𝐻
𝑒
𝑥
𝑘
≤
ℎ
𝑒
H
e
	​

x
k
	​

≤h
e
	​

, so summing gives

	
𝐻
𝑒
𝑦
𝑒
≤
ℎ
𝑒
𝑛
𝑒
.
		
(3)
H
e
	​

y
e
	​

≤h
e
	​

n
e
	​

.
(3)

For ordinary enabling alone, this is simply

𝑦
𝑒
≥
𝑛
𝑒
pre
⁡
𝑒
.
y
e
	​

≥n
e
	​

pre
e
	​

.

Finally impose the original target on 
𝑥
𝑓
x
f
	​

, including the fixed terminal control coordinates.

3.3 Soundness is a telescoping argument

Every actual execution supplies integer values satisfying (1)–(3).

Equation (1) counts entries and exits. Equation (2) cancels each intermediate marking against the same marking when it next leaves its control state. Equation (3) sums valid per-firing inequalities.

Therefore:

If this rational system is infeasible, the original target is unreachable.

A feasible solution is only an overapproximate execution summary. It is not a positive reachability answer.

Summing (2) over all 
𝑞
q gives

𝑥
𝑓
=
𝑥
0
+
∑
𝑒
𝑛
𝑒
Δ
𝑒
.
x
f
	​

=x
0
	​

+
e
∑
	​

n
e
	​

Δ
e
	​

.

So the ordinary state equation is contained in the construction.

In production, retain the full original state equation, with

𝑛
𝑡
o
r
i
g
=
∑
𝑒
:
label
⁡
(
𝑒
)
=
𝑡
𝑛
𝑒
,
n
t
orig
	​

=
e:label(e)=t
∑
	​

n
e
	​

,

even when only selected counter coordinates receive token-moment constraints. This allows selective strengthening without discarding information about omitted places.

There is an important qualification: rational token-flow constraints do not automatically dominate your existing integer state-equation method. Preserve the same integrality treatment, modular deductions, or previously obtained certificates when making that comparison.

4. The useful implementation result: box guards give max-flow subproblems

The preceding formulation looks like a potentially large LP. For your current interval setting, most of those variables need not enter the master solver at all.

Suppose the abstract edge domain is a box:

ℓ
𝑒
,
𝑝
≤
𝑥
𝑝
≤
𝑢
𝑒
,
𝑝
,
ℓ
e,p
	​

≤x
p
	​

≤u
e,p
	​

,

where 
𝑢
𝑒
,
𝑝
u
e,p
	​

 may be infinite.

After the master solver proposes firing counts 
𝑛
𝑒
n
e
	​

 and endpoint 
𝑥
𝑓
x
f
	​

, the remaining constraints for each place 
𝑝
p are independent.

Define

𝑓
𝑒
,
𝑝
=
𝑦
𝑒
,
𝑝
−
ℓ
𝑒
,
𝑝
𝑛
𝑒
.
f
e,p
	​

=y
e,p
	​

−ℓ
e,p
	​

n
e
	​

.

Then

	
0
≤
𝑓
𝑒
,
𝑝
≤
𝑐
𝑒
,
𝑝
,
𝑐
𝑒
,
𝑝
=
(
𝑢
𝑒
,
𝑝
−
ℓ
𝑒
,
𝑝
)
𝑛
𝑒
,
		
(4)
0≤f
e,p
	​

≤c
e,p
	​

,c
e,p
	​

=(u
e,p
	​

−ℓ
e,p
	​

)n
e
	​

,
(4)

with infinite capacity when the upper bound is absent.

Equation (2) becomes an ordinary flow-balance constraint:

	
∑
out
⁡
(
𝑞
)
𝑓
𝑒
,
𝑝
−
∑
in
⁡
(
𝑞
)
𝑓
𝑒
,
𝑝
=
𝑏
𝑞
,
𝑝
,
		
(5)
out(q)
∑
	​

f
e,p
	​

−
in(q)
∑
	​

f
e,p
	​

=b
q,p
	​

,
(5)

where

	
𝑏
𝑞
,
𝑝
=
	
[
𝑞
=
𝑞
0
]
𝑥
0
,
𝑝
−
[
𝑞
=
𝑞
𝑓
]
𝑥
𝑓
,
𝑝


	
−
∑
out
⁡
(
𝑞
)
ℓ
𝑒
,
𝑝
𝑛
𝑒
+
∑
in
⁡
(
𝑞
)
(
ℓ
𝑒
,
𝑝
+
Δ
𝑒
,
𝑝
)
𝑛
𝑒
.
		
(6)
b
q,p
	​

=
	​

[q=q
0
	​

]x
0,p
	​

−[q=q
f
	​

]x
f,p
	​

−
out(q)
∑
	​

ℓ
e,p
	​

n
e
	​

+
in(q)
∑
	​

(ℓ
e,p
	​

+Δ
e,p
	​

)n
e
	​

.
	​

(6)

That is a capacitated flow-feasibility problem on 
𝑄
Q.

4.1 An infeasible flow gives a linear cut

For any subset 
𝑆
⊆
𝑄
S⊆Q, a necessary condition is

	
∑
𝑞
∈
𝑆
𝑏
𝑞
,
𝑝
≤
∑
𝑒
∈
out
⁡
(
𝑆
)
𝑐
𝑒
,
𝑝
.
		
(7)
q∈S
∑
	​

b
q,p
	​

≤
e∈out(S)
∑
	​

c
e,p
	​

.
(7)

This follows by summing (5) over 
𝑆
S: incoming flow can only decrease the left-hand net outflow.

If the flow problem is infeasible, a minimum cut supplies a violated inequality of this form. Substituting (4) and (6) produces a linear inequality in the master variables 
𝑛
𝑒
,
𝑥
𝑓
n
e
	​

,x
f
	​

.

The certificate can be exceptionally small:

Plain text
place p
subset S of control cells
identifiers of the certified edge bounds

The checker reconstructs inequality (7). It does not trust a max-flow implementation.

This is a Benders-style decomposition: solve a small master problem, ask independent feasibility subproblems for violated cuts, and add only the necessary cuts. Benders decomposition itself is established; the potential contribution is the particular Petri-net relaxation and its refinement. 
Springer

4.2 Three valuable consequences

First, relational conclusions do not require relational subproblems. The per-place flows share the same firing-count variables. Combining their cuts with the target can establish relations such as

𝐶
300
−
𝐶
350
+
control offset
≤
0.
C
300
	​

−C
350
	​

+control offset≤0.

You are not restricted to proving coordinate bounds.

Second, moment integrality comes for free in this box-guard fragment. If 
𝑛
𝑒
,
𝑥
𝑓
,
𝑥
0
,
ℓ
,
𝑢
n
e
	​

,x
f
	​

,x
0
	​

,ℓ,u are integers, demands and finite capacities are integers. An integral augmenting-flow construction therefore supplies integral 
𝑓
f, hence integral 
𝑦
y, whenever the flow problem is feasible.

Thus you do not need to branch on thousands of moment variables. The integer difficulty remains in the firing counts, endpoint, and any additional non-network constraints.

Third, separation is complete for this fixed relaxation. For a fixed finite control graph and box bounds, flow balance plus all subset cuts characterize each per-place flow problem. There are finitely many such cuts. An exact separation loop therefore terminates for that fixed rational relaxation—either with infeasibility or with a solution admitting all the required per-place flows.

That is not a termination theorem for the entire reachability procedure. Refining the control partition can continue indefinitely.

4.3 Infinite capacities and zero-count edges

There is an important loss of precision:

𝑛
𝑒
=
0
n
e
	​

=0

does not force 
𝑦
𝑒
=
0
y
e
	​

=0 when the edge has an unbounded source domain. The homogeneous relaxation permits nonzero recession flow on an unused edge.

This is sound, but can be very weak.

A valid strengthening is the integer disjunction

(
𝑛
𝑒
=
0
∧
𝑦
𝑒
=
0
)
  
∨
  
(
𝑛
𝑒
≥
1
)
.
(n
e
	​

=0∧y
e
	​

=0)∨(n
e
	​

≥1).

In a branch where 
𝑛
𝑒
=
0
n
e
	​

=0, set its residual capacity to zero. Do not introduce an unjustified finite “big 
𝑀
M” as a marking bound.

The distinction matters: a flow algorithm may internally replace infinity by a value exceeding total auxiliary supply for that particular feasibility check. That is an implementation bound on a flow computation, not a claimed bound on Petri-net markings. A returned universal cut must not depend on pretending an actually infinite edge capacity is finite.

5. The dual view: control-dependent affine separators

The dual explains the proofs this relaxation can discover.

Associate an affine function with each control cell:

𝐹
𝑞
(
𝑥
)
=
𝑎
𝑞
⊤
𝑥
+
𝑏
𝑞
.
F
q
	​

(x)=a
q
⊤
	​

x+b
q
	​

.

A sufficient safety proof is:

	
𝐹
𝑞
0
(
𝑥
0
)
≤
0
,
		
(8)
F
q
0
	​

	​

(x
0
	​

)≤0,
(8)
	
𝐹
𝑟
(
𝑥
+
Δ
𝑒
)
≤
𝐹
𝑞
(
𝑥
)
for every 
𝑥
∈
𝐷
𝑒
,
		
(9)
F
r
	​

(x+Δ
e
	​

)≤F
q
	​

(x)for every x∈D
e
	​

,
(9)

and

	
𝐹
𝑞
𝑓
(
𝑥
)
≥
1
for every target state in 
𝑞
𝑓
.
		
(10)
F
q
f
	​

	​

(x)≥1for every target state in q
f
	​

.
(10)

Every reachable state has potential at most zero, while every target state has potential at least one.

These are signed safety separators, not nonnegative ranking functions.

For a fixed nonempty rational domain 
𝐷
𝑒
=
{
𝑥
:
𝐻
𝑒
𝑥
≤
ℎ
𝑒
}
D
e
	​

={x:H
e
	​

x≤h
e
	​

}, condition (9) has the Farkas certificate

𝜇
𝑒
≥
0
,
μ
e
	​

≥0,
𝜇
𝑒
⊤
𝐻
𝑒
=
𝑎
𝑟
−
𝑎
𝑞
,
μ
e
⊤
	​

H
e
	​

=a
r
	​

−a
q
	​

,
	
𝜇
𝑒
⊤
ℎ
𝑒
≤
𝑏
𝑞
−
𝑏
𝑟
−
𝑎
𝑟
⊤
Δ
𝑒
.
		
(11)
μ
e
⊤
	​

h
e
	​

≤b
q
	​

−b
r
	​

−a
r
⊤
	​

Δ
e
	​

.
(11)

All constraints are linear in 
𝑎
,
𝑏
,
𝜇
a,b,μ, because the domain matrices are fixed.

For a target 
𝐻
𝑓
𝑥
≤
ℎ
𝑓
H
f
	​

x≤h
f
	​

, the corresponding certificate is

	
𝜆
≥
0
,
𝜆
⊤
𝐻
𝑓
=
−
𝑎
𝑞
𝑓
,
𝜆
⊤
ℎ
𝑓
≤
𝑏
𝑞
𝑓
−
1.
		
(12)
λ≥0,λ
⊤
H
f
	​

=−a
q
f
	​

	​

,λ
⊤
h
f
	​

≤b
q
f
	​

	​

−1.
(12)

Empty antecedents should receive separate infeasibility certificates.

Multiplying the count/moment balance equations by the offsets/slopes and combining them with the guard inequalities gives the same contradiction. This is the primal/dual connection.

For fixed terminal cell and fixed rational domains, this characterizes the associated nonincreasing affine-separator class. It does not characterize every inductive polyhedral invariant.

The trap to avoid

One might try to weaken (9) by assuming the invariant itself:

𝐹
𝑞
(
𝑥
)
≤
0
  
⟹
  
𝐹
𝑟
(
𝑥
+
Δ
𝑒
)
≤
0.
F
q
	​

(x)≤0⟹F
r
	​

(x+Δ
e
	​

)≤0.

That is a more general inductiveness condition. But if both the invariant coefficients and Farkas multipliers are unknown, their products make the synthesis constraints bilinear. Calling this a straightforward LP would be incorrect. The distinction is central in the classical Farkas-based invariant-generation literature. 
Theory of Computation

A practical progression is:

synthesize globally nonincreasing cell-affine separators;
retain proved facts as fixed background;
synthesize additional separators relative to that background;
refine cells when the current class is insufficient.
A limitation that should appear in the paper, not be hidden

For an edge whose data domain is just

𝑥
≥
𝑢
𝑒
,
𝑥
′
=
𝑥
−
𝑢
𝑒
+
𝑣
𝑒
,
x≥u
e
	​

,x
′
=x−u
e
	​

+v
e
	​

,

condition (9) is equivalent to

𝑎
𝑟
≤
𝑎
𝑞
componentwise
,
a
r
	​

≤a
q
	​

componentwise,
	
𝑎
𝑟
⊤
𝑣
𝑒
+
𝑏
𝑟
≤
𝑎
𝑞
⊤
𝑢
𝑒
+
𝑏
𝑞
.
		
(13)
a
r
⊤
	​

v
e
	​

+b
r
	​

≤a
q
⊤
	​

u
e
	​

+b
q
	​

.
(13)

The proof substitutes 
𝑥
=
𝑢
𝑒
+
𝑧
x=u
e
	​

+z, 
𝑧
≥
0
z≥0.

Consequently, slopes must be equal inside a strongly connected component of an unrestricted control graph.

If that control graph is already represented by a single one-hot token in the original net and is strongly connected, the resulting potential is just

𝑎
⊤
𝑥
+
∑
𝑞
𝑏
𝑞
 
𝑚
𝑞
,
a
⊤
x+
q
∑
	​

b
q
	​

m
q
	​

,

an ordinary global linear function of the original places. Its monotonicity is often already captured by the original state equation.

Therefore, offsets alone are not the breakthrough. Additional power comes from phase-dependent slopes, joint control abstractions, enabling-sensitive cell splits, and background constraints. With bounded or relational edge domains, the simple SCC slope-equality argument no longer applies.

6. Your missed SER proof fits this picture—but should not define it

Let

𝑥
=
𝐶
300
,
𝑦
=
𝐶
350
.
x=C
300
	​

,y=C
350
	​

.

Your disjunction can be written as one cell-dependent scalar inequality:

	
𝐹
𝑞
(
𝑥
,
𝑦
)
=
{
𝑥
+
𝑦
	
𝑞
∈
P
r
e
,


𝑦
	
𝑞
∈
L
o
w
,


𝑥
−
𝑦
+
[
𝑞
=
(
150
,
200
)
]
	
𝑞
∈
H
i
g
h
,
𝐹
𝑞
≤
0.
		
(14)
F
q
	​

(x,y)=
⎩
⎨
⎧
	​

x+y
y
x−y+[q=(150,200)]
	​

q∈Pre,
q∈Low,
q∈High,
	​

F
q
	​

≤0.
(14)

Because 
𝑥
,
𝑦
≥
0
x,y≥0, the first branch says both counters are zero, and the second says 
𝑦
=
0
y=0.

For the two High transitions you described:

transfer350 decreases 
𝑥
−
𝑦
x−y by one and increases the control offset by one;
transfer300 increases 
𝑥
−
𝑦
x−y by one and decreases the control offset by one.

The net potential change is zero in both cases.

The integer target implies

𝑦
≥
1
,
𝑥
−
𝑦
≥
1
,
y≥1,x−y≥1,

so each branch contradicts the target.

The important automation experiment is not whether you can program these three formulas. It is whether the solver can recover their structure starting from original place/transition incidence and a generic control abstraction.

I would test this by allowing unconstrained coefficient columns for original places, including pending and delivered responses, and solving for the coefficients and offsets. Equal coefficient vectors can be grouped into phases after discovery.

Do not predefine “Pre/Low/High,” response-number-specific features, or the indicator offset. They are the expected output of this diagnostic experiment.

Also, a valid inductive disjunction does not necessarily satisfy the stronger globally nonincreasing condition (9) on every abstract state. Some original edges may require previously proved zero-counter facts or a finer partition. The described edges support the calculation above; I have not checked your full 202 cases.

What I actually tested

I built an independent five-mode, two-counter toy with the same phase/counter mechanism. The synthesis recovered:

(
1
,
1
)
,
(
0
,
1
)
,
(
1
,
−
1
)
(1,1),(0,1),(1,−1)

as the phase slopes and a unit offset at the intermediate High state. Its local Farkas obligations were checked with exact rational arithmetic.

I also implemented the per-place max-flow separator. It agreed with the corresponding numerical auxiliary LP on 400 small generated subproblems, checked 285 returned cut obstructions exactly, and accepted summaries from 200 independently generated enabled walks.

Those are algebraic/unit tests, not benchmark results. They establish neither scalability nor novelty.

Research probes, exact-checking code, and results

7. One implementable refinement engine

I would implement the following structure, rather than a new list of timed methods.

Plain text
solve(problem, budget):
    normalize original net and property
    B := checked background facts
    A := initial certified control/cell abstraction
    cuts := reusable checked arithmetic constraints

    for each target disjunct, preserving whole-property polarity:
        for each possible terminal cell qf:
            while budget remains:
                M := original state equation
                     + abstract control-flow balance
                     + target in qf
                     + checked cuts

                result := solve_master(M)

                if result is checked infeasibility:
                    mark this terminal-cell obligation proved
                    break

                if result is unknown:
                    perform a bounded refinement/search step
                    continue

                candidate := result.summary
                added_cut := false

                for place p in a prioritized, eventually fair order:
                    outcome := separate_token_flow(A, p, candidate)
                    if outcome supplies a checked violated cut:
                        add cut to M and cache
                        added_cut := true

                if added_cut:
                    continue

                attempt := schedule_and_replay(candidate, original_net)
                if attempt supplies an exact target-reaching execution:
                    return corresponding definitive whole-property answer

                refinement := refine_from_obstruction(A, B, attempt, candidate)
                if no useful refinement fits the remaining budget:
                    return UNKNOWN for this obligation

                A := checked refinement
                preserve old cuts through the refinement map

    combine all proved obligations at the original property layer

The master can begin rationally and use your existing integer and modular machinery as necessary. Numerical solvers may propose candidates, bases, or rays; the arithmetic certificate checker remains authoritative.

7.1 Discover controls by certified boundedness, not total net size

The current “enumerate subsets only when the net has at most 12 places” rule is a major limitation. A large net may contain a very small, excellent controller.

Search for nonnegative subinvariants

𝑤
≥
0
,
𝑤
⊤
𝐶
≤
0.
w≥0,w
⊤
C≤0.

Then every reachable marking satisfies

𝑤
⊤
𝑚
≤
𝑤
⊤
𝑚
0
=
𝐾
,
w
⊤
m≤w
⊤
m
0
	​

=K,

and each 
𝑝
p with 
𝑤
𝑝
>
0
w
p
	​

>0 is bounded by

𝑚
𝑝
≤
⌊
𝐾
/
𝑤
𝑝
⌋
.
m
p
	​

≤⌊K/w
p
	​

⌋.

A concrete candidate search is to normalize 
𝑤
𝑝
=
1
w
p
	​

=1, minimize 
𝑤
⊤
𝑚
0
w
⊤
m
0
	​

, and verify the resulting rational vector exactly. Structural one-hot components should be tried first.

The budget should concern the resulting reachable abstract control graph, not merely the number of selected coordinates. A one-hot controller with 100 places has 100 modes, not 
2
100
2
100
. Conversely, several tiny independent bounded components can have an enormous product.

7.2 Refine enabling information when token flows still admit a spurious summary

Suppose a proposed scheduling attempt first fails because transition 
𝑡
t needs 
𝑚
𝑝
≥
𝑘
m
p
	​

≥k.

A natural refinement is to split the relevant source cell into

𝑚
𝑝
≤
𝑘
−
1
and
𝑚
𝑝
≥
𝑘
.
m
p
	​

≤k−1andm
p
	​

≥k.

This creates finite lower/upper bounds on edge domains and hence new capacities in the token-flow subproblems.

However, one such split need not eliminate every execution with the same count vector, or even every abstract realization of the failed word. Check whether the obstruction was actually removed.

For a fixed failed word, sufficiently precise position/counter refinement can make its feasibility exact. Turning failed traces into refined abstractions is established methodology; your contribution would be selecting and reusing refinements through this flow relaxation. 
Springer
+1

7.3 Couple counters only when the box relaxation is the bottleneck

The box-guard formulation gives the cheap max-flow core. A relational background fact such as

𝑥
𝑝
+
𝑥
𝑟
≤
𝐾
x
p
	​

+x
r
	​

≤K

couples moment variables on an edge.

Add such constraints selectively as small LP blocks. This is a refinement of the same relaxation, not a separate proof engine. Keep the full coupled LP as a reference implementation to measure whether decomposition saves time without sacrificing relevant proof power.

7.4 Promote the original state equation to a background invariant

There is a useful immediate improvement to your current interval certificates.

Let

𝐸
(
𝑚
)
≡
∃
𝑛
∈
𝑁
𝑇
:
  
𝑚
=
𝑚
0
+
𝐶
𝑛
.
E(m)≡∃n∈N
T
:m=m
0
	​

+Cn.

This is itself inductive: after firing 
𝑡
t, replace 
𝑛
n by 
𝑛
+
𝑒
𝑡
n+e
t
	​

.

Your current design requires a region union 
𝐽
J to be inductive by itself, then checks target exclusion using 
𝐽
∩
𝐸
J∩E. You can instead certify

𝐽
(
𝑚
)
∧
𝐸
(
𝑚
)
∧
enabled
⁡
𝑡
(
𝑚
)
  
⟹
  
𝐽
(
𝑚
+
𝐶
𝑡
)
.
J(m)∧E(m)∧enabled
t
	​

(m)⟹J(m+C
t
	​

).

Together with initial inclusion, this proves 
𝐽
∩
𝐸
J∩E invariant.

This can exclude impossible source states during consecution, not just during final target checking. It is standard relative induction, not a novelty claim, but it could be a high-value implementation improvement.

When using existential background descriptions in local arithmetic, introduce their witness variables correctly. Do not identify an arbitrary source-state equation witness with the final execution’s firing-count vector.

8. Raw SER: prove membership, not failure to find nonmembership

The raw problem has a particularly clean contract:

Completed
⁡
(
𝑚
)
  
⟹
  
𝑟
(
𝑚
)
∈
𝑆
,
Completed(m)⟹r(m)∈S,

where

𝑆
=
⋃
𝑗
=
1
𝑘
(
𝑏
𝑗
+
𝐵
𝑗
𝑁
𝑑
𝑗
)
.
S=
j=1
⋃
k
	​

(b
j
	​

+B
j
	​

N
d
j
	​

).

Coordinate and pair-difference bounds are useful search heuristics, but cannot establish this contract in general.

I would add a constructive semilinear inclusion certificate.

8.1 Keep execution-summary variables

Let 
𝑅
(
𝑤
)
R(w) be the current sound relaxation of completed executions. The vector 
𝑤
w can contain:

𝑤
=
(
𝑚
,
𝑛
)
w=(m,n)

for the cut-based master, or

𝑤
=
(
𝑚
,
𝑛
,
𝑦
)
w=(m,n,y)

for the lifted formulation.

Every actual completed execution supplies an integer 
𝑤
w satisfying 
𝑅
R.

Partition those integer solutions into finitely many certificate cells 
𝐷
ℓ
(
𝑤
)
D
ℓ
	​

(w). For each cell, choose a serial component 
𝑗
ℓ
j
ℓ
	​

 and provide an affine generator witness

	
𝑧
ℓ
(
𝑤
)
=
𝑈
ℓ
𝑤
+
𝑣
ℓ
𝑑
ℓ
,
𝑑
ℓ
>
0.
		
(15)
z
ℓ
	​

(w)=
d
ℓ
	​

U
ℓ
	​

w+v
ℓ
	​

	​

,d
ℓ
	​

>0.
(15)

Check, on 
𝑅
∧
𝐷
ℓ
R∧D
ℓ
	​

, that

	
𝑈
ℓ
𝑤
+
𝑣
ℓ
≥
0
,
		
(16)
U
ℓ
	​

w+v
ℓ
	​

≥0,
(16)
	
𝑈
ℓ
𝑤
+
𝑣
ℓ
≡
0
(
m
o
d
𝑑
ℓ
)
,
		
(17)
U
ℓ
	​

w+v
ℓ
	​

≡0(modd
ℓ
	​

),
(17)

and

	
𝐵
𝑗
ℓ
(
𝑈
ℓ
𝑤
+
𝑣
ℓ
)
=
𝑑
ℓ
(
𝑟
(
𝑚
)
−
𝑏
𝑗
ℓ
)
.
		
(18)
B
j
ℓ
	​

	​

(U
ℓ
	​

w+v
ℓ
	​

)=d
ℓ
	​

(r(m)−b
j
ℓ
	​

	​

).
(18)

Then 
𝑧
ℓ
(
𝑤
)
∈
𝑁
𝑑
𝑗
ℓ
z
ℓ
	​

(w)∈N
d
j
ℓ
	​

	​

, and (18) proves membership in that serial component.

The cells must cover all integer solutions of 
𝑅
R, not merely the examples encountered during search.

These are target-coverage cells. They do not each have to be inductive.

8.2 Why summary-dependent witnesses are useful

A serial generator count may be easy to express using transition counts but awkward to recover from the response vector alone.

Allowing 
𝑧
z to depend on 
𝑛
n, and occasionally on 
𝑦
y, can avoid eliminating useful auxiliary information and can make the certificate smaller. It does not require runtime certificate accumulation: the summary variables are mathematical witnesses supplied by the existence of an execution.

For example,

𝑆
=
{
(
𝑥
,
𝑦
)
:
0
≤
𝑥
≤
𝑦
}
S={(x,y):0≤x≤y}

has generators 
(
1
,
1
)
(1,1) and 
(
0
,
1
)
(0,1), with witness

𝑧
1
=
𝑥
,
𝑧
2
=
𝑦
−
𝑥
.
z
1
	​

=x,z
2
	​

=y−x.

An invariant proving 
𝑦
≥
𝑥
y≥x now gives a direct semilinear-membership proof.

This is illustrative, not a claim about the exact serial set in your example.

8.3 Discovery algorithm

For a fixed relaxation and candidate cell:

Plain text
try_component(R, D, base b, generator matrix B):
    derive equality/lattice information from R ∧ D
    propose affine generator counts z(w)
    prove B z(w) = response(w) - b
    prove z(w) >= 0
    prove z(w) is integer on all integer solutions of R ∧ D

    if all obligations check:
        return membership leaf
    otherwise:
        return failure information for splitting or abstraction refinement

Start with denominator-one witnesses. Use integer linear algebra—such as Smith/Hermite normal forms—to obtain particular solutions, kernel structure, and divisibility obligations. Then use rational synthesis for the remaining coefficient choices, followed by exact verification.

For an equality lattice 
𝑤
=
𝑤
0
+
𝐾
𝜉
w=w
0
	​

+Kξ, a sufficient divisibility check is

𝑈
𝑤
0
+
𝑣
≡
0
(
m
o
d
𝑑
)
,
𝑈
𝐾
≡
0
(
m
o
d
𝑑
)
.
Uw
0
	​

+v≡0(modd),UK≡0(modd).

When that is too strong, split into residue cells.

Finite component choice and cell discovery remain genuine search problems. Do not advertise this as a polynomial-time replacement for arbitrary semilinear reasoning.

8.4 Why cones and congruences alone are insufficient

The monoid generated by 
2
2 and 
3
3 excludes 
1
1, although its rational cone and generated integer lattice do not exclude 
1
1.

So

𝑟
−
𝑏
∈
cone
⁡
(
𝐵
)
r−b∈cone(B)

plus lattice compatibility is not a sufficient membership test. The nonnegative integer generator witness is essential.

8.5 A useful representation theorem

There is a reassuring theoretical boundary here.

For a fixed Presburger-definable relaxation 
𝑅
R, suppose every integer 
𝑤
∈
𝑅
w∈R has a witness 
𝑗
,
𝑧
j,z satisfying the serial-membership relation. Presburger definable choice and cell decomposition give a finite piecewise-affine witness, with appropriate congruence conditions. Thus a sufficiently general version of the certificate language above is representation-complete for that fixed inclusion problem. This follows from established Presburger results; it is not a new completeness result for Petri-net reachability. 
arXiv
+1

Functional witness synthesis itself is also an active, explicit research topic; the KR 2025 work on Presburger functional synthesis is relevant. The contribution here would be exploiting execution relaxations and generator structure efficiently, not inventing Skolem-function synthesis. 
arXiv

This is the raw-SER claim I would investigate: direct, checked inclusion in a supplied semilinear contract, avoiding complement/DNF construction at that interface. It does not avoid the cost of constructing the supplied serial union in the first place.

9. Certificate design and soundness hazards

Your current emphasis on exact replay and independent negative checking is the right foundation. The next certificate format should remain tied to the original semantics.

9.1 A small proof kernel for the new method

A negative certificate can consist of:

Plain text
original net hash and original property hash
property polarity and disjunct mapping
certified control/cell partition
certified background bounds
token-flow cuts:
    place + control subset + edge-bound references
optional coupled-domain Farkas cuts
integer branching / modular deductions
final exact arithmetic infeasibility proof

The checker reconstructs the relevant matrices from the original net.

For rational infeasibility of 
𝐴
𝑧
≤
𝑏
Az≤b, verify

𝜆
≥
0
,
𝜆
⊤
𝐴
=
0
,
𝜆
⊤
𝑏
<
0.
λ≥0,λ
⊤
A=0,λ
⊤
b<0.

Equality rows can use signed multipliers. All arithmetic in the checker should use arbitrary-precision integers/rationals.

For integer branching, branches such as

𝑎
⊤
𝑧
≤
𝑘
∨
𝑎
⊤
𝑧
≥
𝑘
+
1
a
⊤
z≤k∨a
⊤
z≥k+1

are exhaustive only when 
𝑎
⊤
𝑧
a
⊤
z is known integer. Normalize denominators and strict inequalities explicitly.

A timeout, failed rational reconstruction, incomplete cut separation, or exhausted refinement budget is Unknown, never a negative result.

9.2 Review of the supplied interval transformer

The shown pre-then-post transformer is sound for ordinary box abstraction under canonical valid inputs. In particular, consuming before producing handles self-loops correctly; an input/output self-loop must still satisfy its input requirement.

I would audit the surrounding representation for:

aggregation of duplicate pre-arcs and post-arcs;
valid nonnegative weights and initial bounds;
signed effect construction without unsigned underflow;
preservation of exact control coordinates;
explicit rejection/Unknown on lower-bound overflow;
upper overflow becoming infinity only in an overapproximating position.

If duplicate arcs are processed independently without normalization, sequential subtraction is not generally the intended representation-level enabling check.

For union invariants, the postimage must be covered by the region union. Intersection with some destination region is not enough. Requiring containment in one destination box is sound but incomplete; more general coverage needs its own checked decomposition.

9.3 Projection subtleties

Your described projection is a sound negative abstraction when it preserves target coordinates and overapproximates every original firing.

Deduplicate projected transitions by their full projected pre/post behavior, not merely their net effect.

Dropping projected stuttering is fine for the old marking-reachability abstraction, but not for the new token-flow construction when those transitions change tracked counters outside the control projection.

A projected positive path needs actual original transition choices. Failure of a greedy lift does not establish that no lift exists.

9.4 Enabling in accelerated witnesses

For a word 
𝑤
w, use both its effect 
Δ
𝑤
Δ
w
	​

 and its enabling hurdle 
𝐻
𝑤
H
w
	​

. Composition obeys

𝐻
𝑢
𝑣
=
max
⁡
(
𝐻
𝑢
,
𝐻
𝑣
−
Δ
𝑢
)
.
H
uv
	​

=max(H
u
	​

,H
v
	​

−Δ
u
	​

).

For 
𝑘
≥
1
k≥1,

𝐻
𝑤
𝑘
=
𝐻
𝑤
+
(
𝑘
−
1
)
(
−
Δ
𝑤
)
+
.
H
w
k
	​

=H
w
	​

+(k−1)(−Δ
w
	​

)
+
.

The zero-repetition case is separate. These summaries support exact compressed replay; they are not a substitute for checking original enabling. Hurdle-based word reasoning is already part of the relevant PDR literature. 
Springer

9.5 Independence should include the semantic boundary

Two arithmetic checkers can agree on a wrongly normalized property.

Include tests where the independent checker starts from original PNML/XML or a separately validated canonical representation. Check whole-property EF/AG polarity, completion conditions, and disjunct aggregation—not only the arithmetic proof payload.

Useful adversarial mutations include omitted transitions, altered enabling weights, wrong terminal cells, uncertified bounds, negative Farkas multipliers, invalid divisibility claims, and finite-capacity substitutions for genuinely unbounded edges.

10. Failure cases and limits worth testing deliberately
A safe net with no unrefined monotone affine separator

Take one place, initial marking 
0
0, and a transition with precondition 
1
1 and postcondition 
2
2. The target is 
𝑥
≥
1
x≥1.

The transition is initially disabled, so the target is unreachable.

For one unrestricted control cell, an affine nonincreasing function 
𝐹
(
𝑥
)
=
𝑎
𝑥
+
𝑏
F(x)=ax+b must satisfy 
𝑎
≤
0
a≤0, while separating 
0
0 from every 
𝑥
≥
1
x≥1 requires incompatible behavior. The unrefined relaxation fails.

Splitting into 
𝑥
=
0
x=0 and 
𝑥
≥
1
x≥1 permits the piecewise constant separator 
0
0 and 
1
1.

This is a mechanism test, not a claimed win over traps or other existing techniques.

Spurious cycles remain possible

Flow feasibility does not establish an executable ordering. Counts may describe cycles whose enabling resources cannot be supplied in the required order.

Even integer counts, integral moment flows, and zero-count gating do not make the relaxation exact.

Congruence and monoid holes remain integer problems

A rational relaxation cannot prove every parity or divisibility obstruction. Keep your modular machinery. Direct semilinear membership may require many residue cells or nontrivial piecewise witnesses.

Large bounded concurrency may defeat explicit control refinement

A net with many independently bounded components may have an enormous useful joint control space. Your lack of a decision-diagram engine is relevant here: it is entirely possible that the proposed method helps unbounded counter/control examples while losing badly on large bounded concurrency.

That would be a legitimate, narrower result—but not evidence of broad MCC superiority.

Stronger invariant classes may win

A nonincreasing scalar separator is more restrictive than an arbitrary inductive polyhedron. A mature disjunctive invariant generator or PDR implementation may find proofs this method misses.

Leroux’s Presburger-inductive-invariant characterization for nonreachability does not make a small fixed template or partition budget complete. 
Logical Methods in Computer Science

Proof overhead may erase discovery gains

Track certificate generation, serialization, exact checking, coefficient bit lengths, and memory—not just the untrusted solver’s time. Sparse, reusable cut identifiers are valuable partly because they may keep this cost low.

11. A fair experimental program
11.1 Freeze what is now development data

All currently seen MCC evaluation families are now development data. Preserve the old split in the historical record, but do not keep calling it held out after further tuning.

Create a new, sealed family-level split before changing the refinement policy. Generated variants and scaling instances from one template belong to the same family.

Use the public MCC model distribution and current competition artifacts to make selection and tool configurations reproducible; current MCC pages provide downloadable tool artifacts suitable as starting points, not as substitutes for your own matched experiment. 
YannTM
+1

11.2 Separate two research questions

General reachability track: original ordinary P/T nets with original linear properties, including easy cases, positive cases, and large bounded models.

Semilinear-contract track: original request-tracking nets plus supplied serial unions, evaluating direct inclusion and counterexample discovery.

Do not use the second track to imply broad superiority on the first.

For SER, report distinct denominators:

Unit	Required reporting
Original programs	All 47, including export failures/timeouts.
Successfully exported originals	The 39-program backend-only track.
Generated harder programs	All 24, grouped by generation family.
Scaling cases	All 6 end-to-end; the 5 exported cases separately.
Simplified backend disjuncts	Diagnostic workload, not 218 independent programs.

Keep the two duplicate small-suite properties for certificate regression, but use distinct properties for headline coverage.

11.3 Baselines that answer the right questions

The indispensable external comparisons are fully installed current SMPT, ITS-Tools, TAPAAL’s appropriate untimed P/T engine, and a documented LoLA configuration. Pin exact versions and use author-recommended settings. ITS-Tools’ MCC wrapper and TAPAAL’s distribution explicitly expose relevant installation/engine choices; using the wrong frontend or missing dependencies would invalidate the comparison. 
GitHub
+2

For positive search, FastForward is a relevant additional comparison where target encodings match. Its TACAS 2021 work already uses reachability relaxations to guide search, so a new heuristic needs to be compared against that idea rather than against unguided BFS alone. 
Department of Computer Science

Coverability-only configurations should be compared only on semantically appropriate targets.

Internally, the decisive ablations are:

Configuration	Question answered
Old solver, full equal budget	Is there an actual improvement over the existing backend?
Old solver with only the new scheduler	Are gains/losses scheduling effects?
Existing interval/projection methods	How much comes from the current additions?
Fixed control + full token-moment LP	Does the relaxation itself help?
Fixed control + lazy max-flow cuts	Does decomposition improve cost?
No adaptive control refinement	Is refinement responsible for additional proofs?
No integer strengthening / zero-count gating	Which integer mechanisms matter?
Same control partition with conventional affine/polyhedral analysis	Is the contribution more than a different implementation of conditional invariants?

The last comparison is particularly important given VMCAI 2025 disjunctive affine synthesis.

11.4 Two fairness tracks, not one compromised comparison

Run:

End-to-end best-tool track. Original inputs; each tool may use its standard reductions and portfolio within the same resource budget.

Common-intermediate-representation track. Identical exported problems and preprocessing boundaries; compare backend algorithms.

For raw SER, end-to-end time includes serial-set construction, export, solving, and checking. Otherwise, avoiding complement cost can disappear from the measurement—or appear as an unfair preprocessing advantage.

For multiple properties per model, report cold per-property runs and batch/amortized runs separately. Shared preprocessing and learned cuts can be useful, but every tool should receive an appropriate opportunity for reuse.

11.5 Resources and repetition

Use a dedicated Linux host with fixed memory limits and pinned physical cores. A process-tree-aware harness such as BenchExec is appropriate; it is designed to account for subprocess resource use and isolate runs. 
GitHub

I would report a fast track retaining your operational two-second budget, plus longer budgets such as 10, 60, and 300 seconds. Exact choices should be frozen before evaluation.

Measure both wall time and total CPU time, including children. Separate one-core comparisons from multicore portfolio comparisons.

Use randomized blocked run order and repeated runs. Do not select the fastest successful repetition as the result. Report instability explicitly, especially near timeouts.

A common 200,000-state cap is not a fair cross-tool resource limit: a decision-diagram node, explicit marking, and LP row are not comparable units. Common time/memory limits are the primary comparison; internal caps are reported configuration choices.

11.6 Outcomes and mechanism measurements

Headline results should include certified solved counts at each budget, separated by positive and negative answers, with paired wins/losses by family.

Treat timeouts as censored observations. Runtime comparisons only on commonly solved cases are useful but secondary because they exclude precisely the hard wins.

Confidence intervals should respect family clustering rather than treating all properties as independent samples.

For this research direction, collect:

∣
𝑄
∣
,
∣
abstract edges
∣
,
number of cuts
,
number of refined predicates
,
∣Q∣,∣abstract edges∣,number of cuts,number of refined predicates,

along with master size, separation calls, LP-block sizes, integer branches, proof size, checking time, and coefficient bit lengths.

Most importantly, record why the new solver won. Was it a control-phase cut, a finite-capacity enabling cut, a modular obstruction, or simply more time spent searching?

11.7 Add mechanism benchmarks without replacing real ones

Create parameterized families that vary independently:

phase count and control-product size;
offset magnitude;
finite enabling resources and misleading cycles;
parity and semigroup holes;
unbounded request accumulation;
safe semilinear contracts requiring more than lock-based reasoning.

Pair safe instances with closely related unsafe instances. Otherwise a method can look strong by specializing to negative examples.

These families explain behavior. They should not replace untouched public families.

12. What I would implement first—and what would make me stop
First: establish the mathematical and certificate core

Implement the fixed-control token-moment formulation as a reference, then the per-place flow separator and cut checker.

Required tests are:

every generated concrete run satisfies the lifted constraints;
max-flow separation agrees with the full box-guard formulation;
violated cuts reject the candidate and are reconstructed independently;
zero-count/unbounded-edge cases behave as intended;
original enabling survives all abstraction steps.

The attached probes provide a starting algebra check, not a production implementation.

Second: test expressiveness before tuning a scheduler

Recover the missed SER proof from original incidence information without response-specific templates.

Then run fixed-control and refined variants on all currently seen families, standalone with equal budgets. Inspect actual proof mechanisms on the remaining Peterson/Lamport/TCP cases rather than assuming they need the same kind of invariant.

This stage should answer whether the method adds useful proof power outside tiny phase examples.

Third: add direct semilinear inclusion

Implement denominator-one affine generator witnesses first, followed by certified lattice/residue handling.

The meaningful milestone is proving nontrivial safe raw instances that the present raw engine leaves unknown, while retaining counterexample discovery. Merely proving an obvious locked family would not establish a general contribution.

Fourth: run the sealed comparison

Only after the algorithm, tool configurations, and budgets are frozen should the new held-out families be exposed.

As an internal project gate—not a conference acceptance rule—I would require either:

repeatable new proofs across several unrelated general-net families with acceptable overhead; or
substantial end-to-end wins on diverse semilinear-contract instances, including safe cases, with a clearly narrower claim.

If the outcome is “37/37 remains impressive, MCC stays unchanged, and only hand-shaped SER examples improve,” I would not present the result as a broadly stronger reachability backend.

Bottom line

The best next step is not another abstract domain added to portfolio-v2. It is a control-indexed token-flow relaxation, solved by lazy per-place min-cut separation, with refinement of the same control abstraction.

Its strengths are unusually concrete:

a direct execution-to-constraints soundness proof;
a cheap graph-theoretic core for interval guards;
compact negative certificates;
an affine-invariant dual that explains discovered proofs;
selective extension to relational guards;
a natural route to direct semilinear-contract inclusion.

Its weaknesses are equally concrete: coarse strongly connected control can collapse back to state-equation strength; ordering remains abstracted; integer and semigroup obstructions remain; control products can explode.

That is a research direction worth implementing and trying to falsify. The algorithmic structure is promising; the broad performance advantage and publication-level novelty are still hypotheses that the next experiments must earn.