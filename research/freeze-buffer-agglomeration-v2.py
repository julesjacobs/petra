import hashlib,json,shutil,subprocess,tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=root/'results/solver-buffer-agglomeration-v2';out.mkdir()
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
names=set(json.loads((root/'results/solver-buffer-agglomeration-v1/source-files-sha256.json').read_text()))
names.add('research/freeze-buffer-agglomeration-v2.py')
hashes={n:sha(root/n) for n in sorted(names)}
(out/'source-files-sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
with tarfile.open(out/'source.tar.gz','w:gz') as tar:
    for name in sorted(names):tar.add(root/name,arcname=name,recursive=False)
with tarfile.open(out/'source.tar.gz','r:gz') as tar:
    assert {m.name for m in tar.getmembers()}==names
    for m in tar.getmembers():assert hashlib.sha256(tar.extractfile(m).read()).hexdigest()==hashes[m.name]
for p in ('target/release/vass-reach','target/release/examples/inspect_buffer_agglomeration'):
    shutil.copy2(root/p,out/Path(p).name)
review=out/'review';review.mkdir()
for p in sorted((root/'research').glob('buffer-agglomeration-*')):
    if p.suffix in ('.log','.md'):shutil.copy2(p,review/p.name)
meta=dict(change='Discovery skips expanding merges and cumulative transition-cap violations; opt-in reduction semantics and independent checker unchanged.',
    binary_sha256=sha(out/'vass-reach'),inspector_sha256=sha(out/'inspect_buffer_agglomeration'),
    source_sha256=sha(out/'source.tar.gz'),source_files=len(names),
    build='cargo build --release --locked --examples --bin vass-reach',
    rustc=subprocess.check_output(['rustc','--version','--verbose'],text=True),
    validation='Prior full suite428passed1ignored; changed discovery rechecked with12module tests and9CLI tests.70Python tests passed; fmt,Clippy,release passed. Original unrestricted v1 guard failures retained.',
    performance='Not measured at freeze.',review_sha256={p.name:sha(p) for p in review.iterdir()})
(out/'provenance.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps({k:v for k,v in meta.items() if k.endswith('sha256') and type(v)is str}))
