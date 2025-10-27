# Atlas β — E1-E3 Development Roadmap

**Фокус:** API контракты → Индексы → Метрики (базовый каркас)  
**Период:** 2–3 недели, параллельная разработка  
**Ветки:** `feature/E1-*`, `feature/E2-*`, `feature/E3-*`  
**PR размер:** 200–400 строк max, "одна мысль — один PR"

---

## E1 — API & Контракты (неделя 1)

### 1.1: Pydantic-схемы из конфигов

**Модуль:** `src/atlas/api/schemas.py`

```python
# Генерируем или маппим вручную из configs/api/schemas.json
from pydantic import BaseModel
from typing import List, Optional

class EncodeRequest(BaseModel):
    text: str
    metadata: Optional[dict] = None

class EncodeResponse(BaseModel):
    vector: List[float]

class SearchRequest(BaseModel):
    query: str
    levels: List[str] = ["sentence", "paragraph", "document"]
    top_k: int = 10
    fuse: str = "RRF"

class SearchResponse(BaseModel):
    hits: List[dict]
    debug: Optional[dict] = None

# ... остальные schemas
```

**Acceptance:**
- ✅ `from atlas.api.schemas import EncodeRequest` работает
- ✅ `make validate` 🟢
- ✅ `pytest tests/test_api_schemas.py` проходит

**PR:** `feature/E1-1-pydantic-schemas` (150–200 строк)

---

### 1.2: FastAPI маршруты по routes.yaml

**Модуль:** `src/atlas/api/routes.py`

```python
from fastapi import FastAPI, HTTPException
from src.atlas.configs import ConfigLoader
from src.atlas.api.schemas import (
    EncodeRequest, EncodeResponse,
    SearchRequest, SearchResponse,
    # ... остальные
)

app = FastAPI(title="Atlas β API", version="0.2.0")

# Загружаем конфиги при старте
routes_cfg = ConfigLoader.get_api_routes()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/encode")
async def encode(req: EncodeRequest) -> EncodeResponse:
    # TODO: реальная реализация в E1.3
    return EncodeResponse(vector=[0.0] * 384)

@app.post("/search")
async def search(req: SearchRequest) -> SearchResponse:
    # TODO: реальная реализация в E1.3
    return SearchResponse(hits=[])

# ... остальные 8 endpoints из routes.yaml
```

**Acceptance:**
- ✅ `uvicorn src.atlas.api.app:app` стартует
- ✅ `curl http://localhost:8010/health` → 200
- ✅ `pytest tests/test_api_routes.py` проходит
- ✅ Все 8 эндпоинтов зарегистрированы

**PR:** `feature/E1-2-fastapi-routes` (200–300 строк)

---

### 1.3: FAB-мембрана (статическая маршрутизация)

**Модуль:** `src/atlas/fab/router.py`

```python
from typing import List, Dict, Any
from collections import defaultdict

def route_search(query: str, levels: List[str], k: int) -> Dict[str, List[dict]]:
    """Параллельная fan-out к трём уровням индексов (mock)."""
    # В реальности будет параллельный вызов к sent/para/doc индексам
    results = {
        "sent": mock_knn("sentence", query, k),
        "para": mock_knn("paragraph", query, k),
        "doc": mock_knn("document", query, k),
    }
    return results

def fuse_rrf(buckets: List[List[Dict[str, Any]]], k: int = 60) -> List[Dict[str, Any]]:
    """RRF fusion: score = Σ 1/(rank_i + k). Детерминированно."""
    agg = defaultdict(float)
    
    for hits in buckets:
        for rank, hit in enumerate(hits):
            agg[hit["id"]] += 1.0 / (rank + k)
    
    merged = [{"id": hid, "score": score} for hid, score in agg.items()]
    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged[:k]

def mock_knn(level: str, query: str, k: int) -> List[Dict[str, Any]]:
    """Mock KNN results (детерминированно по query)."""
    seed = hash((level, query)) & 0xfffffff
    hits = []
    for i in range(k):
        score = 1.0 - i / (k + 3)
        hits.append({"id": f"{level}-{i}", "score": score, "level": level})
    return hits
```

**Модуль:** `src/atlas/fab/clients.py`

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class IndexClient(ABC):
    """Интерфейс клиента индекса."""
    
    @abstractmethod
    async def knn(self, query: List[float], k: int) -> List[Dict[str, Any]]:
        pass

