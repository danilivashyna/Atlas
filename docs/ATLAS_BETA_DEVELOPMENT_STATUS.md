# Atlas β — Статус разработки

**Статус:** 🔴 **В планировании** (начало разработки)  
**Целевой тег:** `v0.2.0-beta`  
**Ветка разработки:** `main` (релизные копии: `0.2.0-release`)  
**Последнее обновление:** 27.10.2025

---

## 📊 Общий прогресс

| Эпик | Статус | Прогресс | Крайний срок |
|------|--------|----------|--------------|
| E1. API & Контракты | 🔴 Not Started | 0% | TBD |
| E2. Индексы & MANIFEST | 🔴 Not Started | 0% | TBD |
| E3. Метрики памяти | 🔴 Not Started | 0% | TBD |
| E4. НФТ | 🔴 Not Started | 0% | TBD |
| E5. Документация | 🟢 In Progress | 30% | TBD |
| E6. (Опция) S1 | 🔴 Not Started | 0% | TBD |
| E7. Релизные артефакты | 🔴 Not Started | 0% | TBD |

**Общий прогресс: 4% (1/43 задач)**

---

## 📋 Детальный статус задач

### E1. API & Контракты

#### E1.1 Pydantic-схемы для всех эндпоинтов
- **Статус:** 🔴 Not Started
- **Ответственный:** TBD
- **Файлы:** `src/atlas/api/schemas.py`
- **Завершённо:** 0%

#### E1.2 `/encode` эндпоинт
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/api/routes/encode.py`
- **Завершённо:** 0%

#### E1.3 `/decode` эндпоинт
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/api/routes/decode.py`
- **Завершённо:** 0%

#### E1.4 `/explain` эндпоинт
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/api/routes/explain.py`
- **Завершённо:** 0%

#### E1.5 `/encode_h` эндпоинт
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/api/routes/encode_h.py`
- **Завершённо:** 0%

#### E1.6 `/decode_h` эндпоинт
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/api/routes/decode_h.py`
- **Завершённо:** 0%

#### E1.7 `/manipulate_h` эндпоинт
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/api/routes/manipulate_h.py`
- **Завершённо:** 0%

#### E1.8 `/search` с FAB-маршрутизацией
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/api/routes/search.py`, `src/atlas/fab/router.py`, `src/atlas/fab/merger.py`
- **Завершённо:** 0%

#### E1.9 `/health`, `/ready`, `/metrics`
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/api/routes/health.py`, `src/atlas/metrics.py`
- **Завершённо:** 0%

#### E1.10 Интеграционные тесты для API
- **Статус:** 🔴 Not Started
- **Файлы:** `tests/test_api_beta.py`
- **Завершённо:** 0%

---

### E2. Индексы & MANIFEST

#### E2.1 Построение HNSW индексов
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/indices/hnsw_builder.py`

#### E2.2 Построение FAISS индекса
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/indices/faiss_builder.py`

#### E2.3 Загрузка индексов и кэширование
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/indices/manager.py`

#### E2.4 MANIFEST генератор и валидатор
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/manifest/generator.py`, `src/atlas/manifest/validator.py`

#### E2.5 Атомарное переключение индексов
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/indices/switcher.py`

#### E2.6 Интеграционные тесты для индексов
- **Статус:** 🔴 Not Started
- **Файлы:** `tests/test_indices_beta.py`

---

### E3. Метрики памяти

#### E3.1 H-Coherence метрика
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/metrics/h_coherence.py`

#### E3.2 H-Stability метрика
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/metrics/h_stability.py`

#### E3.3 IR метрики (Recall@k, nDCG@k)
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/metrics/ir_metrics.py`

#### E3.4 Тестовые наборы для метрик
- **Статус:** 🔴 Not Started
- **Файлы:** `samples/metrics_test_set.json`

