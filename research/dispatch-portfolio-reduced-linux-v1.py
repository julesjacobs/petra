"""Start one detached frozen run and preserve its exact process identity."""
import hashlib,json,shlex,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'research/portfolio-reduced-linux-v1'
a=json.loads((F/'capability-audit.json').read_text());assert a['status']=='passed'
assert a['plan_sha256']==hashlib.sha256((F/'plan.json').read_bytes()).hexdigest()
assert not (F/'dispatch.json').exists()
assert a['closure_receipt_sha256']==hashlib.sha256((F/'closure/receipt.json').read_bytes()).hexdigest()
code='''import hashlib,json,subprocess,psutil,time
from pathlib import Path
from scripts.process_runner import workspace_workloads
root=Path.cwd();f=root/'research/portfolio-reduced-linux-v1'
assert not workspace_workloads(root)
assert not (f/'dispatch.json').exists() and not (f/'execution.json').exists() and not (f/'terminal.json').exists()
assert not (root/'results/linux-portfolio-reduced-v1').exists()
receipt=json.loads((f/'capability.json').read_text())
assert receipt['status']=='passed' and receipt['plan_sha256']==hashlib.sha256((f/'plan.json').read_bytes()).hexdigest()
with (f/'run.log').open('xb') as log:
 p=subprocess.Popen([str(root/'vendor/venv/bin/python'),str(root/'research/run-portfolio-reduced-linux-v1.py'),'--launch','--capability-receipt',str(f/'capability.json')],cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 d=dict(pid=p.pid,created=psutil.Process(p.pid).create_time(),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),plan_sha256=receipt['plan_sha256'])
 with (f/'dispatch.json').open('x') as out:json.dump(d,out,indent=2);out.write('\\n')
 print(json.dumps(d))
'''
code=code.replace("receipt=json.loads((f/'capability.json').read_text())", "assert hashlib.sha256((f/'closure/receipt.json').read_bytes()).hexdigest()=="+repr(a['closure_receipt_sha256'])+"\nreceipt=json.loads((f/'capability.json').read_text())")
r=subprocess.run(['tailscale','ssh','jules@jules-b650-aorus-elite-ax-v2','cd /home/jules/experiments/pvass-publication && vendor/venv/bin/python -c '+shlex.quote(code)],capture_output=True,text=True,check=True)
d=json.loads(r.stdout)
with (F/'dispatch.json').open('x') as f:json.dump(d,f,indent=2);f.write('\n')
print(json.dumps(d))
