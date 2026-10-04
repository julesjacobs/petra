import json, subprocess, shlex, hashlib
from pathlib import Path
root=Path.cwd(); folder=root/'research/general-development-v3-linux-v1'
plan=json.loads((folder/'plan.json').read_text())
pins={**plan['required_file_sha256'],**plan['preflight_file_sha256']}
for name in ['research/general-development-v3-linux-v1/plan.json']:
 pins[name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
code='''import json,hashlib,sys
from pathlib import Path
pins=json.load(sys.stdin); out={}
for name,digest in pins.items():
 p=Path(name)
 if not p.exists():out[name]={'status':'missing'};continue
 with p.open('rb') as f: actual=hashlib.file_digest(f,'sha256').hexdigest()
 out[name]={'status':'matched' if digest==actual else 'mismatch','sha256':actual}
print(json.dumps(out))
'''
cmd=['tailscale','ssh','jules@jules-b650-aorus-elite-ax-v2','cd /home/jules/experiments/pvass-publication && vendor/venv/bin/python -c '+shlex.quote(code)]
r=subprocess.run(cmd,input=json.dumps(pins),text=True,capture_output=True,check=True)
observed=json.loads(r.stdout)
(folder/'deployment-inventory.json').write_text(json.dumps(observed,indent=2)+'\n')
from collections import Counter
print(Counter(v['status'] for v in observed.values()))
missing=[k for k,v in observed.items() if v['status']=='missing']; mismatch=[k for k,v in observed.items() if v['status']=='mismatch']
print('mismatches',mismatch)
print('missing local/unmatched', [k for k in missing if not (root/k).is_file() or hashlib.sha256((root/k).read_bytes()).hexdigest()!=pins[k]])
print('missing bytes',sum((root/k).stat().st_size for k in missing if (root/k).is_file()))
