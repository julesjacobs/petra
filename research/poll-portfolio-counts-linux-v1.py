"""Read authoritative process identity and terminal receipt without restarting jobs."""
import subprocess,shlex,json
from pathlib import Path
code='''import json,psutil
from pathlib import Path
f=Path('research/portfolio-counts-linux-v1'); d=json.loads((f/'dispatch.json').read_text())
terminal=json.loads((f/'terminal.json').read_text()) if (f/'terminal.json').exists() else None
try:
 p=psutil.Process(d['pid']); live=p.create_time()==d['created'] and p.status()!=psutil.STATUS_ZOMBIE and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==d['boot_id']
except psutil.NoSuchProcess:live=False
rows=Path('results/linux-portfolio-counts-v1/runs.jsonl')
print(json.dumps(dict(pid=d['pid'],live=live,terminal=terminal,execution_exists=(f/'execution.json').exists(),rows=sum(1 for _ in rows.open()) if rows.exists() else 0,tail=(f/'run.log').read_text()[-1800:])))
'''
r=subprocess.run(['tailscale','ssh','jules@jules-b650-aorus-elite-ax-v2','cd /home/jules/experiments/pvass-publication && vendor/venv/bin/python -c '+shlex.quote(code)],text=True,capture_output=True,check=True)
observation=json.loads(r.stdout)
Path(__file__).resolve().parent.joinpath('portfolio-counts-linux-v1/latest-observation.json').write_text(json.dumps(observation,indent=2)+'\n')
print(r.stdout)
