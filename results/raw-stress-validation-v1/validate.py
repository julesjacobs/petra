import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/"scripts"))
from raw_stress_worker import sha256,load_json,validate,require
p=Path(sys.argv[1]); require(sha256(p)==sys.argv[2],"hash mismatch")
q=load_json(p); validate(q); require(sha256(p)==sys.argv[2],"input changed")
print(json.dumps(dict(status="validated",places=len(q["places"]),transitions=len(q["transitions"]),components=len(q["target"]["excluded_semilinear"]))))
