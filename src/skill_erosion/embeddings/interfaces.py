from typing import Protocol


class TextEncoder(Protocol):
    model_version: str

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Use the same pinned encoder for indexed and query text."""
        ...
