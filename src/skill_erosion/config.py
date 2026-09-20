import json
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def _load_dotenv(path=None):
    """Read .env into the environment, once. Real exported vars always win
    (setdefault), so a Codespaces secret or shell export still overrides the
    file. Mirrors slice/config.py's loader so the two halves of the kit share
    a single .env with no duplicated logic."""
    try:
        for line in (path or ROOT / ".env").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
    except FileNotFoundError:
        pass

_load_dotenv()

def data_dir(): return Path(os.environ.get("SKILL_EROSION_DATA_DIR", ROOT / "data"))
def load_taxonomy():
    return json.loads((ROOT / "config/skill_taxonomy.json").read_text(encoding="utf-8"))
def skill_map(): return {s["skill_id"]: s for s in load_taxonomy()["skills"]}
