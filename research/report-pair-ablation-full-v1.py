"""Summarize the completed and audited full ordinary pair ablation."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/local-pair-ablation-full-v1'
audit_path = ROOT / 'research/pair-ablation-full-v1-audit.json'
audit = json.loads(audit_path.read_text())
assert audit['status'] == 'passed' and audit['rows'] == 1312
rows = [json.loads(line) for line in (OUT / 'runs.jsonl').read_text().splitlines()]
assert hashlib.sha256((OUT / 'runs.jsonl').read_bytes()).hexdigest() == audit['artifact_sha256'][str((OUT / 'runs.jsonl').relative_to(ROOT))]
manifest = json.loads((ROOT / 'benchmarks/application-portfolio-comparison-v1/manifest.json').read_text())
queries = {q['name']: q for q in manifest['queries']}
methods = ['native-pair', 'native-phase-pair']
solved = {m: {r['query'] for r in rows if r['method'] == m and r['verdict'] == 'unreachable'} for m in methods}
reasons = defaultdict(Counter)
for detail in audit['details']:
    for reason in set(detail.get('reasons', [])):
        reasons[detail['method']][reason] += 1
families = sorted({q['family'] for q in queries.values()})
coverage = {m: dict(Counter(r['verdict'] for r in rows if r['method'] == m)) for m in methods}
comparison = dict(status='audited', source_slots=656, imported_slots=640, unavailable_slots=16, rows=1312, coverage=coverage,
                  phase_only=sorted(solved['native-phase-pair'] - solved['native-pair']), uniform_only=sorted(solved['native-pair'] - solved['native-phase-pair']),
                  family_coverage={f: {m: sum(queries[q]['family'] == f for q in solved[m]) for m in methods} for f in families},
                  reason_property_counts={m: dict(c) for m, c in reasons.items()},
                  audit_sha256=hashlib.sha256(audit_path.read_bytes()).hexdigest(),
                  scope='Full development-cohort local mechanism comparison,5s solver, separate60s checking. Both engines only prove unreachability; no integrated-portfolio or competitive Linux timing result.')
(ROOT / 'research/pair-ablation-full-v1-analysis.json').write_text(json.dumps(comparison, indent=2) + '\n')
lines = ['# Full ordinary uniform/phase pair ablation', '',
         'All1,312rows pass the saved-artifact audit:656source slots,640imports and16unavailable inputs per method. One local repeat,5s per original property, sampled2GiB, separate60s/2GiB/64MiB independent original-input checking. Both methods are negative-only; Unknown is expected on reachable properties.', '',
         '| Method | Independently checked negative properties | Remaining imported properties | Unavailable |', '|---|---:|---:|---:|']
for m in methods:
    lines.append(f'| {m} | {len(solved[m])} | {640-len(solved[m])} | 16 |')
lines += ['', f"Phase-only checked properties:{len(comparison['phase_only'])}; uniform-only:{len(comparison['uniform_only'])}. Lists and per-family counts are preserved in `pair-ablation-full-v1-analysis.json`.", '',
          'The earlier30s selected-survivor results are separate evidence. Fixed-budget differences may reflect discovery/checking cost as well as abstraction precision. Empty landmarks provide the uniform control with the same safety discovery, proof format, verifier, representation and pair-addition cap. No default portfolio changed.', '',
          'Every duplicate, unavailable slot and Unknown is retained. No reserved family was inspected. This local run does not establish cross-machine speed, competitive superiority, publication novelty, or the performance of an integrated portfolio.']
(ROOT / 'research/pair-ablation-full-v1-report.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({k:v for k,v in comparison.items() if k not in ['reason_property_counts','family_coverage']},indent=2))