#### E3.5 Prometheus метрики для памяти
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/metrics/prometheus_exporter.py`

#### E3.6 Отчёт о метриках памяти
- **Статус:** 🔴 Not Started
- **Файлы:** `docs/METRICS_REPORT_BETA.md`

---

### E4. НФТ

#### E4.1 Логирование с trace_id и query_id
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/logging.py`

#### E4.2 Базовые rate-limits
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/api/middleware/rate_limit.py`

#### E4.3 Базовые алерты
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/alerts.py`

#### E4.4 Профилирование cold-start
- **Статус:** 🔴 Not Started
- **Файлы:** `scripts/benchmark_cold_start.py`

#### E4.5 Профилирование warm-paths
- **Статус:** 🔴 Not Started
- **Файлы:** `scripts/benchmark_search_latency.py`

#### E4.6 Profiling дашборд
- **Статус:** 🔴 Not Started
- **Файлы:** `scripts/profiling_dashboard.py`

---

### E5. Документация

#### E5.1 Обновить MODEL_CARD
- **Статус:** 🟢 In Progress
- **Файлы:** `docs/MODEL_CARD.md`
- **Завершённо:** 30%

#### E5.2 Обновить DATA_CARD
- **Статус:** 🔴 Not Started
- **Файлы:** `docs/DATA_CARD.md`

#### E5.3 Обновить NFR документ
- **Статус:** 🔴 Not Started
- **Файлы:** `docs/NFR.md`

#### E5.4 Обновить INTERPRETABILITY документ
- **Статус:** 🔴 Not Started
- **Файлы:** `docs/INTERPRETABILITY_METRICS.md`

#### E5.5 Обновить DISENTANGLEMENT документ
- **Статус:** 🔴 Not Started
- **Файлы:** `docs/DISENTANGLEMENT.md`

#### E5.6 Обновить README (Quick Start β)
- **Статус:** 🔴 Not Started
- **Файлы:** `README.md`

#### E5.7 Создать API docs (OpenAPI/Swagger)
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/api/openapi.py`

---

### E6. (Опция) Нейронный S1

#### E6.1 Загрузить encoder_base.mxfp16
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/models/encoder_loader.py`

