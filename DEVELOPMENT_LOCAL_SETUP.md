# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

# Локальный запуск Atlas в VS Code (v0.2)

Быстрый гайд для разработки и запуска Atlas на локальной машине.

## 📋 Требования

- Python 3.10+ (рекомендуется 3.11+)
- VS Code с расширением Python
- Git (для клонирования репозитория)
- ~500MB свободного места (для PyTorch)

## 🚀 Быстрый старт (5 минут)

### Шаг 1: Клонирование репозитория

```bash
# Создаём директорию проектов (если не существует)
mkdir -p ~/Projects
cd ~/Projects

# Клонируем Atlas
git clone https://github.com/danilivashyna/Atlas.git
cd Atlas

# Проверяем структуру
ls -la
```

### Шаг 2: Создание виртуального окружения

```bash
# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

### Шаг 3: Установка зависимостей

```bash
# Обновляем pip
pip install -U pip wheel setuptools

# Устанавливаем зависимости
pip install -r requirements.txt

# PyTorch (CPU по умолчанию)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Установка самого пакета
pip install -e .

# (Опционально) Для разработки: dev dependencies
pip install pytest pytest-cov black ruff mypy
```

### Шаг 4: Проверка установки

```bash
# Python API
python -c "from atlas import SemanticSpace; print('✓ Atlas imported successfully')"

# CLI
atlas info
```

## 🎮 Запуск в VS Code

### Вариант 1: Использование встроенных конфигураций (рекомендуется)

1. **Откройте VS Code:**
   ```bash
   code .
   ```

2. **Выберите Run Configuration (Ctrl+Shift+D):**
   - `API (Uvicorn, reload)` — запустит REST API на `http://localhost:8000`
   - `Tests (pytest)` — запустит тесты
   - `Example: Basic Usage` — запустит базовый пример
   - `CLI: encode` — запустит CLI команду

3. **Нажмите F5 или кнопку Run**

### Вариант 2: Запуск через Makefile

```bash
# Показать все команды
make help

# Запустить API
make api
# API будет на http://localhost:8000

# Запустить тесты
make test

# Проверить код (lint)
make lint

# Форматировать код
make format
```

### Вариант 3: Прямой запуск в терминале

```bash
# API сервер
uvicorn src.atlas.api.app:app --reload --host 0.0.0.0 --port 8000

# В другом терминале: проверка здоровья
curl http://localhost:8000/health

# Документация API (откройте в браузере)
http://localhost:8000/docs
```

## 📍 Тестирование API

### cURL команды

```bash
# Health check
curl http://localhost:8000/health

# Encode (плоское)
curl -X POST http://localhost:8000/encode \
  -H "Content-Type: application/json" \
  -d '{"text":"Собака","lang":"ru"}'

# Decode (плоское)
curl -X POST http://localhost:8000/decode \
  -H "Content-Type: application/json" \
  -d '{"vector":[0.1,0.9,-0.5,0.2,0.8],"top_k":3}'

# Encode hierarchical (NEW!)
curl -X POST http://localhost:8000/encode_h \
  -H "Content-Type: application/json" \
  -d '{"text":"Собака","max_depth":2,"expand_threshold":0.2}'

# Decode hierarchical (NEW!)
curl -X POST http://localhost:8000/decode_h \
  -H "Content-Type: application/json" \
  -d '{"tree":{"value":[0.1,0.9,-0.5,0.2,0.8]},"top_k":3}'
```

### REST Client в VS Code

1. Установите расширение "REST Client" (Huachao Mao)
2. Создайте файл `requests.http`:

```http
### Health check
GET http://localhost:8000/health

### Encode flat
POST http://localhost:8000/encode
Content-Type: application/json

{
  "text": "Собака",
  "lang": "ru"
}

### Encode hierarchical
POST http://localhost:8000/encode_h
Content-Type: application/json

{
  "text": "Собака",
  "max_depth": 2,
  "expand_threshold": 0.2
}

### Decode hierarchical
POST http://localhost:8000/decode_h
Content-Type: application/json

{
  "tree": {
    "value": [0.1, 0.9, -0.5, 0.2, 0.8]
  },
  "top_k": 3
}
```

