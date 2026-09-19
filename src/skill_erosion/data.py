"""Loaders for synthetic fixtures and curated resources."""

import json

from skill_erosion.config import (
    expected_trends_path,
    remediation_dir,
    synthetic_attempts_path,
)
from skill_erosion.contracts.models import Attempt


def load_synthetic_attempts() -> list[Attempt]:
    rows = json.loads(synthetic_attempts_path().read_text(encoding="utf-8"))
    return [Attempt(**row) for row in rows]


def load_expected_trends() -> dict[str, dict]:
    return json.loads(expected_trends_path().read_text(encoding="utf-8"))


def load_resource_catalog() -> list[dict]:
    return json.loads((remediation_dir() / "catalog.json").read_text(encoding="utf-8"))


def load_resource_body(resource: dict) -> str:
    return (remediation_dir() / resource["path"]).read_text(encoding="utf-8")