class HNSWClient(IndexClient):
    """Mock HNSW клиент (пока заглушка)."""
    async def knn(self, query: List[float], k: int) -> List[Dict[str, Any]]:
        # TODO: реальная HNSW при появлении индекса
        return []

class FAISSClient(IndexClient):
    """Mock FAISS клиент (пока заглушка)."""
    async def knn(self, query: List[float], k: int) -> List[Dict[str, Any]]:
        # TODO: реальный FAISS при появлении индекса
        return []
```

**Acceptance:**
- ✅ `from atlas.fab.router import fuse_rrf, route_search` работает
- ✅ RRF детерминирован (одинаковый ввод → одинаковый результат)
- ✅ `pytest tests/test_fab_router.py` проходит
- ✅ `make smoke` зелёный (проверяет reproducibility)

**PR:** `feature/E1-3-fab-router` (150–200 строк)

---

### 1.4: ConfigLoader в инициализацию API

**Обновление:** `src/atlas/api/routes.py`

```python
from src.atlas.configs import ConfigLoader

# При старте приложения
def on_startup():
    # Загрузить конфиги и проверить целостность
    routes = ConfigLoader.get_api_routes()
    indices = ConfigLoader.get_all_index_configs()
    metrics = ConfigLoader.get_metrics_config()
    
    # Проверить что всё скачилось
    assert routes is not None, "routes.yaml не загрузился"
    assert indices is not None, "index configs не загрузились"
    
    print("✅ Configs loaded and validated")

app.add_event_handler("startup", on_startup)
```

**Acceptance:**
- ✅ Сломанный конфиг → `make validate` падает ❌
- ✅ Корректный конфиг → `make validate` зелёный ✅
- ✅ `make smoke` работает

**PR:** `feature/E1-4-configloader-integration` (50–100 строк)

---

## E2 — Индексы & MANIFEST (неделя 2)

### 2.1: Index builders

**Скрипт:** `scripts/build_indexes.py`

```python
#!/usr/bin/env python3
"""Построить индексы из конфигов."""

import pathlib
import json
from src.atlas.configs import ConfigLoader

def build_indexes():
    """Создать stub индексы с корректными метаданными."""
    
    # Загрузить конфиги
    sent_cfg = ConfigLoader.get_index_config("sentence")
    para_cfg = ConfigLoader.get_index_config("paragraph")
    doc_cfg = ConfigLoader.get_index_config("document")
    
    # Создать директорию
    idx_dir = pathlib.Path("indexes")
    idx_dir.mkdir(exist_ok=True)
    
    # Создать stub HNSW индексы (пока просто metadata JSON)
    for level, cfg in [("sent", sent_cfg), ("para", para_cfg)]:
        meta = {
            "type": "hnsw",
            "level": level,
            "M": cfg["M"],
            "ef_construction": cfg["ef_construction"],
            "ef_search": cfg["ef_search"],
            "vector_dim": 384,
            "num_vectors": 0  # stub
        }
        with (idx_dir / f"{level}.hnsw.meta.json").open("w") as f:
            json.dump(meta, f, indent=2)
    
    # Создать stub FAISS индекс
    doc_meta = {
        "type": "faiss",
        "level": "doc",
        "nlist": doc_cfg["ivf"]["nlist"],
        "m": doc_cfg["pq"]["m"],
        "nbits": doc_cfg["pq"]["nbits"],
        "vector_dim": 384,
        "num_vectors": 0  # stub
    }
    with (idx_dir / "doc.faiss.meta.json").open("w") as f:
        json.dump(doc_meta, f, indent=2)
    
    print("✅ Index stubs created")

if __name__ == "__main__":
    build_indexes()
