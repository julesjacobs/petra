
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
