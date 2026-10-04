# Independent assessment of the completed Pro review

The full substantive response and visible citations are saved in answer.md as a browser DOM transcription. The UI reports 46m6s of work and exposes response rating/regeneration controls; the earlier challenge error was an observation failure. No duplicate request was submitted.

## Findings checked against local evidence

- scripts/accelerated_bmc.py:46–99 discovers a fixed vocabulary, regenerates a formula at each bound and starts a fresh Z3 process. Exhausted bounded schemes return unknown. This confirms that the experiment does not test persistent dynamic ABMC. The Rust incremental encoder alone does not supply an incremental solver session.
- src/scheme_search.rs:99–160 enumerates word sequences with a FIFO agenda and calls native arithmetic separately on target and feasible-prefix problems. Comparing it with joint SMT path selection does not isolate arithmetic backend performance.
- src/reduced_bfs.rs:13,24–41 caps closure at 200,000 states and verifies a finite-closure result by rerunning explicit search. A compressed symbolic negative certificate would require a different checking mechanism to preserve compression.
- research/frontier-expansion-development-v1/report.md records 960 audited rows: expanded and DFS variants each solve the same 94 positives, with no complementary portfolio coverage. Stop growth-factor tuning absent a materially different mechanism; retain the experiment and its checks.
- research/portfolio-reduced-linux-v1/report.md records the single-run 135/129/97/128 comparison, no paired losses, and six missing-counter warnings. It does not establish broad superiority. The current repeated suite is still running and was not used in this assessment.

## Mathematical assessment

The fixed-word boundedness argument is valid conditional on a global K bound: if a reachable execution w^r has nonzero integer effect delta[p], both endpoints in [0,K] imply r*abs(delta[p]) <= K. Zero-effect repetition visits no new markings after its first traversal. This limits large fixed-word repetitions; it does not rule out deep paths, ordinary BMC or richer relation learning. DNAwalker boundedness on the exact frozen files has not been mechanically verified here.

The proposed transition-invariant ray diagnostic is sound for the state equation, final-marking target and a finite collection of frontier disjunctions: Cc=0, c>=0, and positive support intersecting each frontier let x0+k*c satisfy those disjunctions for sufficiently large k without changing the final marking. This is not proof of an actual spurious ray on our inputs, of escape from all future cuts, or of satisfying artificial model caps/other constraints.

Exact decision diagrams can share marking sets and preserve read guards. A negative result needs initial inclusion, transition closure and target exclusion. Partial closure cannot establish unreachability. Variable order, residual transition-set growth, numeric range, signed target intersection and witness extraction can erase the expected advantage.

## Proposals and unverified claims

ITS-Tools qualification and a predeclared original-input comparison are the best next discriminator before a custom symbolic engine. This is a proposed experiment, not measured evidence that ITS or a Rust implementation wins. The suggested shared residual-transition representation has close prior-art overlap (implicit relations, conditional locality, recursive reachability and libDDD); novelty is unproven.

The reviewer reports 69 Python checks plus one unavailable fixture, and a separate symbolic prototype agreeing on 1,000 small bounded nets / 2,697 markings / 3,000 target queries. The three downloadable probe artifacts have not yet been collected or executed locally. These numbers remain reviewer-reported. The official-model metadata, additional saturation papers and newer LoAT/TRL references have not been independently read and verified in this assessment.

## Next work

1. Preserve the live six-block benchmark suite and its frozen configurations; collect/audit only after the whole suite terminates.
2. Independently inspect ITS-Tools documentation/source and pin a reproducible version. Qualify exact property selection, EF/AG polarity, signed arithmetic, original-input cost and single-property versus shared-query execution before registration. No remote setup while the suite is live.
3. Classify existing development survivors on exact hashed models, mechanically establish conservation/bounds where possible, and separate explicit stage caps from representation failures. Reserved families remain untouched.
4. Run an established symbolic baseline before deciding on a custom Rust rewrite. Keep both current combined and original frozen native controls. If pursuing acceleration, compare genuine incremental/static/dynamic approaches and published LoAT; compare arithmetic backends only on identical fixed schemes.

The review supports a change in experimental priority, not a publication claim. The goal remains incomplete.
