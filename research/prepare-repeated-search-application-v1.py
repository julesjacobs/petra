import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
corpus=ROOT/'benchmarks/application-expansion-v1'
manifest=json.loads((corpus/'manifest.json').read_text());assert len(manifest['queries'])==192
binary=ROOT/'results/solver-repeated-search-v1/vass-reach'
paths={str(binary.relative_to(ROOT)):sha(binary),str((corpus/'manifest.json').relative_to(ROOT)):sha(corpus/'manifest.json')}
for q in manifest['queries']:
    assert q['status']=='imported'
    for k,v in q.items():
        if k.endswith('_sha256') and k[:-7] in q:
            p=(corpus/q[k[:-7]]).resolve();assert sha(p)==v;paths[str(p.relative_to(ROOT))]=v
    for b in q['branches']:
        p=(corpus/b['path']).resolve();assert sha(p)==b['sha256'];paths[str(p.relative_to(ROOT))]=b['sha256']
for p in (ROOT/'scripts').glob('*.py'):paths[str(p.relative_to(ROOT))]=sha(p)
for name in ('source.tar.gz','source-files-sha256.json','provenance.json'):
    p=binary.parent/name;paths[str(p.relative_to(ROOT))]=sha(p)
plan=dict(status='registered-not-started',scope='Full192-query existing application cohort regression after the outcome-selected repeated-firing diagnostic. Same frozen binary and buffer flag for both; only engine changes from portfolio-focused to portfolio-batched. Local single-repeat coverage, not competitor timing.',
    corpus=str(corpus.relative_to(ROOT)),manifest_sha256=sha(corpus/'manifest.json'),properties=192,
    exact_ordered_branch_representatives=187,expected_rows=384,seconds=5,repeat=1,
    methods={'control':'portfolio-focused','batched':'portfolio-batched'},buffer_agglomeration_methods=['control','batched'],
    max_states=2_000_000,memory_mib=2048,memory_enforcement='sampled macOS process-tree RSS',outer_grace=0,
    order_seed=20261107,profiling=False,output='results/repeated-search-application-v1',
    validation=dict(seconds=60,memory_mib=2048,response_mib=64,dag_check_max_work=200_000_000,included_in_solver_timing=False),
    binary_sha256=sha(binary),source_sha256=sha(binary.parent/'source.tar.gz'),required_file_sha256=paths,
    reporting='Retain192queries/187representatives and384rows, all failures, gains and losses. Compare per-family. No default promotion or stable speed claim from one repeat.')
with (ROOT/'research/repeated-search-application-v1-plan.json').open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
print(json.dumps(dict(required_files=len(paths),plan_sha256=sha(ROOT/'research/repeated-search-application-v1-plan.json'))))
