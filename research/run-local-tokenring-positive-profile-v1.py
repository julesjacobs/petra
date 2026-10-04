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
