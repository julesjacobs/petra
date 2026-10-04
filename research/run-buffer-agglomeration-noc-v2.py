import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import workspace_workloads

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
corpus=ROOT/'benchmarks/application-gaps-v2'
binary=ROOT/'results/solver-buffer-agglomeration-v2/vass-reach'
output=ROOT/'results/buffer-agglomeration-noc-v2'
manifest=json.loads((corpus/'manifest.json').read_text())
query=next(q for q in manifest['queries'] if q['name']=='NoC3x3-PT-8B__RC12')
paths={str(binary):sha(binary),str(corpus/'manifest.json'):sha(corpus/'manifest.json')}
for k,v in query.items():
    if k.endswith('_sha256') and k[:-7] in query:
        p=(corpus/query[k[:-7]]).resolve();assert sha(p)==v;paths[str(p)]=v
for branch in query['branches']:
    p=(corpus/branch['path']).resolve();assert sha(p)==branch['sha256'];paths[str(p)]=branch['sha256']
for p in (ROOT/'scripts').glob('*.py'):paths[str(p)]=sha(p)
plan=dict(scope='One motivating development query, one local same-binary opt-in comparison; no competitor or stable timing claim.',
    query=query['name'],methods={'control':[],'buffer':['--buffer-agglomeration']},
    engine='portfolio-focused',seconds=10,repeat=1,outer_grace=0,memory_mib=2048,max_states=2_000_000,
    validation=dict(seconds=60,memory_mib=2048,response_mib=64,dag_work=200_000_000),
    expected_rows=2,profiling=True,required_files=paths)
with (ROOT/'research/buffer-agglomeration-noc-v2-plan.json').open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
assert not output.exists() and not workspace_workloads(ROOT)
command=[sys.executable,'scripts/benchmark_smpt_classic.py','--corpus',str(corpus),'--binary',str(binary),
    '--native-tool','control','portfolio-focused',str(binary),'--native-tool','buffer','portfolio-focused',str(binary),
    '--methods','control','buffer','--buffer-agglomeration-method','buffer','--rust-original','--bounded-validation',
    '--validation-seconds','60','--validation-memory-mib','2048','--validation-response-mib','64','--validation-dag-work','200000000',
    '--track-resources','--memory-mib','2048','--max-states','2000000','--outer-grace','0','--seconds','10','--repeat','1',
    '--filter','^NoC3x3-PT-8B__RC12$','--order-seed','20261012','--output',str(output)]
subprocess.run(command,cwd=ROOT,env=dict(os.environ,VASS_PORTFOLIO_PROFILE='1'),check=True)
assert all(sha(Path(p))==v for p,v in paths.items())
