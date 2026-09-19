"""Deterministic, dependency-free text encoder.

Uses hashed word tokens plus character n-grams with L2 normalization so the
pilot runs without model downloads. Swap for sentence-transformers later by
implementing the same TextEncoder protocol; keep model_version distinct.
"""

import hashlib
import math
import re

_WORD = re.compile(r"[a-z0-9]+")


class HashingTextEncoder:
    model_version = "hash-ngram-v1"

    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions

    def _bucket(self, token: str) -> int:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "big") % self.dimensions

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dimensions
            for word in _WORD.findall(text.lower()):
                vec[self._bucket("w:" + word)] += 1.0
                padded = f"^{word}$"
                for n in (3, 4):
                    for i in range(len(padded) - n + 1):
                        vec[self._bucket("g:" + padded[i : i + n])] += 0.5
            norm = math.sqrt(sum(v * v for v in vec))
            if norm:
                vec = [v / norm for v in vec]
            vectors.append(vec)
        return vectors


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