```

**Acceptance:**
- ✅ `python scripts/build_indexes.py` создаёт `indexes/*.meta.json`
- ✅ `make validate` зелёный
- ✅ Метаданные совпадают с конфигом

**PR:** `feature/E2-1-index-builders` (100–150 строк)

---

### 2.2: MANIFEST генератор

**Скрипт:** `tools/make_manifest.py`

```python
#!/usr/bin/env python3
"""Сгенерировать MANIFEST.v0_2.json с SHA256 и метаданными."""

import json
import pathlib
import hashlib
import subprocess
from datetime import datetime

def sha256_file(fpath):
    """Вычислить SHA256 файла."""
    h = hashlib.sha256()
    with open(fpath, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

def get_git_info():
    """Получить git commit и branch."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
    except Exception:
        commit = "unknown"
        branch = "unknown"
    return {"commit": commit, "branch": branch}

def make_manifest(out_path="MANIFEST.v0_2.json"):
    """Создать MANIFEST."""
    
    manifest = {
        "version": "0.2.0-beta",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "git": get_git_info(),
        "models": {
            "teacher": {
                "name": "stub-teacher",
                "hash": "sha256:" + ("0" * 64),  # placeholder
                "url": "s3://stub/teacher"
            }
        },
        "indices": {
            "sentence": {
                "type": "hnsw",
                "hash": "sha256:" + sha256_file("indexes/sent.hnsw.meta.json"),
            },
            "paragraph": {
                "type": "hnsw",
                "hash": "sha256:" + sha256_file("indexes/para.hnsw.meta.json"),
            },
            "document": {
                "type": "faiss",
                "hash": "sha256:" + sha256_file("indexes/doc.faiss.meta.json"),
            }
        },
        "schema": "src/atlas/configs/indices/manifest_schema.json"
    }
    
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"✅ MANIFEST written to {out_path}")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="MANIFEST.v0_2.json")
    args = ap.parse_args()
    make_manifest(args.out)
```

**Acceptance:**
- ✅ `python tools/make_manifest.py --out MANIFEST.v0_2.json` создаёт файл
- ✅ `python scripts/validate_baseline.py --manifest MANIFEST.v0_2.json` проходит валидацию ✅
- ✅ SHA256 хеши соответствуют артефактам

**PR:** `feature/E2-2-manifest-generator` (100–150 строк)

---

## E3 — Метрики (базовый каркас) (неделя 2–3)

### 3.1: H-метрик каркас

**Модуль:** `src/atlas/metrics/h_memory.py`

```python
"""H-Coherence и H-Stability вычисления."""

from typing import Dict, Any
from src.atlas.configs import ConfigLoader
import numpy as np

def compute_h_coherence(sent_embeddings: np.ndarray, para_embeddings: np.ndarray) -> float:
    """
    H-Coherence между sentence и paragraph уровнями.
    Формула (stub): средний cosine similarity.
    """
    # Нормализовать
    sent_norm = np.linalg.norm(sent_embeddings, axis=1, keepdims=True)
    para_norm = np.linalg.norm(para_embeddings, axis=1, keepdims=True)
    
    sent_normalized = sent_embeddings / (sent_norm + 1e-10)
    para_normalized = para_embeddings / (para_norm + 1e-10)
    
    # Средний cosine similarity (stub упрощение)
    min_len = min(len(sent_normalized), len(para_normalized))
    scores = [
        np.dot(sent_normalized[i], para_normalized[i])
        for i in range(min_len)
    ]
    return np.mean(scores) if scores else 0.0

def compute_h_stability(embeddings_t0: np.ndarray, embeddings_t1: np.ndarray) -> float:
    """
    H-Stability: дрейф embeddings между двумя моментами.
    Формула (stub): средняя L2 норма разницы.
    """
    diff = np.linalg.norm(embeddings_t0 - embeddings_t1, axis=1)
    return float(np.mean(diff))

def check_h_metrics(sent_emb, para_emb, doc_emb) -> Dict[str, Any]:
    """Проверить H-метрики против пороговых значений."""
    
    cfg = ConfigLoader.get_metrics_config()
    
    # Вычислить H-Coherence
    h_coh_sp = compute_h_coherence(sent_emb, para_emb)
    h_coh_pd = compute_h_coherence(para_emb, doc_emb)
    
    # Получить пороги
    h_coh_sp_target = cfg["h_coherence"]["sent_to_para"]["target"]
    h_coh_pd_target = cfg["h_coherence"]["para_to_doc"]["target"]
    
    # Проверить
    passed = (h_coh_sp >= h_coh_sp_target and h_coh_pd >= h_coh_pd_target)
    
    return {
        "h_coherence": {
            "sent_to_para": {"value": h_coh_sp, "target": h_coh_sp_target, "passed": h_coh_sp >= h_coh_sp_target},
            "para_to_doc": {"value": h_coh_pd, "target": h_coh_pd_target, "passed": h_coh_pd >= h_coh_pd_target},
        },
        "passed": passed
    }
```

**Acceptance:**
- ✅ `from atlas.metrics.h_memory import check_h_metrics` работает
- ✅ Пороги читаются из `h_metrics.yaml`
- ✅ `pytest tests/test_h_metrics.py` проходит

**PR:** `feature/E3-1-h-metrics-framework` (150–200 строк)

---

### 3.2: Скрипт для локальной проверки метрик

**Скрипт:** `scripts/run_h_metrics.py`

```python
#!/usr/bin/env python3
"""Запустить H-метрик проверку локально."""

import json
import numpy as np
from src.atlas.metrics.h_memory import check_h_metrics

def run_h_metrics():
    """Mock embeddings и проверить metrics."""
    
    # Генерировать mock embeddings (L2-normalized)
    num_samples = 100
    dim = 384
    
    sent_emb = np.random.randn(num_samples, dim)
    sent_emb /= np.linalg.norm(sent_emb, axis=1, keepdims=True)
    
    para_emb = np.random.randn(num_samples, dim)
    para_emb /= np.linalg.norm(para_emb, axis=1, keepdims=True)
    
    doc_emb = np.random.randn(num_samples, dim)
    doc_emb /= np.linalg.norm(doc_emb, axis=1, keepdims=True)
    
    # Проверить H-метрики
    result = check_h_metrics(sent_emb, para_emb, doc_emb)
    
    # Вывести отчёт
    print(json.dumps(result, indent=2))
    
    if result["passed"]:
        print("\n✅ H-metrics PASSED")
        return 0
    else:
        print("\n❌ H-metrics FAILED")
        return 1

if __name__ == "__main__":
    exit(run_h_metrics())
```

**Acceptance:**
- ✅ `python scripts/run_h_metrics.py` работает
- ✅ JSON отчёт с метриками и пороговыми значениями
- ✅ Exit code 0 (pass) или 1 (fail)

**PR:** `feature/E3-2-h-metrics-script` (100–150 строк)

---

## CI / Защита веток

### GitHub Actions: `.github/workflows/validate.yml`

```yaml
name: Validate

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -e .[dev]
      
      - name: Validate configs (strict)
        run: make validate
      
      - name: Smoke tests
        run: make smoke
      
      - name: Run tests
        run: pytest tests/ -v
```

### Branch Protection Rules

- ✅ Require status checks (validate, smoke, tests)
- ✅ Require PRs reviewed
- ✅ Auto-delete head branches

---

## Acceptance на каждый этап

### E1 ✅
- [ ] Pydantic-схемы в `src/atlas/api/schemas.py`
- [ ] 8 FastAPI маршрутов в `src/atlas/api/routes.py`
- [ ] FAB-мембрана (router.py, clients.py)
- [ ] ConfigLoader в инициализацию
- [ ] `make validate` 🟢
- [ ] `make smoke` 🟢
- [ ] `/health` → 200
- [ ] `pytest tests/test_api_*.py` 🟢

### E2 ✅
- [ ] Index builders создают stub индексы
- [ ] MANIFEST генерируется и проходит валидацию
- [ ] `python scripts/build_indexes.py` работает
- [ ] `python tools/make_manifest.py --out MANIFEST.v0_2.json` работает
- [ ] `python scripts/validate_baseline.py --manifest MANIFEST.v0_2.json` 🟢

### E3 ✅
- [ ] H-метрик каркас в `src/atlas/metrics/h_memory.py`
- [ ] Скрипт `scripts/run_h_metrics.py` работает
- [ ] Пороги читаются из конфига
- [ ] `pytest tests/test_h_metrics.py` 🟢

---

## Быстрые команды

```bash
# Разработка
uvicorn src.atlas.api.app:app --reload

# Валидация
make validate
make smoke

# Тесты
pytest tests/ -v

# MANIFEST
python tools/make_manifest.py --out MANIFEST.v0_2.json
python scripts/validate_baseline.py --manifest MANIFEST.v0_2.json --strict

# H-метрики
python scripts/run_h_metrics.py
```

---

## Напоминание: Границы безопасности

❌ **Запрещено:**
- Политики внимания / намерений
- Онлайн-обучение
- Hidden state внутри FAB
- Auto-reconfig параметров

✅ **Правильно:**
- FAB = stateless маршрутизация + детерминированный RRF
- Все параметры в конфигах (routes.yaml, *.yaml, metrics.yaml)
- Изменения через git → review → deploy + перезагрузка
- MANIFEST верифицирует все артефакты

---

**Статус:** 🟢 **READY TO START E1**

