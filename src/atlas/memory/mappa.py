from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Dict, List, Optional, Tuple


def _cosine(a: List[float], b: List[float]) -> float:
    # Compute cosine similarity for 5D vectors
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass
class MappaMemory:
    """Lightweight in-process memory for tests.

    Stores 5D vectors keyed by id with optional metadata and supports
    simple cosine similarity queries.
    """

    _store: Dict[str, Tuple[List[float], Optional[dict]]] = field(default_factory=dict)

    def write(self, id: str, vector: List[float], meta: Optional[dict] = None) -> None:
        if not isinstance(vector, list) or len(vector) != 5:
            raise ValueError("vector must be a list of 5 floats")
        self._store[id] = (vector, meta)

    def query(self, vector: List[float], top_k: int = 5) -> List[dict]:
        if not isinstance(vector, list) or len(vector) != 5:
            raise ValueError("vector must be a list of 5 floats")

        scores = []
        for k, (v, meta) in self._store.items():
            sim = _cosine(vector, v)
            scores.append((sim, k, v, meta))

        scores.sort(key=lambda x: x[0], reverse=True)

        items = []
        for sim, k, v, meta in scores[:top_k]:
            items.append({"id": k, "score": float(sim), "vector": v, "meta": meta})

        return items


# Singleton instance for convenience in tests
MEMORY = MappaMemory()
