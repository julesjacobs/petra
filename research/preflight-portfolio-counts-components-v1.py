"""Check fully reduced SMT/CP and portable WALK with bounded real subprocesses."""
from pathlib import Path
import hashlib
import json
import os
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'research/portfolio-counts-linux-v1'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert sys.platform=='linux' and str(ROOT)=='/home/jules/experiments/pvass-publication'
    plan=json.loads((FOLDER/'plan.json').read_text())
    harness=json.loads((FOLDER/'capability-harness.json').read_text())
    assert harness['status']=='harness-passed-component-smokes-pending'
    assert harness['plan_sha256']==sha(FOLDER/'plan.json')
    sys.path.insert(0,str(ROOT/plan['runner_source']/'scripts'))
    from process_runner import workspace_workloads
    from linux_runner import run
    assert not workspace_workloads(ROOT)
    folder=FOLDER/'components'; folder.mkdir()
    os.environ['PATH']=':'.join(str(ROOT/p) for p in [plan['minizinc_tool_bin'],'vendor/venv/bin','vendor/tina-linux/tina-4.0.0/bin','vendor/4ti2-install/bin'])+':'+os.environ['PATH']
    os.environ['PYTHONPATH']=str(ROOT/'vendor/SMPT-portable')
    net=ROOT/'research/smpt-minizinc-repair-v1/model.net'
    rows=[]
    for method,labels in [('SMT',['sat','unsat']),('CP',['sat','unsat']),('WALK',['sat'])]:
        for label in labels:
            log=folder/f'{method}-{label}.log'
            xml=ROOT/f'research/smpt-minizinc-repair-v1/smpt-cp-{label}.xml'
            cmd=[str(ROOT/'vendor/venv/bin/python'),'-m','smpt','--net',str(net),'--xml',str(xml),'--methods',method,'--timeout','10','--show-techniques','--show-model','--debug']
            if method!='WALK':cmd.append('--auto-reduce')
            wall,code,expired,resources=run(cmd,ROOT/'vendor/SMPT-portable',10,log,2**31,cpus=[8],perf=True)
            text=log.read_text(); expected='TRUE' if label=='sat' else 'FALSE'
            passed=code==0 and not expired and f'FORMULA smpt-cp-{label} {expected}' in text and not re.search('Traceback|command not found|No such file or directory',text)
            if method=='CP':passed=passed and 'CONSTRAINT_PROGRAMMING' in text and 'solve satisfy;' in text
            if method=='WALK':passed=passed and 'WALK' in text
            row=dict(method=method,label=label,passed=bool(passed),command=cmd,wall_seconds=wall,exit_code=code,expired=expired,resources=resources,log_sha256=sha(log))
            rows.append(row)
            (folder/'rows.json').write_text(json.dumps(rows,indent=2))
            assert passed,(method,label,text[-2000:])
    receipt=dict(harness,status='passed',component_rows=rows,component_script_sha256=sha(Path(__file__)),harness_receipt_sha256=sha(FOLDER/'capability-harness.json'),scope='Synthetic configuration/capability checks only; no competitive result.')
    with (FOLDER/'capability.json').open('x') as stream:json.dump(receipt,stream,indent=2)
    print(json.dumps(dict(status='passed',harness_rows=harness['rows'],component_rows=len(rows))))

if __name__=='__main__':main()
