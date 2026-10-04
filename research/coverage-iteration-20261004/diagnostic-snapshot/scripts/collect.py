#!/usr/bin/env python3
"""Run the unmodified artifact sequentially and preserve every emitted query."""
import argparse, json, os, pathlib, shutil, signal, subprocess, time
ROOT = pathlib.Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--seconds', type=int, default=20)
p.add_argument('--outer-seconds', type=int, default=40)
a = p.parse_args()
front = ROOT / 'vendor/SerializabilityChecker'
out = ROOT / 'benchmarks/serializability'
out.mkdir(parents=True, exist_ok=True)
for source in sorted((front / 'examples').glob('*/*')):
    if source.suffix not in ('.ser', '.json'): continue
    start = time.monotonic()
    with (out / (source.stem + '.frontend.log')).open('w') as log:
        proc = subprocess.Popen([str(front / 'target/release/ser'), '--no-viz', '--timeout', str(a.seconds), str(source)], cwd=front, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        status = 'completed'
        try: proc.wait(timeout=a.outer_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL); proc.wait(); status = 'outer_timeout'
    dest = out / source.stem
    dest.mkdir(exist_ok=True)
    generated = front / 'out' / source.stem
    for path in generated.glob('*'):
        if path.suffix in ('.net','.xml','.scn','.stdout','.stderr') or path.name == 'certificate.json': shutil.copy2(path, dest / path.name)
    record = dict(benchmark=source.stem, status=status, exit_code=proc.returncode, seconds=time.monotonic()-start, queries=len(list(dest.glob('smpt_petri_disjunct_*.net'))))
    with (out/'collection.jsonl').open('a') as f: f.write(json.dumps(record)+'\n')
    print(json.dumps(record), flush=True)
