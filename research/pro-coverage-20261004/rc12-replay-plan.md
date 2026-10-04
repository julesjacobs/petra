# RC12 replay gate and copy-mixture assessment

Static inspection only, 2026-10-04. No reviewer program, replay, build, test or solver was executed. Run the command below only after **all** active measurements finish and root opens the checking window.

The reviewer archive is `copy-mixture-consultation.zip`, SHA-256 `772feaeb1d2bc18b3eab0f6a6e50ef5f3527450c71592b2e8e9d9c1e53a217a1`. The exact JSON member is `copy-mixture-consultation/fixed_prefix/RERS17pb114-PT-5__RC12__mix.json`, SHA-256 `e545c6ca3bcdc1ba6d1c725d678538b7690484f658a1faf940c88de4291102f5`.

It proposes branch 0, factor 5, and an expanded trace of 5,192 transition indices. Segment A has length 181 and multiplicity 2; B has length 1,610 and multiplicity 3. Claimed component row values are `(1,0,0,0,1)` and `(0,0,1,0,0)`, yielding `(2,0,3,0,2)`. These are inspected artifact contents, not yet locally replayed results.

Original inputs are under `benchmarks/general-development-v3`:

- `inputs/RERS17pb114-PT-5/model.pnml`: SHA-256 `782a9a55d957bebc6f6634834a425b9d6d1edb24bbc51373125ba0bf1954bbba`.
- `RERS17pb114-PT-5__RC12/original-property.xml`: SHA-256 `b0c9754017c84dee0fc100ae0813b85b58d1a87494efda457d04241dbaaa6147`.
- `RERS17pb114-PT-5__RC12/branch-0.json`: SHA-256 `352f7731820ce85deb4e587c377d1a19e38d8859800d7140800055463279a489`.

The exact ID is `RERS17pb114-PT-5-ReachabilityCardinality-12`, an EF property with one branch. Its complete target is `p16-p700 >= 0`, `-p1355 >= -1`, `p1211 >= 3`, `p1017-p921 >= 0`, and `p1166-p405 >= 1`.

## Deferred command

Run from `/Users/julesjacobs/git/git/pvass`, with assertions enabled. This reads reviewer JSON as data, executes only project checker/importer code plus the inline independent replay below, and applies the existing 60-second/2-GiB sampled process-tree limit. It creates a fresh output directory and does not rerun discovery. Recorded checking time is not a solver measurement.

