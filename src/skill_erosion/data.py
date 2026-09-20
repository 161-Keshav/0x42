import csv
import json
from pathlib import Path

def read_attempts(path):
    path=Path(path)
    if path.suffix==".json": return json.loads(path.read_text(encoding="utf-8"))
    if path.suffix!=".csv": raise ValueError("Use CSV or JSON fixtures")
    with path.open(encoding="utf-8", newline="") as f: rows=list(csv.DictReader(f))
    for row in rows:
        for field in ("similarity_to_prior","self_reported_confidence"):
            if row.get(field)=="": row[field]=None
    return rows