#### E6.2 Валидировать нормировки и совместимость
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/models/validator.py`

#### E6.3 Интеграция S1 в `/encode_h`
- **Статус:** 🔴 Not Started
- **Файлы:** `src/atlas/api/routes/encode_h.py` (обновить)

---

### E7. Релизные артефакты

#### E7.1 Собрать индексы и MANIFEST
- **Статус:** 🔴 Not Started
- **Файлы:** `scripts/build_release.py`

#### E7.2 Dockerfile для β
- **Статус:** 🔴 Not Started
- **Файлы:** `Dockerfile.beta`

#### E7.3 Smoke-тесты для релиза
- **Статус:** 🔴 Not Started
- **Файлы:** `scripts/smoke_tests_beta.py`

#### E7.4 Release notes для v0.2.0-beta
- **Статус:** 🔴 Not Started
- **Файлы:** `docs/RELEASE_NOTES_v0.2.0-beta.md`

#### E7.5 Создать tag и publish release
- **Статус:** 🔴 Not Started

---

## 🎯 Цели приёмки

### Функциональные

- [ ] Все 8 основных API эндпоинтов работают и протестированы
- [ ] FAB маршрутизация и слияние (RRF/max_sim) детерминированы
- [ ] Индексы (HNSW/FAISS) построены и загружены успешно
- [ ] MANIFEST генерирован и валиден (SHA256, версионирование)
- [ ] Атомарное переключение индексов реализовано

### Метрики качества

- [ ] H-Coherence ≥ 0.78 (sent/para), ≥ 0.80 (para/doc)
- [ ] H-Stability drift ≤ 0.08
- [ ] Search latency p50 ≤ 60 ms (GPU) / ≤ 200 ms (CPU)
- [ ] `/ready` < 5 s (холодный старт ≤ 5M векторов)

### НФТ

- [ ] Логирование (ATLAS_LOG_LEVEL, trace_id, query_id)
- [ ] Prometheus метрики экспортируются
- [ ] Rate-limits работают (429 ответы)
- [ ] Алерты настраиваются
- [ ] Profiling дашборд доступен

### Безопасность

- [ ] FAB stateless (без состояния, без записи)
- [ ] Без auto-policy / attention механик
- [ ] MANIFEST валидация работает
- [ ] Роллбек индексов работает
- [ ] Нет online-learning без ревью

### Документация

- [ ] MODEL_CARD актуален
- [ ] DATA_CARD актуален
- [ ] NFR документ полный
- [ ] INTERPRETABILITY документ актуален
- [ ] DISENTANGLEMENT документ актуален
- [ ] README с Quick Start β
- [ ] API docs (Swagger/OpenAPI)

---

## ⚠️ Риски и блокеры

| Риск | Влияние | План смягчения |
|------|---------|-----------------|
| Производительность S1 (нейронный) | Высокое | Использовать rule-based fallback |
| Размер индексов > памяти | Высокое | Streaming load, сегментация |
| Совместимость encoder версий | Среднее | Strict MANIFEST валидация |
| Latency при cold-start | Среднее | Async preload, кэширование |

---

## 📅 Таймлайн

### Неделя 1 (27 Oct - 3 Nov)
- [ ] Начать E1 (API & Контракты): E1.1-E1.4
- [ ] Начать E2 (Индексы): E2.1-E2.2

### Неделя 2-3 (4 Nov - 17 Nov)
- [ ] Завершить E1 (оставить E1.10 на конец)
- [ ] Завершить E2
- [ ] Начать E3 (Метрики)

### Неделя 4-5 (18 Nov - 1 Dec)
- [ ] Завершить E3 (Метрики)
- [ ] Завершить E4 (НФТ)
- [ ] Начать E5 (Документация)

### Неделя 6-7 (2 Dec - 15 Dec)
- [ ] Завершить E5 (Документация)
- [ ] E6 (опция, если позволяет время)
- [ ] Начать E7 (Релизные артефакты)

### Неделя 8-9 (16 Dec - 31 Dec)
- [ ] Завершить E7 (Релизные артефакты)
- [ ] Final smoke-тесты
- [ ] Выпуск `v0.2.0-beta` 🚀

---

## 🔄 Зависимости

```
E1 (API) --→ E1.10 (Tests)
             ↓
E2 (Indices) --→ E2.6 (Tests)
             ↓
E3 (Metrics) --→ E3.6 (Report)
             ↓
E4 (NFT) --→ final smoke-tests (E7.3)
             ↓
E5 (Docs) --→ Release Notes (E7.4)
             ↓
E7 (Release) --→ v0.2.0-beta tag (E7.5) 🎯
```

---

## 📞 Контакты

| Роль | Ответственный | Email | Slack |
|------|---------------|-------|-------|
| Лид E1 (API) | TBD | TBD | TBD |
| Лид E2 (Indices) | TBD | TBD | TBD |
| Лид E3 (Metrics) | TBD | TBD | TBD |
| Лид E4 (NFT) | TBD | TBD | TBD |
| Лид E5 (Docs) | TBD | TBD | TBD |
| Лид E6 (S1) | TBD | TBD | TBD |
| Лид E7 (Release) | TBD | TBD | TBD |

---

## 🔗 Ссылки

- **ТЗ:** [TZ_ATLAS_BETA.md](./TZ_ATLAS_BETA.md)
- **Задачи:** [ATLAS_BETA_TASKS.md](./ATLAS_BETA_TASKS.md)
- **Ветка:** `main` (разработка) → `v0.2.0-beta` (тег)
- **GitHub Issues:** [Atlas v0.2.0-beta](https://github.com/danilivashyna/Atlas/issues?q=label%3Av0.2.0-beta)

---

## 📝 Обновления статуса

| Дата | Дельта | Автор | Примечания |
|------|--------|-------|-----------|
| 27.10.2025 | +4% (E5 начало) | Team | Инициализация, ТЗ готово, документация начата |
| TBD | - | - | - |
