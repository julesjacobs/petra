# TokenRing positive gaps

Read-only investigation of the completed comparison; no solver/build or remote
operation was run. All nine gaps are competitor-reported reachable targets
(counterexamples for AG), not independently replayed competitor witnesses.

## Established by saved logs

SMPT names **WALK** on TokenRing-20 RC09/10/13/14/15. Its reported WALK times are
0.025–0.281s, full-reduction times0.282–0.289s, while complete invocations take
about2.0–2.4s. These internal times are not end-to-end timing. The local SMPT
interface implements a random walk using `walk -R ... -loop -seed`; the winning
logs do not retain the particular walk or seed. Their success is evidence for
a generic positive-search mechanism worth testing, not a reproducible witness.

VerifyPN's six successes have the following saved explicit-search statistics:

| Query | Native canonical branches | Discovered / expanded | Wall seconds |
|---|---:|---:|---:|
| TokenRing-20 RC13 | 2 | 253 / 94 | 0.146 |
| TokenRing-20 RC15 | 2 | 484 / 327 | 0.150 |
| TokenRing-30 RC12 | 1 | 966 / 635 | 0.491 |
| TokenRing-30 RC14 | 1 | 904 / 573 | 0.499 |
| TokenRing-40 RC12 | 3 | 1971 / 833 | 1.576 |
| TokenRing-40 RC14 | 3 | 3900 / 249 | 1.684 |

**Every one of these six logs reports zero removed places/transitions.** The
technique banner includes structural reduction, query reduction, SAT/SMT,
explicit search, state compression and stubborn sets; it does not establish
which search heuristic was decisive. Trace generation was disabled.

Formula simplification is concrete:20/RC13 becomes `EF State_3_4>=1`, and20/RC15
becomes `not EF State_6_15>=1`; threshold atoms requiring2or3tokens disappear
from the40-node queries. The two30-node queries retain their essential comparison
between two places. Therefore query simplification is useful evidence, but
cannot alone explain all six wins. Branch scheduling cannot explain the five
single-branch gaps either.

Models have441/961/1681places and8421/27931/65641transitions for20/30/40nodes.
The nine saved native-batched JSON outputs are incomplete/empty; there is no
native phase evidence identifying parsing, preparation, search or replay cost.
Source: `results/linux-application-portfolio-comparison-v1/TokenRing-*.log` and
the selected rows in `research/application-positive-gaps-v1.json`.

## Mechanisms to distinguish

1. **Positive search arrives too late.** The current focused/batched portfolio
   first performs capacity discovery/refutation, optional buffer preparation,
   relevance preparation, causal solving and local closure. Capacity discovery
   is capped at500ms; buffer preparation at100ms; causal solving at500ms;
   local closure at100ms. Fractions and branch budgets can lower these caps.
   Focused search then gets60%of the remaining portfolio time and internally
   tries helpful actions for one third before restarting unrestricted search.
   These are source-derived allocations, not measured TokenRing costs.
2. **Expensive guidance per explored state.** `relaxed::Graph::plan` allocates
   fact/action arrays and propagates relaxed costs anew per evaluated state.
   With tens of thousands of transitions, a few hundred useful states can still
   cost too much. A lightweight walk with incremental enabled-transition
   maintenance, or cheaper/incremental goal guidance, could complement this
   search. No current result establishes that this is the bottleneck.
3. **Formula-level simplification before branch search.** Native capacity
   preprocessing currently refutes whole conjunctions; it does not generally
   remove tautological atoms and simplify the original Boolean formula. Exact
   capacity-based atom simplification could reduce branches/constraints, provided
   equivalence is checked. VerifyPN's changes support investigating this, not
   blindly copying its simplified targets.
4. **Search ordering/reduction.** The existing direct target-stubborn search is
   a cheap first comparison before implementing another reduction. A random-walk
   phase would need fixed recorded seeds, bounded restarts and original-net
   replay; failure must remain Unknown. Repeated firing is unlikely to be the
   principal missing ingredient merely because it helped CircadianClock: these
   logs establish no long repeated-transition witness.

## Next local diagnostics, not yet run

Wait until local session53215 is confirmed terminal. Do not access Linux while
session13213 is live. First compare the unchanged portfolio against direct
positive engines on three representative queries: a WALK-only single branch,
a VerifyPN single branch, and a strongly simplified two-branch formula. This
is a12-row diagnostic, not a replacement for the full nine-gap denominator.
The frozen local binary is the macOS counterpart of the tested implementation;
do not compare these local wall times numerically with Linux timings.

