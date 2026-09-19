"""Storage ports plus the default SQLite adapter."""

from functools import lru_cache
from pathlib import Path

from skill_erosion.config import db_path
from skill_erosion.storage.interfaces import EmbeddingIndex, TraceRepository
from skill_erosion.storage.sqlite_repo import SQLiteTraceRepository

__all__ = ["EmbeddingIndex", "SQLiteTraceRepository", "TraceRepository", "default_repository"]


@lru_cache(maxsize=8)
def default_repository(db_file: str | None = None) -> SQLiteTraceRepository:
    path = Path(db_file) if db_file else db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return SQLiteTraceRepository(path)
