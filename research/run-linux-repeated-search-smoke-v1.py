"""Remote capability preflight; preserved separately from comparative timings."""
import json
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REMOTE = '/home/jules/experiments/pvass-publication'
HOST = 'jules@jules-b650-aorus-elite-ax-v2'
new = 'results/linux-solver-repeated-search-v1/vass-reach'
old = 'results/linux-solver-capacity-direct-v1/vass-reach'
hashes = json.loads((ROOT / 'results/runner-repeated-search-v2/files-sha256.json').read_text())
hashes[new] = json.loads((ROOT / 'results/linux-solver-repeated-search-v1/provenance.json').read_text())['binary_sha256']
hashes[old] = 'e3e7f057d8885b82238a0c86a50ef56fc5492946aa85abc805387b609dc37a'
# Pin the authoritative baseline hash rather than relying on a copied literal.
hashes[old] = json.loads((ROOT / 'research/application-parameter-ladders-v2-screen-plan.json').read_text())['native_binary_sha256']
code = f'''
import hashlib
from pathlib import Path
from scripts.process_runner import workspace_workloads
assert not workspace_workloads(Path.cwd())
for name,expected in {hashes!r}.items():
    with Path(name).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expected,name
print('Frozen runner and both native binaries verified.',flush=True)
'''
subprocess.run(['tailscale', 'ssh', HOST,
                f'cd {REMOTE} && vendor/venv/bin/python -c ' + shlex.quote(code)
                + ' && vendor/venv/bin/python research/check-smpt-minizinc-repair-v1.py'], check=True)
command = ['vendor/venv/bin/python', '-u', 'scripts/benchmark_smpt_classic.py',
           '--corpus', 'benchmarks/application-expansion-v1', '--binary', new,
           '--native-tool', 'native-frozen', 'portfolio-focused', old,
           '--native-tool', 'native-buffer', 'portfolio-focused', new,
           '--native-tool', 'native-batched', 'portfolio-batched', new,
           '--methods', 'native-frozen', 'native-buffer', 'native-batched', 'verifypn-default', 'smpt-full-portable',
           '--buffer-agglomeration-method', 'native-buffer', '--buffer-agglomeration-method', 'native-batched',
           '--rust-original', '--smpt-original', '--bounded-validation',
           '--validation-seconds', '60', '--validation-memory-mib', '2048',
           '--validation-response-mib', '64', '--validation-dag-work', '200000000',
           '--linux-cpus', '8', '--perf', '--memory-mib', '2048', '--max-states', '2000000', '--outer-grace', '0',
           '--smpt-root', 'vendor/SMPT-portable', '--smpt-python', 'vendor/venv/bin/python',
           '--tool-bin', 'vendor/tina-linux/tina-4.0.0/bin', '--tool-bin', 'vendor/4ti2-install/bin',
           '--tool-bin', 'vendor/minizinc-linux-v1/MiniZincIDE-2.10.1-x86_64-linux-gnu/bin',
           '--verifypn-binary', 'vendor/verifypn/build-release/verifypn/bin/verifypn-linux64',
           '--seconds', '5', '--repeat', '1', '--order-seed', '20261108',
           '--filter', '^(CircadianClock-PT-100000__RC12|NoC3x3-PT-8B__RC12|IOTPpurchase-PT-C05M04P03D02__RC13)$',
           '--output', 'results/linux-repeated-search-smoke-v1']
plan = dict(scope='Capability smoke, not competitive timing evidence.', command=command,
            expected_rows=15, required_file_sha256=hashes)
with (ROOT / 'research/linux-repeated-search-smoke-v1-plan.json').open('x') as stream:
    json.dump(plan, stream, indent=2)
    stream.write('\n')
subprocess.run(['tailscale', 'ssh', HOST,
                f'cd {REMOTE} && unset VASS_PORTFOLIO_PROFILE VASS_RELAXED_PROFILE && ' + shlex.join(command)], check=True)
