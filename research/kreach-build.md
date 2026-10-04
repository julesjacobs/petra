# Native KReach build

Upstream: <https://github.com/dixonary/kosaraju>, commit `48b41f249bc0f93707402b2c11b21024f041a286`.
This is the external Haskell implementation of Kosaraju reachability, distinct from the Rust bounded path-scheme engine.

Pinned upstream dependencies:

| Repository | Commit |
|---|---|
| dixonary/vass | 21020e8246353f14042c4e8070a6af093e2aebf2 |
| dixonary/duvet | 1cb22f34ed52ed5f8ca6ce639696cdc7c4c4e1f0 |
| dixonary/karp-miller | cf24259b56dc36f30ab8f4f6e19a31709cbf1038 |

The original Stack configuration specifies GHC 8.6.5 and SBV 8.5. This machine has native GHC 9.14.1 and cabal-install 3.16.1.0 in `~/.ghcup/bin`. The native adaptation uses SBV 14.5, so it is not a reproduction of the paper's exact historical toolchain. Optimization is `-O2`.

Compatibility changes:

- Generate Cabal files for the pinned auxiliary packages, whose repositories supply only package.yaml. Omit unused diagrams dependencies and the unused KarpMiller.Render module. Algorithm modules remain present.
- Replace SBV's removed `mkExistVars`/`mkForallVars` interface by free model variables and `ForallN`, with the runtime dimension reflected through `someNatVal`. Preserve the quantified formula for minimal nonnegative Diophantine solutions exactly.
- Replace the removed `System.Environment.Blank.getEnv` interface by `System.Environment.lookupEnv`, and `sbvAvailableSolvers` by `getAvailableSolvers`.
- Hide SBV’s newly exported `project` name to retain the local function of that name.

KReach still invokes an SMT solver internally for arithmetic. Use `KOSARAJU_SOLVER=z3` and provide the artifact virtual environment's `z3` on PATH. Use `+RTS -N1 -RTS` when comparing single-process backend timings: upstream otherwise enables all GHC capabilities by default.

## Input semantics

The CLI accepts MIST files, with `--reach --quiet FILE`. It treats the supplied target marking as exact reachability. All places must be enumerated after `vars`; initial and target entries use `p = N` separated by commas. Missing initial/target coordinates default to zero.

**The upstream MIST parser ignores rule guards.** Its pre/post arcs come from separate negative and positive assignment entries. Thus preserve a Petri-net transition by writing both `p' = p -PRE` and `p' = p +POST` when both arcs exist, including read arcs. Emitting only a net-effect assignment and an enabling guard loses read arcs and can change reachability. Each sign is stored separately by the parser; duplicate assignments for the same place and sign would overwrite, so aggregate each arc multiplicity beforehand.

Parser-only example preserving a read arc (the algorithm requires the additional transformation below):

```
vars
p q
rules
p >= 1 -> p' = p -1, p' = p +1, q' = q +1;
init
p = 1, q = 0
target
p = 1, q = 1
```

Signs must directly precede their magnitudes: `+1`, not `+ 1`. The upstream parser does not consume whitespace after a sign. Despite `--quiet`, trace output can appear before the final result. Read the last nonempty output line and require exit code zero.

## Required Petri-net encoding

**Passing read arcs directly to KReach is unsound.** Independently verified: the example above with initial `p = 0, q = 0` and target `p = 0, q = 1` returns `Reachable`, although its only transition is disabled. Upstream `makeRigid` uses zero net effects to remove rigid coordinates and does not retain positive read-arc requirements. This behavior follows its VASS-oriented implementation; the compatibility patch does not alter `makeRigid`.

Therefore split every Petri-net transition (including those added by the linear-target reduction) into two pure-effect transitions using one fresh global idle place and one private intermediate place per transition:

- Consume the original pre-arcs plus idle, and produce the private intermediate token.
- Consume that private token, and produce the original post-arcs plus idle.

Initial and target idle counts are one; all private counts are zero. This preserves atomicity and removes every overlap between pre and post support in each individual transition. Benchmark timings must include the effect of the resulting increase in dimensions and transitions.

Native compilation succeeded. Smoke results and discovered limitations are recorded below. No benchmark performance claims are made by this build note.

## Linear-target adapter

`scripts/kreach_adapter.py` freezes the original net, drains each original token into positive/negative accumulators for every target constraint, then cancels pairs. Inequalities additionally allow disposal of positive surplus; equalities do not. The exact final marking requires all original and accumulator places empty.

Every resulting transition is then split into a consume step and a produce step, with a global idle place and a private intermediate place. This prevents interleaving and removes pre/post overlap. The encoding is necessary: an upstream smoke test incorrectly accepted a disabled read arc because `makeRigid` discarded a zero-effect coordinate without retaining its enabling requirement. The benchmark therefore never feeds such overlapping transitions directly to KReach.

The conversion expands the net and occurs outside KReach's timed process; parsing and solving the expanded net are included. KReach verdicts do not export independently checked certificates. `python3 scripts/test_kreach_adapter.py` compares the full reduction, including transition splitting, with finite exhaustive reachability on 150 random signed-conjunction instances.

## Additional independently observed limitation

A compact finite-control encoding was tested through an optional `.kvass` reader added to `app/Main.hs`. Its input is the Haskell-readable integer tuple `(initialState, initialVector, finalState, finalVector, [(sourceState, destinationState, signedEffectVector)])`; Python tuple/list `repr` produces it directly. The reader constructs pure-effect VASS transitions and validates dimensions and nonnegative endpoint counters. This extension changes only input loading.

The following two-edge pure VASS has the obvious witness consisting of both edges, but this KReach build returns `Unreachable`:

```
(0, [1, 0], 0, [1, 1], [(0, 1, [-1, 0]), (1, 0, [1, 1])])
```

The printed internal VASS matches this input. Inspection identifies a likely upstream cause: bounded-transition refinement (`makeChain` in `src/Data/VASS/Reachability/Kosaraju.hs`) removes a bounded transition and inserts its vector as an adjoinment without adjusting component entry/exit control states to the removed edge's endpoints. This diagnosis is source-based; no semantic repair has been applied. The optional finite-state reader is therefore diagnostic, not a recommended benchmark shortcut.

In contrast, encoding that same consume/produce pair with a single state and idle/intermediate **counter places** returned the correct answer for both enabled and disabled cases:

```
(0, [1, 0, 1, 0], 0, [1, 1, 1, 0],
 [(0, 0, [-1, 0, -1, 1]), (0, 0, [1, 1, 1, -1])])
```

These smoke checks also passed: direct one-place increment by two reaches four; it does not reach three. Results of direct and finite-control tests are saved under `vendor/KReach/smoke/`. The full signed-target adapter followed by counter-place splitting timed out at 30 seconds on the small increment-by-two/reach-four example. This is observed behavior, not evidence of unreachability.

Build completed and the setup script was rerun successfully. Its embedded patch records every changed upstream source. GHC 9.14.1, Cabal 3.16.1.0, SBV 14.5, and Hackage index state `2026-08-11T20:49:38Z` are used. Final executable SHA-256: `9c1c6dfedc4cd0a5562ad3575709120a37ecd167e71873e5b1d3c520f6e4ec30`.

**KReach benchmark verdicts should be described as external, unverified results.** The upstream correctness counterexamples above preclude treating agreement on the benchmark collection as a general correctness validation. The Rust solver does not inherit these upstream changes or defects.

The resolved Haskell dependency plan is preserved in `scripts/kreach.cabal.project.freeze` and copied by the setup script before building.