```sh
env -u VASS_PORTFOLIO_PROFILE -u VASS_RELAXED_PROFILE \
  vendor/venv/bin/python scripts/benchmark_smpt_classic.py \
  --corpus benchmarks/application-portfolio-comparison-v1 \
  --binary results/solver-repeated-search-v1/vass-reach \
  --native-tool native-portfolio portfolio-batched results/solver-repeated-search-v1/vass-reach \
  --native-tool native-focused relaxed-focused results/solver-repeated-search-v1/vass-reach \
  --native-tool native-batched relaxed-batched results/solver-repeated-search-v1/vass-reach \
  --native-tool native-target relaxed-target-stubborn results/solver-repeated-search-v1/vass-reach \
  --methods native-portfolio native-focused native-batched native-target \
  --buffer-agglomeration-method native-portfolio \
  --rust-original --bounded-validation --validation-seconds 60 \
  --validation-memory-mib 2048 --validation-response-mib 64 \
  --validation-dag-work 200000000 --track-resources --memory-mib 2048 \
  --max-states 2000000 --outer-grace 0 --seconds 5 --repeat 1 \
  --order-seed 20261113 \
  --filter '^(TokenRing-PT-020__RC09|TokenRing-PT-030__RC12|TokenRing-PT-020__RC13)$' \
  --output results/local-tokenring-positive-diagnostic-v1
```

Direct modes intentionally bypass several preparation stages, so any recovery
supports a preparation/allocation hypothesis but does not isolate a single
stage. All positives still require the runner's independent original-input
check; keep failures and the runner's source/binary/input snapshots.

Then obtain phase evidence for the same three portfolio calls, serially. This
separate profile includes a strict5s outer limit and sampled2GiB RSS; split
stderr from stdout because the ordinary JSON validator cannot consume combined
profiling records. This command only records diagnostic artifacts; it does not
classify/check a positive answer and its times must not replace the unprofiled
run. Missing phase ends remain censored; no first event is not proof of parsing
being the bottleneck because capacity/relevance preparation also lacks a complete
outer phase span.

```sh
vendor/venv/bin/python - <<'PY'
import hashlib, json, os, sys
from pathlib import Path
sys.path.insert(0, 'scripts')
from process_runner import run, workspace_workloads
root = Path.cwd()
assert not workspace_workloads(root)
binary = root/'results/solver-repeated-search-v1/vass-reach'
assert hashlib.sha256(binary.read_bytes()).hexdigest() == '1d7776ad8984faac623d994119678e1379457842e31eff5b53336964d0eb8c60'
corpus = root/'benchmarks/application-portfolio-comparison-v1'
queries = {q['name']:q for q in json.loads((corpus/'manifest.json').read_text())['queries']}
out = root/'results/local-tokenring-positive-profile-v1'
out.mkdir()
for name in ['TokenRing-PT-020__RC09','TokenRing-PT-030__RC12','TokenRing-PT-020__RC13']:
    assert not workspace_workloads(root)
    q = queries[name]
    cmd = [str(binary),'--pnml',str(corpus/q['pnml']),'--xml',str(corpus/q['xml']),
           '--property-id',q['property_id'],'--method','portfolio-batched',
           '--buffer-agglomeration','--seconds','5','--max-states','2000000']
    for key in ['pnml','xml']:
        with (corpus/q[key]).open('rb') as f:
            assert hashlib.file_digest(f,'sha256').hexdigest() == q[key+'_sha256']
    code = ('import os,subprocess,sys; '
            'o=open(sys.argv[1],"w"); e=open(sys.argv[2],"w"); '
            'sys.exit(subprocess.call(sys.argv[3:],stdout=o,stderr=e,'
            'env=dict(os.environ,VASS_PORTFOLIO_PROFILE="1",VASS_RELAXED_PROFILE="1")))')
    wrapper = [sys.executable,'-c',code,str(out/(name+'.json')),str(out/(name+'.profile.jsonl')),*cmd]
    wall, status, expired, usage = run(wrapper,root,5,out/(name+'.wrapper.log'),memory_bytes=2048*1024**2)
    (out/(name+'.metadata.json')).write_text(json.dumps(dict(command=cmd,wall_seconds=wall,
        exit_code=status,outer_timeout=expired,resources=usage),indent=2)+'\n')
PY
```

If direct search recovers the cases, isolate capacity/buffer/relevance costs
next using the recorded phases and explicit flags. If all direct engines still
struggle while reaching only small state counts, instrument heuristic evaluation
cost before implementing a walk. If they explore many states cheaply, investigate
guidance/restarts and query simplification. These are conditional next steps,
not diagnoses established by the saved timeout rows.
