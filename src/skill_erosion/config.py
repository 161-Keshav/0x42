"""Runtime paths and settings. Env overrides keep tests and demos isolated."""

import os
from functools import lru_cache
from pathlib import Path


def project_root() -> Path:
    override = os.environ.get("SKILL_EROSION_ROOT")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[2]


def db_path() -> Path:
    override = os.environ.get("SKILL_EROSION_DB")
    path = Path(override) if override else project_root() / "data" / "processed" / "traces.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def synthetic_attempts_path() -> Path:
    return project_root() / "data" / "synthetic" / "attempts.json"


def expected_trends_path() -> Path:
    return project_root() / "data" / "synthetic" / "expected_trends.json"


def taxonomy_path() -> Path:
    return project_root() / "config" / "skill_taxonomy.json"


def remediation_dir() -> Path:
    return project_root() / "resources" / "remediation"


@lru_cache(maxsize=1)
def known_skill_ids() -> frozenset[str]:
    import json

    data = json.loads(taxonomy_path().read_text(encoding="utf-8"))
    return frozenset(item["skill_id"] for item in data["skills"])
