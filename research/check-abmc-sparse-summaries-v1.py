"""Regression for sparse nets beyond the former dense-summary cap and retained budgets."""
from pathlib import Path
import hashlib, importlib.util, json, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('checker', ROOT/'scripts/check_accelerated_witness.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
p = dict(places=[f'p{i}' for i in range(500)], initial=[0]*500,
         transitions=[dict(name=f't{i}', pre=[], post=[[i, 1]]) for i in range(500)],
         target=[dict(coefficients=[1]+[0]*499, bound=1, equality=True)])
rows = []
with tempfile.TemporaryDirectory(prefix='pvass-sparse-regression-') as tmp:
    path = Path(tmp)/'problem.json'
    path.write_text(json.dumps(p))
    base = [sys.executable, str(ROOT/'scripts/accelerated_bmc.py'), '--problem', str(path),
            '--mode', 'singleton', '--depth-limit', '1', '--seconds', '10']
    for limit, expected in [(200000, 'reachable'), (1100, 'summary cell limit'), (2200, 'encoding cell limit')]:
        result = json.loads(subprocess.check_output(base+['--encoding-cells', str(limit)], text=True, timeout=15))
        if expected == 'reachable':
            assert result['verdict'] == expected, result
            checker.check(p, result['segments'])
        else:
            assert result['verdict'] == 'unknown' and result['reason'] == expected, result
        rows.append(dict(limit=limit, result=result))
record = dict(status='passed', dense_cells=250000, runs=rows,
              sources={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in [ROOT/'src/accelerated_bmc.rs', ROOT/'scripts/accelerated_bmc.py', Path(__file__)]})
(ROOT/'research/abmc-sparse-summaries-v1/regression.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps(dict(status='passed', cases=len(rows))))
