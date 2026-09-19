"""Persistent Chroma collections for semantic attempt and resource retrieval."""

from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from skill_erosion.config import project_root
from skill_erosion.logging_utils import get_logger

logger = get_logger("chroma")

_EMBEDDING_VERSION = "chroma-default-all-minilm-l6-v2"


def _client() -> chromadb.ClientAPI:
    path = project_root() / "data" / "processed" / "chroma"
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path))


def _collection(name: str):
    return _client().get_or_create_collection(
        name=name,
        embedding_function=DefaultEmbeddingFunction(),
        metadata={"hnsw:space": "cosine"},
    )


def attempt_collection():
    return _collection("skill-erosion-attempts")


def resource_collection():
    return _collection("skill-erosion-resources")


def embed_texts(texts: list[str]) -> list[list[float]]:
    return _collection("skill-erosion-embedding-helper")._embedding_function(texts)


def embedding_model_version() -> str:
    return _EMBEDDING_VERSION


def upsert(collection, *, ids, documents, metadatas) -> None:
    logger.info("chroma collection=%s operation=upsert items=%d", collection.name, len(ids))
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)


def query(collection, **kwargs):
    count = len(kwargs.get("query_texts") or kwargs.get("query_embeddings") or [])
    logger.info("chroma collection=%s operation=query items=%d", collection.name, count)
    result = collection.query(**kwargs)
    logger.info(
        "chroma collection=%s operation=query_result items=%d",
        collection.name,
        sum(len(row) for row in result.get("ids", [])),
    )
    return result


def get(collection, **kwargs):
    ids = kwargs.get("ids") or []
    logger.info("chroma collection=%s operation=get items=%d", collection.name, len(ids))
    return collection.get(**kwargs)