```sh
PYTHONPATH=scripts vendor/venv/bin/python - <<'PY'
import json
import pathlib
import sys
from process_runner import run
root = pathlib.Path.cwd()
out = root / 'research/pro-coverage-20261004/rc12-independent-replay-v1'
out.mkdir(exist_ok=False)
worker = r'''
import hashlib, json, pathlib, zipfile
from bounded_validation import InputChecks
from native_original import translate
from benchmark import verify
assert __debug__
root = pathlib.Path.cwd()
base = root / 'benchmarks/general-development-v3'
folder = root / 'research/pro-coverage-20261004'
checks = InputChecks()
archive = folder / 'copy-mixture-consultation.zip'
checks.check(archive, '772feaeb1d2bc18b3eab0f6a6e50ef5f3527450c71592b2e8e9d9c1e53a217a1')
member = 'copy-mixture-consultation/fixed_prefix/RERS17pb114-PT-5__RC12__mix.json'
with zipfile.ZipFile(archive) as z:
    data = z.read(member)
assert hashlib.sha256(data).hexdigest() == 'e545c6ca3bcdc1ba6d1c725d678538b7690484f658a1faf940c88de4291102f5'
proposal = json.loads(data)
pnml = base / 'inputs/RERS17pb114-PT-5/model.pnml'
xml = base / 'RERS17pb114-PT-5__RC12/original-property.xml'
canonical_path = base / 'RERS17pb114-PT-5__RC12/branch-0.json'
checks.check(pnml, '782a9a55d957bebc6f6634834a425b9d6d1edb24bbc51373125ba0bf1954bbba')
checks.check(xml, 'b0c9754017c84dee0fc100ae0813b85b58d1a87494efda457d04241dbaaa6147')
checks.check(canonical_path, '352f7731820ce85deb4e587c377d1a19e38d8859800d7140800055463279a489')
net, prop = translate(pnml, xml, 'RERS17pb114-PT-5-ReachabilityCardinality-12')
assert prop['kind'] == 'EF' and len(prop['targets']) == 1
assert proposal['verdict'] == 'reachable' and proposal['branch'] == 0
canonical = json.loads(canonical_path.read_text())
assert canonical['places'] == net['places'] and canonical['initial'] == net['initial']
assert canonical['target'] == prop['targets'][0]
assert len(canonical['transitions']) == len(net['transitions'])
for a, b in zip(canonical['transitions'], net['transitions']):
    assert a['name'] == b['name']
    for side in ('pre', 'post'):
        assert [tuple(x) for x in a[side]] == b[side]
del canonical

def replay(initial, trace):
    marking = initial.copy()
    for i in trace:
        assert type(i) is int and 0 <= i < len(net['transitions'])
        tr = net['transitions'][i]
        assert all(marking[p] >= w for p, w in tr['pre'])
        for p, w in tr['pre']:
            marking[p] -= w
        for p, w in tr['post']:
            marking[p] += w
            assert marking[p] < 2**64
    return marking

def values(marking):
    return [sum(a*m for a, m in zip(row['coefficients'], marking))
            for row in prop['targets'][0]]

trace = proposal['trace']
assert type(trace) is list and len(trace) == proposal['trace_length'] == 5192
marking = replay(net['initial'], trace)
assert values(marking) == proposal['values'] == [2, 0, 3, 0, 2]
checked = verify(dict(net, target=prop['targets'][0]),
                 dict(verdict='reachable', trace=trace, marking=marking))
assert checked == 'python-witness'
assert proposal['factor'] == 5 and all(m % 5 == 0 for m in net['initial'])
assert proposal['multiplicities'] == [2, 3]
assert proposal['segment_lengths'] == [181, 1610]
assert len(proposal['segment_values']) == 2
unit = [m // 5 for m in net['initial']]
endpoint_sum = [0] * len(unit)
offset = 0
for count, length, signature in zip(proposal['multiplicities'], proposal['segment_lengths'], proposal['segment_values']):
    word = trace[offset:offset+length]
    assert trace[offset:offset+count*length] == word*count
    endpoint = replay(unit, word)
    assert values(endpoint) == signature
    for i, value in enumerate(endpoint):
        endpoint_sum[i] += count*value
    offset += count*length
assert offset == len(trace) and endpoint_sum == marking
checks.unchanged()
report = dict(status='passed', scope='one reviewer witness replay; no solver measurement',
              query='RERS17pb114-PT-5__RC12', property_kind='EF', property_truth=True,
              original_weighted_replay=True, original_complete_target=True,
              canonical_transition_identity=True, component_replay=True,
              additive_endpoint=True, independent_checker=checked,
              trace_length=len(trace), final_values=values(marking),
              checker_sha256=hashlib.sha256((root/'scripts/benchmark.py').read_bytes()).hexdigest(),
              importer_sha256=hashlib.sha256((root/'scripts/smpt_import.py').read_bytes()).hexdigest())
(folder/'rc12-independent-replay-v1/result.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
'''
(out / 'worker.py').write_text(worker)
wall, code, expired, resources = run(
    [sys.executable, str(out / 'worker.py')], root, 60,
    out / 'checker.log', 2 * 1024**3)
receipt = dict(wall_seconds=wall, exit_code=code, timeout=expired, resources=resources,
               included_in_solver_measurement=False)
(out / 'execution.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps(receipt, indent=2))
assert code == 0 and not expired
assert json.loads((out / 'result.json').read_text())['status'] == 'passed'
PY
```

The separate universal claim that uniform lifting cannot solve RC12 additionally needs checking conservation of the block `p1119..p1247` on every original transition. The command above establishes the witness and its composition without depending on that claim. Its successful output must not be folded into native five-second coverage: the current solver did not discover this supplied trace.

## Integration decision

Finish and audit the frozen repeated whole-cohort comparison first. On the evidence currently reported by root, original-net scaled walking already captures 25/26 RERS and the integrated survivor screen captures 26/31. Copy mixtures have a plausible **one-property** gain over that much stronger control, RC12; their larger reviewer gain predominantly overlaps the independently developed scaled-walk change.

A small positive-only composition follow-up is worthwhile research because RC12 exhibits a real expressiveness limitation of uniform lifting. It is not needed to establish the current iteration's substantial gain, and it should not delay or contaminate its frozen measurement. If pursued next, retain the current candidate as the control, replay RC12 first, then add bounded endpoint retention and exact composition as a separate arm. Use one complete target branch, preserve signed row values/equalities, retain short witnesses, and replay the concatenated trace on the original net. Do not introduce a general integer-solver redesign for one property. Native runtime, new held-out coverage and novelty remain unknown.
