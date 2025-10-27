# Atlas β — Safety Boundaries

## Философия: Zero Human-level Self-Improvement (HSI)

Atlas β — это **статический, детерминированный поисковый система** с жёсткими границами. Никакие компоненты не могут самостоятельно улучшаться, адаптироваться или учиться.

---

## Что строго запрещено (Out of Scope)

### 1. Никакие политики внимания / намерений
- **Запрещено:** Использовать сигналы о "важности" запроса для маршрутизации.
- **Запрещено:** Кэшировать "популярные" запросы или давать им приоритет.
- **Запрещено:** Использовать контекст о пользователе для изменения логики.
- **Только:** Детерминированная маршрутизация по конфигу (routes.yaml).

### 2. Никакое онлайн-обучение (online learning)
- **Запрещено:** Обновлять веса индексов HNSW на основе feedback.
- **Запрещено:** Переобучать encoder на примерах из production.
- **Запрещено:** Динамически менять MANIFEST без ревью и перезагрузки.
- **Только:** Offline обучение → новый MANIFEST → manual deployment.

### 3. Никакое внутриграфовое состояние (hidden state)
- **Запрещено:** Кэш внутри FAB с auto-invalidation.
- **Запрещено:** Скрытые переменные в роутере (position bias, query budget).
- **Запрещено:** Side-channel коммуникация между запросами.
- **Только:** Stateless FAB + внешний read-through кэш (Redis с TTL).

### 4. Никакой автоматической рекофигурации (auto-reconfig)
- **Запрещено:** Менять параметры индексов на лету (M, ef_search, nlist).
- **Запрещено:** Auto-scaling структуры индекса по трафику.
- **Запрещено:** Динамически выбирать fuse-алгоритм.
- **Только:** Конфиг меняется через новый коммит в git → review → deployment.

---

## Технические предохранители

### Предохранитель 1: ConfigLoader как единственный источник конфигов

**Механизм:**
```python
from src.atlas.configs import ConfigLoader

# Все конфиги читаются ровно один раз при старте приложения
routes = ConfigLoader.get_api_routes()  # read-only
indices = ConfigLoader.get_all_index_configs()  # read-only
metrics = ConfigLoader.get_metrics_config()  # read-only
```

**Гарантия:**
- Нет "скрытого" конфига, подгруженного из окружения или base64 в коде.
- Любое изменение конфига → ошибка линтера (ConfigLoader.check_config_integrity()).
- Все инициализации явные, в одном месте.

**Проверка:** `scripts/validate_baseline.py --strict`

---

### Предохранитель 2: MANIFEST верификация с SHA256

**Механизм:**
```json
{
  "version": "0.2.0-beta",
  "created_at": "2025-10-27T10:30:00Z",
  "models": {
    "teacher": {
      "name": "nomic-embed-text-1.5",
      "hash": "sha256:abc123...xyz789",
      "url": "s3://atlas-models/teacher/nomic-1.5/model.safetensors"
    }
  },
  "indices": {
    "sentence": {
      "type": "hnsw",
      "index_file": "s3://atlas-indices/sentence.hnsw",
      "hash": "sha256:def456..."
    }
  },
  "schema": "src/atlas/configs/indices/manifest_schema.json"
}
```

**Гарантия:**
- При старте приложение загружает MANIFEST и проверяет его против `manifest_schema.json`.
- Любое изменение hash или версии → validation error → panic.
- Нельзя случайно загрузить старый индекс с новым кодом.

**Проверка:** 
```bash
python scripts/validate_baseline.py --manifest MANIFEST.v0_2.json
```

---

### Предохранитель 3: Детерминированные fuse-алгоритмы

**RRF (Reciprocal Rank Fusion):**
```python
def fuse_rrf(bucket1, bucket2, bucket3, k=60):
    scores = defaultdict(float)
    for rank, hit in enumerate(bucket1):
        scores[hit['id']] += 1.0 / (rank + k)
    for rank, hit in enumerate(bucket2):
        scores[hit['id']] += 1.0 / (rank + k)
    for rank, hit in enumerate(bucket3):
        scores[hit['id']] += 1.0 / (rank + k)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**Гарантия:**
- Одинаковый ввод (bucket1, bucket2, bucket3) → одинаковый результат.
- Нет randomness, нет epsilon-greedy выборки.
- Воспроизводимо в тестах.

**max_sim (element-wise max):**
```python
def fuse_max_sim(embeddings_list):
    return element_wise_max(*embeddings_list)
```

**Гарантия:**
- Pure function, result = f(input).
- Тесты проверяют reproducibility на CI.

**Проверка:**
```bash
python scripts/smoke_test_wiring.py  # Проверяет RRF reproducibility
```

---

### Предохранитель 4: Метрики-пороги в конфиге

**Механизм:**
```yaml
# src/atlas/configs/metrics/h_metrics.yaml
h_coherence:
  sent_to_para_min: 0.78
  para_to_doc_min: 0.80

h_stability:
  max_drift: 0.08

ir:
  recall_at_10_min: 0.75

latency:
  p50_ms_gpu: 60
  p95_ms_gpu: 150
  p99_ms_gpu: 300
