# Атлас — Панель управления смыслом

**Atlas - Semantic Space Control Panel**: Интерфейс между абстрактным смыслом и конкретной формой.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL v3 / Commercial](https://img.shields.io/badge/License-AGPL%20v3%20%2F%20Commercial-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-64%20passing-brightgreen.svg)]()
[![API](https://img.shields.io/badge/API-FastAPI-009688.svg)]()

## 🎯 Ключевая идея

Атлас — это не просто визуализация векторов, а **когнитивный интерфейс**, где каждая ось — измерение понимания. Это зеркало, в котором смысл видит, как он движется в пространстве.

## 🌟 Особенности

- **5-мерное семантическое пространство** — каждая ось представляет отдельное измерение смысла
- **Иерархическое пространство (NEW!)** — "матрёшка 5D" с рекурсивными под-измерениями
- **Интерпретируемый декодер** — объясняет, почему выбран именно этот смысл
- **Визуальный интерфейс** — для исследования и манипуляции смысловым пространством
- **Осознанная настройка мышления** — можно вручную менять оси, "вращая" смысл

## 📐 5-мерное пространство

Пять регуляторов смыслового состояния (как ручки микшера мышления):

| Ось   | Семантика                    | Роль                        |
|-------|------------------------------|-----------------------------|
| dim₁  | Объект ↔ Действие           | Структура фразы             |
| dim₂  | Позитив ↔ Негатив           | Эмоциональный тон           |
| dim₃  | Абстрактное ↔ Конкретное    | Уровень обобщения           |
| dim₄  | Я ↔ Мир                     | Точка наблюдения            |
| dim₅  | Живое ↔ Механическое        | Сущностная природа          |

*Эти значения не жёсткие, а выявляемые обучением. Модель сама распределяет смысл между осями.*

## � Лицензирование (Dual License)

Atlas распространяется под **двойной лицензией**:

| Модель | Для кого | Условия |
|--------|----------|---------|
| **AGPLv3** | Открытый код | Свободное использование, распространение с исходниками |
| **Commercial** | Проприетарные проекты | Закрытый исходник, платная лицензия |

👉 **[Подробнее в docs/LICENSING.md](docs/LICENSING.md)** | Контакт: [danilivashyna@gmail.com](mailto:danilivashyna@gmail.com)

## �📊 Статус разработки (v0.2.0a1)

| Компонент | Статус | Детали |
|-----------|--------|--------|
| **Ядро** | | |
| ├─ Encoder (rule-based) | ✅ Готов | Простой эвристический энкодер |
| ├─ Decoder (interpretable) | ✅ Готов | Декодирование с объяснениями |
| ├─ Semantic Space | ✅ Готов | 5D пространство операций |
| ├─ Dimensions | ✅ Готов | Интерпретация измерений |
| ├─ Hierarchical Encoder | ✅ Готов | Иерархическое кодирование |
| ├─ Hierarchical Decoder | ✅ Готов | Декодирование по путям |
| └─ Hierarchical API | ✅ Готов | /encode_h, /decode_h, /manipulate_h |
| **API** | | |
| ├─ REST API (FastAPI) | ✅ Готов | /encode, /decode, /explain |
| ├─ Health checks | ✅ Готов | /health, /ready, /metrics |
| ├─ Request validation | ✅ Готов | Pydantic models |
| └─ Error handling | ✅ Готов | Graceful degradation |
| **Testing** | | |
| ├─ Unit tests | ✅ 50 тестов | Encoder, decoder, space, hierarchical |
| ├─ Golden samples | ✅ 16 тестов | Регрессионные тесты |
| ├─ API tests | ✅ 20 тестов | Integration tests |
| └─ Coverage | ✅ > 80% | Основной функционал |
| **Документация** | | |
| ├─ README | ✅ Готов | Основная документация |
| ├─ CONTRIBUTING | ✅ Готов | Гайд для контрибуторов |
| ├─ MODEL_CARD | ✅ Готов | Описание модели |
| ├─ NFR | ✅ Готов | Нефункц. требования |
| ├─ DATA_CARD | ✅ Готов | Описание данных |
| ├─ DISENTANGLEMENT | ✅ Готов | Методология разделения |
| └─ INTERPRETABILITY | ✅ Готов | Метрики интерпретируемости |
| **Deployment** | | |
| ├─ Docker | ✅ Готов | Dockerfile + compose |
| ├─ CLI | ✅ Готов | atlas command |
| └─ Python package | ✅ Готов | pip install |
| **Запланировано (v0.2+)** | | |
| ├─ Neural encoder | 🔄 В плане | BERT-based |
| ├─ Neural decoder | 🔄 В плане | Transformer |
| ├─ Disentanglement training | 🔄 В плане | β-TC-VAE |
| ├─ Hierarchical losses | 🔄 В плане | Ortho/sparsity/router |
| ├─ Hierarchical metrics | 🔄 В плане | H-Coherence, H-Stability |
| ├─ Distillation | 🔄 В плане | Teacher→Hierarchical |
| ├─ Metrics implementation | 🔄 В плане | Coherence, stability |
| └─ Human evaluation | 🔄 В плане | Аннотация |

**Легенда**: ✅ Готово | 🔄 В разработке | ⏳ Запланировано

## 🚀 Установка

```bash
# Клонировать репозиторий
git clone https://github.com/danilivashyna/Atlas.git
cd Atlas

# Установить зависимости
pip install -r requirements.txt

# Установить пакет
pip install -e .

# Для разработки (опционально)
# See: LOCAL_SETUP_COMPLETE.md for full dev guide
make setup    # Create venv
make dev      # Install dev dependencies
make test     # Run test suite
make api      # Start API server (http://localhost:8000/docs)
```

### Dev Setup для v0.2 (Hierarchical)

Полный гайд локальной разработки: **[LOCAL_SETUP_COMPLETE.md](LOCAL_SETUP_COMPLETE.md)**

```bash
# 1. Клонировать и перейти в директорию
git clone https://github.com/danilivashyna/Atlas.git
cd Atlas

# 2. Создать и активировать venv
python -m venv .venv
source .venv/bin/activate  # или .venv\Scripts\activate на Windows

# 3. Установить зависимости
pip install -U pip wheel
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu

# 4. Установить пакет + запустить тесты
pip install -e .
pytest tests/test_api_smoke.py -v

# 5. Запустить API
uvicorn src.atlas.api.app:app --reload --port 8000
# Перейти на http://localhost:8000/docs для Swagger UI
```

## 💡 Быстрый старт

### Python API

```python
from atlas import SemanticSpace

# Инициализировать пространство
space = SemanticSpace()

# Кодировать текст в 5D вектор
vector = space.encode("Собака")
print(f"Вектор: {vector}")

# Декодировать вектор в текст с рассуждением
result = space.decode(vector, with_reasoning=True)
print(result['reasoning'])
print(f"Текст: {result['text']}")

# Манипулировать измерением
result = space.manipulate_dimension(
    "Собака",
    dimension=1,  # Эмоциональный тон
    new_value=-0.9  # Сделать негативным
)
print(f"Изменено: {result['modified']['decoded']['text']}")
```

### Hierarchical API (NEW!)

```python
from atlas.hierarchical import HierarchicalEncoder, HierarchicalDecoder

# Инициализация
encoder = HierarchicalEncoder()
decoder = HierarchicalDecoder()

# Кодирование в иерархическое дерево
tree = encoder.encode_hierarchical(
    "Собака",
    max_depth=2,              # Глубина дерева
    expand_threshold=0.2      # Порог для раскрытия веток
)

# Декодирование с объяснением по путям
result = decoder.decode_hierarchical(tree, top_k=3, with_reasoning=True)
print(f"Текст: {result['text']}")
for r in result['reasoning']:
    print(f"  {r.path}: {r.label} (вес={r.weight:.2f})")

# Манипуляция по пути (хирургическая правка)
modified_tree = decoder.manipulate_path(
    tree,
    path="dim2/dim2.4",  # Конкретная ветка
    new_value=[0.9, 0.1, -0.2, 0.0, 0.0]
)
modified_result = decoder.decode_hierarchical(modified_tree)
print(f"Изменено: {modified_result['text']}")
```

### REST API

```bash
# Запустить сервер
python scripts/run_api.py
# или с Docker
docker-compose up

# Использовать API
curl -X POST "http://localhost:8000/encode" \
  -H "Content-Type: application/json" \
  -d '{"text": "Собака", "lang": "ru"}'

curl -X POST "http://localhost:8000/decode" \
  -H "Content-Type: application/json" \
  -d '{"vector": [0.1, 0.9, -0.5, 0.2, 0.8], "top_k": 3}'

curl -X POST "http://localhost:8000/explain" \
  -H "Content-Type: application/json" \
  -d '{"text": "Любовь"}'

# Hierarchical endpoints (NEW!)
curl -X POST "http://localhost:8000/encode_h" \
  -H "Content-Type: application/json" \
  -d '{"text": "Собака", "max_depth": 2, "expand_threshold": 0.2}'

curl -X POST "http://localhost:8000/decode_h" \
  -H "Content-Type: application/json" \
  -d '{"tree": {...}, "top_k": 3}'

curl -X POST "http://localhost:8000/manipulate_h" \
  -H "Content-Type: application/json" \
  -d '{"text": "Собака", "edits": [{"path": "dim2/dim2.4", "value": [0.9,0.1,-0.2,0.0,0.0]}]}'

# Документация API: http://localhost:8000/docs
```

### Командная строка

```bash
# Показать информацию об измерениях
atlas info

# Кодировать текст
atlas encode "Собака бежит" --explain

# Декодировать вектор с рассуждением
atlas decode --vector 0.1 0.9 -0.5 0.2 0.8 --reasoning

# Трансформировать текст
atlas transform "Любовь" --reasoning

# Манипулировать измерением
atlas manipulate "Собака" --dimension 1 --value -0.8 --reasoning

# Интерполировать между концептами
atlas interpolate "Любовь" "Ненависть" --steps 5

# Исследовать измерение
atlas explore "Жизнь" --dimension 4 --steps 7

# Hierarchical commands (NEW!)
atlas encode-h "Любовь" --max-depth 2 --expand-threshold 0.2
atlas decode-h --input tree.json --top-k 3 --reasoning
atlas manipulate-h "Собака" --edit dim2/dim2.4=0.9,0.1,-0.2,0.0,0.0 --reasoning
```

## 📊 Примеры

### Пример: Интерпретируемый декодер

**Ввод:** `[0.1, 0.9, -0.5, 0.2, 0.8]`

**Обычный AI:** "Собака."

**Атлас:**
```
Я чувствую, что:
dim₁ = 0.10 → слегка action (Структура фразы)
dim₂ = 0.90 → сильно positive (Эмоциональный тон)
dim₃ = -0.50 → умеренно concrete (Уровень обобщения)
dim₄ = 0.20 → слегка world (Точка наблюдения)
dim₅ = 0.80 → сильно living (Сущностная природа)
→ итог: "Собака"
```

### Пример: Манипуляция измерениями

```python
# Изменить эмоциональный тон
result = space.manipulate_dimension(
    "Радость",
    dimension=1,  # Позитив ↔ Негатив
    new_value=-0.9
)
# Результат: "Грусть" или "Тоска"
```

### Пример: Интерполяция концептов

```python
# Плавный переход между концептами
results = space.interpolate("Любовь", "Страх", steps=5)
# Показывает, как смысл постепенно трансформируется
```

## 🔬 Примеры использования

### Базовое использование

```bash
python examples/basic_usage.py
```

Демонстрирует:
- Кодирование текста в вектор
- Декодирование с рассуждением
- Манипуляцию измерениями
- Интерполяцию между концептами
- Исследование измерений

### Визуализация

```bash
python examples/visualization.py
```

Создаёт визуализации:
- Радарные диаграммы семантических векторов
- 2D проекции семантического пространства
- Визуализацию интерполяции

## 🏗️ Архитектура

```
atlas/
├── encoder.py      # Кодирование: текст → 5D вектор
├── decoder.py      # Декодирование: вектор → текст + рассуждение
├── dimensions.py   # Определение и интерпретация измерений
├── space.py        # Основной интерфейс семантического пространства
└── cli.py          # Интерфейс командной строки
```

### Компоненты

1. **Encoder** (`encoder.py`)
   - Сжимает тексты в 5-мерное пространство
   - Каждое измерение становится отдельной "осью смысла"

2. **Decoder** (`decoder.py`)
   - Восстанавливает текст из вектора
   - Объясняет, почему выбран именно этот смысл
   - Не просто "вектор → слово", а "вектор → история выбора"

3. **Dimensions** (`dimensions.py`)
   - Определяет 5 семантических измерений
   - Интерпретирует значения по каждой оси
   - Объясняет векторы человеческим языком

4. **Space** (`space.py`)
   - Объединяет encoder и decoder
   - Предоставляет API для манипуляции смыслом
   - Визуализация и исследование пространства

## 🎨 Зачем это нужно

### 1. Интерпретируемый AI
Можно увидеть, какая ось отвечает за какой смысл. AI перестаёт быть "чёрным ящиком".

### 2. Визуальный доступ к мышлению
Не только "что" модель поняла, но и "почему" — полная прозрачность процесса.

### 3. Осознанная настройка мышления
Можно вручную менять оси, "вращая" смысл, как спектр света в призме.

### 4. Универсальный интерфейс сознания
- Исследовать эмбеддинги (уменьшенные пространства)
- Наблюдать, как оси коррелируют с концептами
- "Управлять" мыслью, как параметром в аудиоредакторе

## 📚 Документация

### 🚀 v0.2 Development (Текущий спринт)

| Документ | Описание |
|----------|----------|
| [docs/v0.2_QUICK_SPECS.md](docs/v0.2_QUICK_SPECS.md) | **СТАРТ ЗДЕСЬ**: Краткая шпаргалка (print it!) |
| [docs/v0.2_IMPLEMENTATION_SPECS.md](docs/v0.2_IMPLEMENTATION_SPECS.md) | Полные спецификации для PRs #7-12 |
| [docs/v0.2_TASK_BRIEFS.md](docs/v0.2_TASK_BRIEFS.md) | 8 task briefs для всех веток (copy-paste) |
| [docs/v0.2_ASSIGNMENT_KICKOFF.md](docs/v0.2_ASSIGNMENT_KICKOFF.md) | Developer quick start (5-min read) |
| [docs/v0.2_DELIVERY_SUMMARY.md](docs/v0.2_DELIVERY_SUMMARY.md) | Executive summary + timelines |
| [docs/v0.2_TEAM_DEPLOYMENT.md](docs/v0.2_TEAM_DEPLOYMENT.md) | Manager guide for coordination |
| [docs/v0.2_PR_BODY_TEMPLATES.md](docs/v0.2_PR_BODY_TEMPLATES.md) | PR descriptions (ready to copy) |

### Основная документация

| Документ | Описание |
|----------|----------|
| [README.md](README.md) | Основная документация (этот файл) |
| [DOCUMENTATION.md](DOCUMENTATION.md) | Полная техническая документация |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Гайд для контрибуторов |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Кодекс поведения |
| [SECURITY.md](SECURITY.md) | Политика безопасности |
| [MODEL_CARD.md](MODEL_CARD.md) | Карточка модели |

### Техническая документация

| Документ | Описание |
|----------|----------|
| [docs/NFR.md](docs/NFR.md) | Нефункциональные требования (производительность, безопасность) |
| [docs/DATA_CARD.md](docs/DATA_CARD.md) | Описание данных для обучения |
| [docs/DISENTANGLEMENT.md](docs/DISENTANGLEMENT.md) | Методология разделения семантических измерений |
| [docs/INTERPRETABILITY_METRICS.md](docs/INTERPRETABILITY_METRICS.md) | Метрики интерпретируемости |
| [docs/HIERARCHICAL_SPACE.md](docs/HIERARCHICAL_SPACE.md) | Иерархическое семантическое пространство (NEW!) |

### API документация

### API Reference

#### `SemanticSpace`

Главный класс для работы с семантическим пространством.

```python
space = SemanticSpace()

# Кодирование
vector = space.encode(text)

# Декодирование
text = space.decode(vector, with_reasoning=True)

# Трансформация
result = space.transform(text, show_reasoning=True)

# Манипуляция
result = space.manipulate_dimension(text, dimension, new_value)

# Интерполяция
results = space.interpolate(text1, text2, steps=5)

# Исследование
results = space.explore_dimension(text, dimension, range_vals)

# Информация
info = space.get_dimension_info()
```

## 🧪 Тестирование

```bash
# Запустить тесты (когда будут добавлены)
pytest tests/
```

## 🤝 Вклад

Contributions are welcome! Пожалуйста:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 Лицензия

MIT License - см. [LICENSE](LICENSE) файл.

## 🌐 Философия

> **Атлас — это не модель, а зеркало, в котором смысл видит, как он двигается.**

Это визуальный мозг, отражающий структуру мышления. Через него можно не просто анализировать смысл, но и **управлять** им сознательно.

## 📞 Контакты

- GitHub: [@danilivashyna](https://github.com/danilivashyna)
- Repository: [Atlas](https://github.com/danilivashyna/Atlas)

---

**Atlas** — где смысл встречается с формой. 🗺️✨
