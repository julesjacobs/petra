"""Freeze a separate runner; never mutate the active Linux comparison's scripts."""
from pathlib import Path
import hashlib,json,shutil,tarfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/runner-phase-pair-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
parents=json.loads((ROOT/'results/runner-repeated-search-v2/files-sha256.json').read_text())
OUT.mkdir();source=OUT/'source';source.mkdir()
for name,digest in parents.items():
    path=ROOT/name;assert sha(path)==digest,name
    target=source/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
shutil.copyfile(ROOT/'scripts/phase_pair_checker.py',source/'scripts/phase_pair_checker.py')
p=source/'scripts/benchmark.py';s=p.read_text();marker="    if kind == 'local-closure-v1':";assert s.count(marker)==1
s=s.replace(marker,"    if kind == 'phase-pair-closure-v1':\n        from phase_pair_checker import verify_phase_pair\n        return verify_phase_pair(problem, proof)\n"+marker);p.write_text(s)
p=source/'scripts/benchmark_smpt_classic.py';s=p.read_text();marker="ROOT/'scripts/local_closure_checker.py',";assert s.count(marker)==1;s=s.replace(marker,marker+" ROOT/'scripts/phase_pair_checker.py',");p.write_text(s)
files={str(p.relative_to(source)):sha(p) for p in sorted(source.rglob('*')) if p.is_file()}
(OUT/'files-sha256.json').write_text(json.dumps(files,indent=2)+'\n')
with tarfile.open(OUT/'runner.tar.gz','w:gz') as a:
    for name in files:a.add(source/name,arcname=name,recursive=False)
(OUT/'provenance.json').write_text(json.dumps(dict(parent=parents,files=files,archive_sha256=sha(OUT/'runner.tar.gz'),changes=['benchmark.py: new proof dispatch','benchmark_smpt_classic.py: snapshot new checker','phase_pair_checker.py: independent checker'],scope='Isolated runtime; original shared scripts unchanged.'),indent=2)+'\n')
print('Frozen',len(files),'files')