```

**Гарантия:**
- Все пороги в конфиге, видны в git diff.
- CI тесты проверяют метрики против пороговых значений.
- Тест падает, если coherence < 0.78 или latency > 150ms.
- Нет "скрытого" бенчмарка в коде.

**Проверка:**
```bash
pytest tests/test_h_coherence.py -v  # Читает h_metrics.yaml, проверяет пороги
```

---

### Предохранитель 5: Нулевая runtime-мутация (zero runtime mutation)

**Запрещено:**
```python
# ❌ Плохо: изменение конфига в рантайме
def update_ef_search(new_ef):
    ConfigLoader._cached_configs['indices']['ef_search'] = new_ef
```

**Разрешено:**
```python
# ✅ Хорошо: новый MANIFEST → перезапуск сервиса
# 1. Commit новый MANIFEST
# 2. CI: validate_baseline.py --manifest новый_MANIFEST.json
# 3. Deployment инструмент перезагружает сервис
# 4. Новый ef_search из конфига
```

**Гарантия:**
- Изменения артефактов (модели, индексы) → git history.
- Rollback = `git revert` + redeploy.
- Все изменения видны в git log.

---

## Граничные проверки на CI

| Проверка | Команда | Что проверяет | Fail если |
|----------|---------|---------------|-----------|
| Config lint | `python scripts/validate_baseline.py --strict` | Все конфиги load и consistent | Синтаксис или range мимо bounds |
| Manifest validation | `python scripts/validate_baseline.py --manifest MANIFEST.v0_2.json` | MANIFEST against schema | Версия, хеши, типы не совпадают |
| Smoke wiring | `python scripts/smoke_test_wiring.py` | /search, /encode_h, RRF reproducibility | Shape или контракт нарушен |
| H-Coherence test | `pytest tests/test_h_coherence.py` | sent→para ≥0.78, para→doc ≥0.80 | Когда-то ниже порога |
| Latency test | `pytest tests/test_latency.py` | p50 ≤ 60ms (GPU), p95 ≤ 150ms | SLA нарушен |
| Reproducibility | `pytest tests/test_reproducibility.py` | Одинаковый запрос → одинаковый результат | RRF или decode нарушены |

---

## Контрольный список безопасности (Pre-deployment)

Перед каждым deployment в prod:

- [ ] **Git log clean:** Все изменения конфигов видны в `git log --oneline docs/ src/atlas/configs/`
- [ ] **validate_baseline.py passed:** `python scripts/validate_baseline.py --strict`
- [ ] **MANIFEST valid:** `python scripts/validate_baseline.py --manifest MANIFEST.v0_2.json`
- [ ] **Smoke tests passed:** `python scripts/smoke_test_wiring.py`
- [ ] **H-Coherence targets met:** `pytest tests/test_h_coherence.py -v`
- [ ] **Latency SLA met:** `pytest tests/test_latency.py -v`
- [ ] **Reproducibility check:** `pytest tests/test_reproducibility.py`
- [ ] **Code review signed off:** ≥2 reviewers одобрили PR
- [ ] **No runtime config access:** grep -r "os.environ\|request.headers\|session.get" src/atlas/api/ → 0 результатов
- [ ] **ConfigLoader.check_integrity() passes:** При startu сервиса логирует OK

---

## Зачем это нужно?

**Риск 1: Drift в продакшене**
- Без MANIFEST: старый индекс + новый encoder → неправильные результаты.
- С MANIFEST: версии совпадают, или sервис не стартует.

**Риск 2: Скрытое изменение логики**
- Без конфигов: A/B тест внутри кода, никто не видит.
- С конфигами в git: все изменения в review, видны в diff.

**Риск 3: Онлайн-обучение → дисперсия**
- Без границ: система адаптируется к noise, качество деградирует.
- С границами: качество stable, reproducible.

**Риск 4: Детерминизм нарушен**
- Без RRF: softmax/sampling → разные результаты на одинаковый ввод.
- С RRF: одинаковый ввод → одинаковый результат (кэширующие).

---

## FAQ

**Q: Как мне добавить новый параметр индекса?**

A: 
1. Отредактируй `src/atlas/configs/indices/*.yaml`
2. Запусти `python scripts/validate_baseline.py --strict`
3. Обнови `ConfigLoader.get_index_config()`
4. Создай PR, review, merge в main
5. Deploy новой версии с новым конфигом

**Q: Можно ли кэшировать внутри FAB?**

A: Нет, FAB stateless. Кэш может быть в Redis снаружи (с TTL и invalidation логикой).

**Q: Как обновить модели?**

A: 
1. Offline обучение → новые веса
2. Сгенерировать новый MANIFEST с SHA256
3. Запустить `validate_baseline.py --manifest новый_MANIFEST.json`
4. PR + review
5. Deploy → sервис перезагружается, загружает новый MANIFEST

**Q: Что если тест упал, но метрика выглядит OK?**

A: Не mergeй PR. Проверь:
- Ошибка в тесте? → Поправь и перепроверь.
- Ошибка в конфиге? → Обнови пороги в h_metrics.yaml с обоснованием.
- Ошибка в коде? → Доработай и перепроверь.

**Q: Можно ли отключить валидацию для быстрого теста?**

A: Только локально (флаг `--skip-validation` на разработке). На CI — всегда валидируй.

