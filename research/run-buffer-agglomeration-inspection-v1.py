import hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import run,workspace_workloads
from buffer_agglomeration_checker import reconstruct

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
output=ROOT/'results/buffer-agglomeration-inspection-v1';output.mkdir()
query=ROOT/'benchmarks/application-expansion-v1/NoC3x3-PT-8B__RC12/branch-0.json'
binary=ROOT/'results/solver-buffer-agglomeration-v1/inspect_buffer_agglomeration'
plan=dict(scope='Local single-branch structural diagnostic only, not solver coverage or competitor timing.',
          query=str(query.relative_to(ROOT)),query_sha256=sha(query),binary_sha256=sha(binary),
          preparation_seconds=[.1,1.],outer_seconds=5,memory_mib=2048,work=20_000_000,
          independent_reconstruction_seconds=60)
(output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
assert not workspace_workloads(ROOT)
rows=[]
for index,budget in enumerate(plan['preparation_seconds']):
    path=output/f'inspection-{index}.json'
    wall,exit_code,expired,resources=run([str(binary),str(query),str(budget)],ROOT,5,path,2048*1024**2)
    row=dict(budget=budget,wall_seconds=wall,exit_code=exit_code,expired=expired,resources=resources)
    if exit_code==0 and not expired:
        answer=json.loads(path.read_text());detail=answer['detail'];row.update(status=detail['status'],preparation_seconds=answer['preparation_seconds'])
        if detail['status']=='reduced':
            checked=reconstruct(json.loads(query.read_text()),detail['steps'],deadline=time.monotonic()+60)
            assert checked==detail['reduced']
            row.update(steps=len(detail['steps']),places=len(checked['places']),transitions=len(checked['transitions']),independent_reconstruction=True)
        else:row['detail']=detail
    rows.append(row)
    print(json.dumps(row),flush=True)
assert sha(query)==plan['query_sha256'] and sha(binary)==plan['binary_sha256']
(output/'report.json').write_text(json.dumps(dict(plan=plan,rows=rows),indent=2)+'\n')
