"""Exercise the frozen nine-configuration harness on synthetic EF/AG properties."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'research/general-development-v3-linux-v1'
CORPUS=ROOT/'benchmarks/general-development-v3-capability-v1'
OUTPUT=ROOT/'results/linux-general-development-v3-capability-v1'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert sys.platform=='linux' and str(ROOT)=='/home/jules/experiments/pvass-publication'
    plan=json.loads((FOLDER/'plan.json').read_text())
    sys.path.insert(0,str(ROOT/plan['runner_source']/'scripts'))
    import smpt_import as imp
    from process_runner import workspace_workloads
    assert not workspace_workloads(ROOT)
    assert not CORPUS.exists() and not OUTPUT.exists(), 'Fresh evidence required'
    subprocess.run([sys.executable,str(ROOT/plan['minizinc_preflight'])],check=True)
    CORPUS.mkdir()
    model=CORPUS/'model.pnml'
    model.write_text('''<pnml><net id="smoke" type="http://www.pnml.org/version-2009/grammar/ptnet"><page id="page"><place id="p"><initialMarking><text>1</text></initialMarking></place><place id="q"><initialMarking><text>0</text></initialMarking></place><transition id="move"/><arc id="a" source="p" target="move"/><arc id="b" source="move" target="q"/></page></net></pnml>''')
    problem=imp.pnml(model)
    records=[]; expected={}
    for slot,(kind,bound,truth) in enumerate([('EF',1,True),('EF',2,False),('AG',0,True),('AG',1,False)]):
        name=f'{kind}-{bound}'
        d=CORPUS/name; d.mkdir()
        outer,inner=('exists-path','finally') if kind=='EF' else ('all-paths','globally')
        xml=d/'original.xml'
        xml.write_text(f'<property-set><property><id>{name}</id><description>synthetic capability check</description><formula><{outer}><{inner}><integer-le><integer-constant>{bound}</integer-constant><tokens-count><place>q</place></tokens-count></integer-le></{inner}></{outer}></formula></property></property-set>')
        prop=imp.properties(xml,problem)[0]; branches=[]
        for i,target in enumerate(prop.pop('targets')):
            path=d/f'branch-{i}.json'; path.write_text(json.dumps(dict(problem,target=target)))
            branches.append(dict(path=str(path.relative_to(CORPUS)),sha256=sha(path)))
        net=d/'model.net'; net.write_text(imp.tina(problem))
        translated=d/'property.xml'; translated.write_text(imp.translated_xml(xml,problem['places']))
        record=dict(name=name,suite='synthetic-capability',instance='one-token-move',status='imported',property_slot=slot,branches=branches,places=2,transitions=1,**prop)
        for field,path in [('pnml',model),('xml',xml),('net',net),('property',translated)]:
            record[field]=str(path.relative_to(CORPUS)); record[field+'_sha256']=sha(path)
        records.append(record); expected[name]=truth
    (CORPUS/'manifest.json').write_text(json.dumps(dict(format='synthetic-capability-v1',queries=records),indent=2))
    spec=importlib.util.spec_from_file_location('launch',ROOT/'research/run-general-development-v3-linux-v1.py')
    launch=importlib.util.module_from_spec(spec); spec.loader.exec_module(launch)
    cmd=launch.command(plan)
    for flag,value in [('--corpus',str(CORPUS)),('--output',str(OUTPUT))]:cmd[cmd.index(flag)+1]=value
    (FOLDER/'capability-plan.json').write_text(json.dumps(dict(command=cmd,expected=expected,methods=list(plan['methods']),script_sha256=sha(Path(__file__))),indent=2))
    result=subprocess.run(cmd,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    (FOLDER/'capability-terminal.json').write_text(json.dumps(dict(exit_code=result.returncode)))
    result.check_returncode()
    rows=[json.loads(s) for s in (OUTPUT/'runs.jsonl').read_text().splitlines()]
    assert Counter((r['query'],r['method'],r['repeat']) for r in rows)==Counter((q,m,0) for q in expected for m in plan['methods'])
    for r in rows:
        label=(r['query'],r['method'])
        assert r['property_truth'] is expected[r['query']], (label,r)
        assert r['exit_code']==0 and not r['outer_timeout'],label
        res=r['resources']
        assert res['runner']=='linux-systemd-user' and res['cpus']==[8] and res['memory_limit_bytes']==2**31,label
        assert res['perf_enabled'] and not res.get('memory_limit_exceeded'),label
        assert res['perf_counters']['instructions:u']['value']>0,label
        if r['method'].startswith('native-'):
            assert r['independent_checks'] and r['validation']['exit_code']==0,label
    receipt=dict(status='harness-passed-component-smokes-pending',plan_sha256=sha(FOLDER/'plan.json'),runner_archive_sha256=plan['runner_archive_sha256'],methods=list(plan['methods']),rows=len(rows),expected=expected,runs_sha256=sha(OUTPUT/'runs.jsonl'),environment_sha256=sha(OUTPUT/'environment.json'))
    (FOLDER/'capability-harness.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__=='__main__':main()
