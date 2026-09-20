import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/"docs/verification/upstream-manifest.json").read_text())
failures=[]
for name,digest in manifest["files"].items():
    p=ROOT/name
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest: failures.append(name)
required=["config/skill_taxonomy.json","resources/remediation/catalog.json","src/skill_erosion/mcp_server.py","src/skill_erosion/metrics.py","src/skill_erosion/orchestration/pipeline.py","src/skill_erosion/contracts/models.py","src/skill_erosion/storage/sqlite_repo.py","apps/teacher_dashboard/app.py","apps/student_portal/app.py","apps/parent_portal/app.py","data/synthetic/attempts.json","data/synthetic/attempts.csv","data/synthetic/expected_trends.json"]
failures += [p for p in required if not (ROOT/p).is_file()]
for folder in ("slice","demo","web","docs","scripts","tests"):
    originals=[name for name in manifest["files"] if name.startswith(folder+"/")]
    print(f"{folder}/: {len(originals)} original files present and byte-identical" if not any(n in failures for n in originals) else f"{folder}/: integrity failure")
for name in ("PRINCIPLES-BRIEF.md","ARCHITECTURE.md","DESIGNER.md","BUILDER.md","VERIFIER.md","ON-THE-DAY.md","SPEC-TEMPLATE.md"):
    print(f"docs/{name}: {'present' if (ROOT/'docs'/name).exists() else 'MISSING'}")
print("Upstream revision:",manifest["revision"])
print(f"Protected files: {len(manifest['files'])}; new required files: {len(required)}; failures: {len(failures)}")
if failures: raise SystemExit("Integrity/scaffold failures: "+", ".join(failures))
