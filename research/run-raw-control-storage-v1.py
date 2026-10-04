"""Match dense and compressed game-control storage on the complete transfer cohort."""
import hashlib
import importlib.util
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from process_runner import workspace_workloads

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def read(path):return json.loads(path.read_text())

def save(path,data):
    with path.open('x') as stream:json.dump(data,stream,indent=2);stream.write('\n')


def main():
    assert not workspace_workloads(ROOT)
    prior=read(ROOT/'research/transfer-raw-pilot-v1-plan.json')
    corpus=ROOT/'benchmarks/raw-transfer-automaton-v2'
    collection=read(corpus/'collection.json')
    assert 'finished_unix' in collection and len(collection['attempts'])==12
    sources=read(corpus/'source-manifest.json')['cases']
    attempts={a['name']:a for a in collection['attempts']}
    methods=['raw-portfolio-balanced']
    runs=[];pins=dict(prior['file_sha256'])
    for label,folder in [('dense','solver-raw-balanced-v1'),('compressed','solver-walk-sparse-v1')]:
        directory=ROOT/'results'/folder
        provenance=read(directory/'provenance.json')
        assert sha(directory/'vass-reach')==provenance['binary_sha256']
        assert sha(directory/'source.tar.gz')==provenance['source_sha256']
        for name in ['vass-reach','source.tar.gz','provenance.json']:
            path=directory/name;pins[str(path.relative_to(ROOT))]=sha(path)
        output=ROOT/f'results/raw-control-storage-v1-{label}'
        assert not output.exists()
        command=[sys.executable,'scripts/benchmark_stress_raw.py','--corpus',str(corpus),'--output',str(output),
                 '--binary',str(directory/'vass-reach'),'--methods',*methods,'--all-sources','--seconds','60',
                 '--memory-mib','2048','--repeat','1','--solver-fraction','0.8','--max-states','100000000']
        runs.append(dict(configuration=label,output=str(output.relative_to(ROOT)),command=command,binary_sha256=provenance['binary_sha256']))
    pins[str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__))
    plan=dict(format='raw-control-storage-v1',runs=runs,methods=methods,rows=24,source_slots=12,exported_queries=9,export_failures=3,
              file_sha256=pins,limits=dict(seconds=60,memory_mib=2048,max_states=100000000,repeat=1),
              scope='Complete unchanged transfer cohort, same balanced schedule/checker, older dense controls versus exact sparse/dense controls.60s input/check-inclusive,2GiB,one repeat. New intern work charge8*dimension versus2*before, so work-capped rows are not a pure storage ablation. No concurrent local solver/build/export. Both architectures remain current native development engines, not external competitors.')
    save(ROOT/'research/raw-control-storage-v1-plan.json',plan)
    environment=dict(os.environ)
    for name in ['VASS_RAW_PHASE_DIAGNOSTICS','VASS_RAW_NEGATIVE_DIAGNOSTICS']:environment.pop(name,None)
    summaries=[];verdicts=defaultdict(set);artifacts={}
    for run in runs:
        assert not workspace_workloads(ROOT)
        assert all(sha(ROOT/name)==digest for name,digest in pins.items())
        print('Starting '+run['output'],flush=True)
        result=subprocess.run(run['command'],cwd=ROOT,env=environment)
        assert result.returncode==0,'Retain harness failure; do not accept partial matrix'
        output=ROOT/run['output'];recorded=read(output/'environment.json')
        assert recorded['binary_sha256']==sha(output/'vass-reach')==run['binary_sha256']
        assert recorded['selected_sources']==[s['name'] for s in sources]
        for name,digest in recorded['runner_sha256'].items():assert sha(output/'runner-source'/name)==digest==pins['scripts/'+name]
        spec=importlib.util.spec_from_file_location('storage_classifier',output/'runner-source/benchmark_stress_raw.py')
        classifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(classifier)
        rows=[json.loads(line) for line in (output/'runs.jsonl').read_text().splitlines()]
        assert len(rows)==12 and {(r['query'],r['method'],r['repeat']) for r in rows}=={(s['name'],'raw-portfolio-balanced',0) for s in sources}
        for row in rows:
            verdicts[row['query']].add(row['verdict'])
            attempt=attempts[row['query']]
            if attempt['status']!='exported-unvalidated':
                assert row['status']=='export-unavailable' and row['verdict']=='not-run';continue
            assert row['query_sha256']==sha(corpus/attempt['query'])==sha(output/'inputs'/(row['query']+'.json'))
            directory=output/f"{row['query']}.{row['method']}.0"
            classified,expired,usage=classifier.classify_bounded_worker(directory,row['worker_exit_code'],row['outer_timeout'],row['usage'],row['wall_seconds'],60,2048*1024**2)
            assert all(row.get(k)==v for k,v in classified.items()) and row['outer_timeout']==expired and row['usage']==usage
            if row['verdict'] in ['reachable','unreachable']:
                assert not expired and not usage['memory_limit_exceeded'] and row['independent_check']
                assert row['worker_exit_code']==row['solver_exit_code']==0
                assert read(directory/'solver.stdout')['verdict']==row['verdict']
        summaries.append(dict(configuration=run['configuration'],rows=12,statuses=dict(Counter(r['status'] for r in rows))))
        paths=[output/name for name in ['runs.jsonl','environment.json','sources.json']]+list(output.glob('*/result.json'))+list(output.glob('*/solver.stdout'))
        artifacts.update({str(path.relative_to(ROOT)):sha(path) for path in paths})
    assert all(len(v & {'reachable','unreachable'})<=1 for v in verdicts.values())
    report=dict(status='passed',rows=24,source_slots=12,summaries=summaries,artifact_sha256=artifacts,
                scope='Saved independent-check/result reconciliation with frozen outer-limit classification. Full source denominator retained. One local repeat; no competitive timing claim.')
    save(ROOT/'research/raw-control-storage-v1-verification.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='artifact_sha256'},indent=2))

if __name__=='__main__':main()