3. Нажмите "Send Request" над каждым блоком

## 🧪 Запуск примеров

```bash
# Базовое использование
python examples/basic_usage.py

# Комплексная демонстрация
python examples/comprehensive_demo.py

# Визуализация (если установлены matplotlib и seaborn)
python examples/visualization.py

# Проблемное выражение
python examples/problem_statement_example.py
```

## 🔧 Дополнительные конфигурации

### VS Code расширения (рекомендуемые)

Установите эти расширения для лучшего опыта разработки:

```bash
# Python, Pylance
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance

# Форматирование
code --install-extension ms-python.black-formatter
code --install-extension charliermarsh.ruff

# REST API
code --install-extension humao.rest-client
code --install-extension rangav.vscode-thunder-client

# Git
code --install-extension eamodio.gitlens
code --install-extension donjayamanne.githistory

# Docker (опционально)
code --install-extension ms-azuretools.vscode-docker
```

### .env конфиг (опционально)

Создайте `.env` в корне проекта:

```bash
# Окружение
ATLAS_ENV=dev

# Logging
LOG_LEVEL=DEBUG
PYTHONUNBUFFERED=1

# API
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# Models
PYTORCH_DEVICE=cpu  # или cuda для GPU
TRANSFORMERS_CACHE=~/.cache/huggingface/hub
```

## 🐛 Отладка

### VS Code Debugging

В `.vscode/launch.json` уже есть конфигурации для отладки:

1. **Установите точку останова** (F9 на нужной строке)
2. **Выберите конфигурацию** (Ctrl+Shift+D)
3. **Нажмите F5**
4. **Используйте консоль** для просмотра переменных

### Логирование

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

## 🚨 Решение проблем

### Проблема: "ModuleNotFoundError: No module named 'atlas'"

**Решение:**
```bash
pip install -e .
```

### Проблема: "ImportError: No module named 'torch'"

**Решение:**
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Проблема: "Address already in use :8000"

**Решение:**
```bash
# Убить процесс на порту 8000
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

### Проблема: "No such file or directory: '.venv/bin/activate'"

**Решение:**
```bash
python -m venv .venv
source .venv/bin/activate
```

## 📊 Бенчмарки

```bash
# Запустить бенчмарки (v0.2+)
make bench

# Или напрямую
python scripts/benchmark_hierarchical.py
```

## 🔄 Рабочий процесс разработки

### 1. Создание ветки для нового функционала

```bash
git checkout -b feature/my-feature
```

### 2. Разработка и тестирование

```bash
# Делайте изменения
# ... code ...

# Форматируйте код
make format

# Проверяйте синтаксис
make lint

# Запускайте тесты
make test
```

### 3. Коммит и push

```bash
git add .
git commit -m "feat: описание изменений"
git push origin feature/my-feature
```

### 4. Pull Request

- Откройте PR на GitHub
- Дождитесь проверок CI
- Получите апрув
- Мержьте в main

## 📚 Документация v0.2

Новые компоненты v0.2:

| Модуль | Файл | Описание |
|--------|------|----------|
| **Encoder** | `src/atlas/models/encoder_bert.py` | BERT-based 5D encoder |
| **Decoder** | `src/atlas/models/decoder_transformer.py` | Interpretable Transformer decoder |
| **Losses** | `src/atlas/models/losses_hier.py` | Ortho/Sparsity/Entropy losses |
| **Metrics** | `src/atlas/metrics/metrics_hier.py` | H-Coherence, H-Stability (stubs) |
| **Distill** | `src/atlas/training/distill.py` | Knowledge distillation loss |
| **API** | `src/atlas/api/app.py` | FastAPI endpoints (/encode_h, /decode_h, /manipulate_h) |

## 🎯 Следующие шаги

- [ ] Запустить `make api` и открыть http://localhost:8000/docs
- [ ] Попробовать `python examples/basic_usage.py`
- [ ] Прочитать [docs/HIERARCHICAL_SPACE.md](../docs/HIERARCHICAL_SPACE.md)
- [ ] Создать свой первый PR!

---

**Вопросы?** Откройте issue на GitHub: [Atlas Issues](https://github.com/danilivashyna/Atlas/issues)
