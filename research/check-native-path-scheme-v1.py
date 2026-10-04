"""Compare native fixed schemes to real Z3 and independently check all witnesses."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('checker', ROOT/'scripts/check_accelerated_witness.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
cases = []
for initial in [1, 2]:
    for target in [0, 2, 4, 10**12]:
        cases.append((dict(places=['p'], initial=[initial],
                           transitions=[dict(name='grow', pre=[[0,2]], post=[[0,3]])],
                           target=[dict(coefficients=[1], bound=target, equality=True)]), [[0]]))
for target in [0, 1, 2, 5]:
    cases.append((dict(places=['p'], initial=[0],
                       transitions=[dict(name='produce', pre=[], post=[[0,2]]),
                                    dict(name='consume', pre=[[0,2]], post=[])],
                       target=[dict(coefficients=[1], bound=target, equality=True)]), [[0], [1]]))
for target in [0, 1]:
    cases.append((dict(places=['p'], initial=[0], transitions=[],
                       target=[dict(coefficients=[1], bound=target, equality=True)]), []))
rows = []
with tempfile.TemporaryDirectory(prefix='pvass-native-scheme-') as temporary:
    folder = Path(temporary)
    for i, (problem, words) in enumerate(cases):
        p, w = folder/'problem.json', folder/'words.json'
        p.write_text(json.dumps(problem)); w.write_text(json.dumps(words))
        native = subprocess.run([str(ROOT/'target/debug/examples/native_path_scheme'), str(p), str(w), '5'],
                                text=True, capture_output=True, check=True, timeout=7)
        answer = json.loads(native.stdout)
        formula = subprocess.check_output([str(ROOT/'target/debug/examples/accelerated_bmc'), 'emit', str(p), str(w), str(len(words))], text=True, timeout=7)
        fixed = ''.join(f'(assert (= w{i} {i}))\n(assert (> n{i} 0))\n' for i in range(len(words)))
        formula = formula.split('(check-sat)')[0] + fixed + '(check-sat)\n'
        result = subprocess.run([str(ROOT/'vendor/venv/bin/z3'), '-in', '-T:5'], input=formula,
                                text=True, capture_output=True, check=True, timeout=7)
        status = result.stdout.strip()
        assert status in ['sat', 'unsat'], result.stdout
        assert (answer['verdict'] == 'reachable') == (status == 'sat'), (i, answer, status)
        if status == 'sat': checker.check(problem, answer['segments'])
        else: assert answer['reason'] == 'fixed positive-repetition scheme infeasible', answer
        rows.append(dict(case=i, problem=problem, words=words, native=answer, z3=status,
                         formula_sha256=hashlib.sha256(formula.encode()).hexdigest()))
record = dict(status='passed', cases=len(rows), rows=rows,
              scope='Fixed-scheme semantics only; no discovery or performance evidence.',
              sources={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in [ROOT/'src/path_scheme.rs', ROOT/'src/summary.rs',
                                 ROOT/'src/accelerated_bmc.rs', ROOT/'examples/native_path_scheme.rs', Path(__file__)]})
folder = ROOT/'research/native-path-scheme-v1'
folder.mkdir(exist_ok=True)
(folder/'semantic.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps(dict(status='passed', cases=len(rows), reachable=sum(r['z3']=='sat' for r in rows))))
