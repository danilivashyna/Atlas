from __future__ import annotations

import math
import threading
import time
from typing import Dict, List, Optional, Tuple

try:
    import faiss  # type: ignore

    HAS_FAISS = True
except Exception:
    HAS_FAISS = False


# ---- Simple TTL+LRU cache (v0.5.2) ----
class TTLCacheLRU:
    def __init__(self, capacity: int = 2048, ttl: float = 300.0) -> None:
        self.capacity = capacity
        self.ttl = ttl
        self._store: Dict[str, Tuple[float, object]] = {}
        self._order: List[str] = []
        self._lock = threading.Lock()

    def get(self, key: str):
        now = time.time()
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            ts, val = item
            if now - ts > self.ttl:
                self._store.pop(key, None)
                try:
                    self._order.remove(key)
                except ValueError:
                    pass
                return None
            # LRU bump
            try:
                self._order.remove(key)
            except ValueError:
                pass
            self._order.append(key)
            return val

    def set(self, key: str, val) -> None:
        now = time.time()
        with self._lock:
            if key in self._store:
                self._store[key] = (now, val)
                try:
                    self._order.remove(key)
                except ValueError:
                    pass
                self._order.append(key)
                return
            if len(self._order) >= self.capacity:
                evict = self._order.pop(0)
                self._store.pop(evict, None)
            self._store[key] = (now, val)
            self._order.append(key)


# ---- Query embed cache facade (uses TTLCacheLRU) ----
class QueryEmbedCache:
    def __init__(self, size: int = 2048, ttl: float = 300.0) -> None:
        self.cache = TTLCacheLRU(capacity=size, ttl=ttl)
        self.hits = 0
        self.misses = 0

    def get_or_compute(self, key: str, fn):
        v = self.cache.get(key)
        if v is not None:
            self.hits += 1
            return v, True
        self.misses += 1
        v = fn()
        self.cache.set(key, v)
        return v, False


# ---- Node ANN interface ----
class NodeANN:
    def rebuild(self, items: List[Tuple[str, List[float]]]) -> int:
        raise NotImplementedError

    def add_nodes(self, items: List[Tuple[str, List[float]]]) -> int:
        raise NotImplementedError

    def remove_nodes(self, paths: List[str]) -> int:
        raise NotImplementedError

    def search(self, vec: List[float], top_k: int) -> List[Tuple[str, float]]:
        raise NotImplementedError

    def size(self) -> int:
        raise NotImplementedError


# ---- In-process ANN (naive, but incremental) ----
class InprocANN(NodeANN):
    def __init__(self) -> None:
        self._data: Dict[str, List[float]] = {}

    def rebuild(self, items: List[Tuple[str, List[float]]]) -> int:
        self._data = {p: v for p, v in items}
        return len(self._data)

    def add_nodes(self, items: List[Tuple[str, List[float]]]) -> int:
        for p, v in items:
            self._data[p] = v
        return len(items)

    def remove_nodes(self, paths: List[str]) -> int:
        cnt = 0
        for p in paths:
            if p in self._data:
                self._data.pop(p, None)
                cnt += 1
        return cnt

    def _cos(self, a: List[float], b: List[float]) -> float:
        num = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1e-9
        nb = math.sqrt(sum(y * y for y in b)) or 1e-9
        return num / (na * nb)

    def search(self, vec: List[float], top_k: int) -> List[Tuple[str, float]]:
        scored = [(p, self._cos(vec, v)) for p, v in self._data.items()]
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:top_k]

    def size(self) -> int:
        return len(self._data)


# ---- FAISS ANN (optional) ----
class FAISSANN(NodeANN):
    def __init__(self, dim: int = 5) -> None:
        if not HAS_FAISS:
            raise RuntimeError("FAISS not available")
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self._paths: List[str] = []
        self._vectors: List[List[float]] = []

    def _rebuild_index(self):
        import numpy as np

        arr = np.array(self._vectors, dtype="float32")
        # cosine → normalize
        norms = (arr**2).sum(1, keepdims=True) ** 0.5
        norms[norms == 0] = 1.0
        arr = arr / norms
        self.index = faiss.IndexFlatIP(self.dim)
        if len(arr):
            self.index.add(arr)

    def rebuild(self, items: List[Tuple[str, List[float]]]) -> int:
        self._paths = [p for p, _ in items]
        self._vectors = [v for _, v in items]
        self._rebuild_index()
        return len(self._paths)

    def add_nodes(self, items: List[Tuple[str, List[float]]]) -> int:
        # простая реализация: дописываем и пересобираем (можно сделать add без полного rebuild)
        self._paths += [p for p, _ in items]
        self._vectors += [v for _, v in items]
        self._rebuild_index()
        return len(items)

    def remove_nodes(self, paths: List[str]) -> int:
        if not paths:
            return 0
        keep = [(p, v) for p, v in zip(self._paths, self._vectors) if p not in paths]
        self._paths = [p for p, _ in keep]
        self._vectors = [v for _, v in keep]
        self._rebuild_index()
        return len(paths)

    def search(self, vec: List[float], top_k: int) -> List[Tuple[str, float]]:
        import numpy as np

        v = np.array([vec], dtype="float32")
        n = (v**2).sum(1, keepdims=True) ** 0.5
        n[n == 0] = 1.0
        v = v / n
        if self.index.ntotal == 0:
            return []
        D, I = self.index.search(v, top_k)
        res = []
        for idx, score in zip(I[0], D[0]):
            if 0 <= idx < len(self._paths):
                res.append((self._paths[idx], float(score)))
        return res

    def size(self) -> int:
        return len(self._paths)


# ---- Factory + singletons ----
_ANN_INSTANCE: Optional[NodeANN] = None
_QUERY_CACHE: Optional[QueryEmbedCache] = None


def get_ann_index(backend: str = "inproc") -> Optional[NodeANN]:
    global _ANN_INSTANCE
    if _ANN_INSTANCE is not None:
        return _ANN_INSTANCE
    if backend == "faiss":
        _ANN_INSTANCE = FAISSANN(dim=5)
    elif backend == "off":
        return None
    else:
        _ANN_INSTANCE = InprocANN()  # inproc or safe-off
    return _ANN_INSTANCE


def get_query_cache(size: int = 2048, ttl: float = 300.0) -> QueryEmbedCache:
    global _QUERY_CACHE
    if _QUERY_CACHE is None:
        _QUERY_CACHE = QueryEmbedCache(size=size, ttl=ttl)
    return _QUERY_CACHE
