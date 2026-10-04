from pathlib import Path
import json, hashlib, zipfile, datetime
root = Path(__file__).resolve().parents[2]
out = Path(__file__).resolve().parent
files = set()
def add(path):
    p = root/path
    if p.is_file() and not p.is_symlink():
        files.add(p)
def tree(path, suffixes=None):
    p = root/path
    if p.exists():
        for f in p.rglob('*'):
            if f.is_file() and not f.is_symlink() and '__pycache__' not in f.parts and (suffixes is None or f.suffix in suffixes):
                files.add(f)
for path in ('src','tests','examples','scripts'):
    tree(path)
for path in ('Cargo.toml','Cargo.lock','README.md','.gitignore'):
    add(path)
for path in ('research/grouped-excess-2026-10-04','research/count-dominance-v1','research/survivor-bounds-v1','research/benchmark-expansion-2026-10-04','research/coverage-iteration-20261004','research/direct-search-20261004','research/its-qualification-v1'):
    tree(path, {'.md','.json','.py','.log','.txt','.rs','.toml','.lock'})
for path in ('research/pro-direction-review-v1/answer.md','research/pro-direction-review-v1/assessment.md','research/pro-pair-review-v1/answer.md','research/pro-pair-review-v1/assessment.md','research/grouped-excess-20261004/RESULTS.md','research/grouped-excess-20261004/protocol.json','research/grouped-excess-20261004/plan.json','research/grouped-excess-20261004/full-audit.json','research/grouped-excess-20261004/run.py','results/grouped-excess-20261004/full/runs.jsonl'):
    add(path)
tree('research/grouped-excess-20261004/snapshot/src')
tree('research/grouped-excess-20261004/snapshot/tests')
for path in ('research/grouped-excess-20261004/snapshot/Cargo.toml','research/grouped-excess-20261004/snapshot/Cargo.lock'):
    add(path)
for path in ('results/coverage-iteration-20261004','results/direct-search-20261004'):
    tree(path, {'.jsonl','.json','.log'})
cohorts = {'existing176':'benchmarks/general-development-v3','expansion192':'benchmarks/development-expansion-v4'}
rows = [json.loads(line) for line in (root/'results/grouped-excess-20261004/full/runs.jsonl').read_text().splitlines()]
unsolved = {(r['corpus'],r['query']) for r in rows if r['method']=='candidate' and r['verdict']=='unknown'}
survivors = []
for corpus, location in cohorts.items():
    add(location+'/manifest.json')
    manifest = json.loads((root/location/'manifest.json').read_text())
    for q in manifest['queries']:
        if (corpus,q['name']) not in unsolved:
            continue
        survivors.append(dict(corpus=corpus,**q))
        add(location+'/'+q['pnml'])
        add(location+'/'+q['xml'])
        # Include all survivor canonical targets compactly, and one full canonical net per instance.
        for b in q['branches']:
            target = json.loads((root/location/b['path']).read_text())
            qout = out/'survivor-targets'/corpus/q['name']
            qout.mkdir(parents=True,exist_ok=True)
            (qout/(Path(b['path']).stem+'.json')).write_text(json.dumps({'places':target['places'],'target':target['target']},indent=2)+'\n')
        first = next(iter(q['branches']),None)
        if first is not None:
            canonical = out/'canonical-nets'/f"{q['instance']}.json"
            if not canonical.exists():
                canonical.parent.mkdir(exist_ok=True)
                canonical.write_bytes((root/location/first['path']).read_bytes())
(out/'survivors.json').write_text(json.dumps(survivors,indent=2)+'\n')
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
context = f'''# Consultation context\n\nPrepared at {now}. The current source files may include ongoing, unmeasured work. The frozen full-screen candidate is in research/grouped-excess-20261004/snapshot; its RESULTS.md and full-audit.json describe completed evidence. Current src/ and tests/ are newer.\n\nThe completed full screen has 31 unresolved original properties; survivor metadata and compact exact branch targets are in this consultation directory. Original PNML/XML is included for every unresolved query. canonical-nets contains one complete canonical branch per survivor model for convenient inspection; its target is only that example branch. The complete exact targets for other branches are in survivor-targets and original XML.\n\nCurrent development adds guarded large arithmetic stages, less expensive validation, acyclic count realization, exact enabled-action enumeration, backward cover, and positive scaling. Do not infer measured wins from their presence. Coverage-iteration and direct-search diagnostic rows, when present, are partial development evidence; root is still running them. At the time of the assignment, the first newer portfolio had one checked RERS5 RC01 witness in3.156s end-to-end (parse0.476s,solve2.630s), relaxed-batched677states438trace. Consult saved rows for newer completed observations. Positive scaling was being implemented independently; evaluate it or challenge it without making it the preferred direction.\n\nOriginal RERS models have1,446places151,085transitions with preserved total tokens90/162 and initial nonzero places carrying5/9tokens. The certified old survivor bounds and failed count-dominance diagnostic are included. Fixed-word repetition bounds do not rule out deeper paths or more general acceleration. The older Pro responses are historical suggestions, not established truth.\n\nNo proprietary credentials or unrelated personal files are intentionally included. Build outputs, executables, virtual environments, downloaded external solver binaries, duplicate canonical full nets per query, and unrelated historical research are omitted. The entire current source, test, example and script development plus build configuration is included.\n'''
(out/'CONSULTATION_CONTEXT.md').write_text(context)
for path in ('prompt.txt','CONSULTATION_CONTEXT.md','survivors.json','build_archive.py'):
    files.add(out/path)
tree(str(out.relative_to(root)/'survivor-targets'))
tree(str(out.relative_to(root)/'canonical-nets'))
manifest = {'created_utc':now,'files':{}}
archive = out/'development.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
    for p in sorted(files):
        data = p.read_bytes()
        rel = str(p.relative_to(root))
        manifest['files'][rel] = {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        z.writestr(rel,data)
    z.writestr('archive-manifest.json',json.dumps(manifest,indent=2)+'\n')
(out/'files-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
receipt = {'status':'prepared-not-submitted','created_utc':now,'archive':str(archive),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'archive_bytes':archive.stat().st_size,'archive_files':len(files),'conversation_url':None,'model_verified':False,'upload_completed':False,'blocker':'CUA reports Browser is not available: iab and browsers=[]; native Codex access rejected by CUA safety policy','prompt_path':str(out/'prompt.txt'),'answer_path':str(out/'answer.md'),'existing_monitor_id':'review-vass-algorithm-direction','monitor_updated':False}
(out/'submission.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
