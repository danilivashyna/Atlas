# ⚡ Atlas v0.2 - Быстрый Справочник

**Версия**: 0.2.0a2 (в разработке)
**Статус**: ✅ Инфраструктура готова
**Команда**: 8 параллельных feature branches

---

## 🎯 Главные Команды

### 1️⃣ Посмотреть Статус Проекта

```bash
# Показать все v0.2 PR-ы и Issues
./tools/manage_v0.2.sh status

# Альтернативно (через gh CLI)
gh pr list --repo danilivashyna/Atlas -l v0.2
gh issue list --repo danilivashyna/Atlas -l v0.2
```

### 2️⃣ Назначить Разработчиков

```bash
# Распределить PRs round-robin
./tools/manage_v0.2.sh assign alice,bob,charlie

# Или вручную одному человеку
gh issue edit 14 --repo danilivashyna/Atlas --add-assignee alice
```

### 3️⃣ Начать Разработку

```bash
# Получить свежий код
git fetch origin
git checkout feature/v0.2-01-encoder-bert

# Implement feature...
git add .
git commit -m "feat(v0.2-01): Implement TextEncoder5D with MiniLM"
git push origin feature/v0.2-01-encoder-bert
```

### 4️⃣ Подготовить к Review

```bash
# Конвертировать Draft PR → Ready (когда готово)
gh pr ready 5 --repo danilivashyna/Atlas

# Или все одновременно
./tools/manage_v0.2.sh ready
```

### 5️⃣ Запросить Review

```bash
# Запросить ревью у мейнтейнера
./tools/manage_v0.2.sh review danilivashyna

# Или вручную
gh pr edit 5 --repo danilivashyna/Atlas --add-reviewer danilivashyna
```

### 6️⃣ Отслеживать Прогресс

```bash
# Смотреть все открытые v0.2-issues
gh issue list --repo danilivashyna/Atlas -l v0.2 -s open

# Или открыть в браузере
gh issue list --repo danilivashyna/Atlas -l v0.2 --web

# Или через скрипт
./tools/manage_v0.2.sh web
```

---

## 📊 Текущее Состояние

### PRs (8 draft, готовы к разработке)

```
#5   v0.2-01: TextEncoder5D ..................... ready
#6   v0.2-02: Transformer Decoder .............. ready
#7   v0.2-03: API Endpoints .................... ready
#8   v0.2-04: Hierarchical Losses .............. ready
#9   v0.2-05: Distillation Pipeline ............ ready
#10  v0.2-06: Metrics Suite .................... ready
#11  v0.2-07: Benchmarks Suite ................. ready
#12  v0.2-08: Docs & Demos ..................... ready
```

### Issues (8 open, отслеживают работу)

```
#14  v0.2-01: TextEncoder5D
#15  v0.2-02: Transformer Decoder
#16  v0.2-03: API Endpoints
#17  v0.2-04: Hierarchical Losses
#18  v0.2-05: Distillation Pipeline
#19  v0.2-06: Metrics Suite
#20  v0.2-07: Benchmarks Suite
#21  v0.2-08: Docs & Demos
```

---

## 🔗 Важные Ссылки

| Ссылка | Назначение |
|--------|-----------|
| [Issues (v0.2)](https://github.com/danilivashyna/Atlas/issues?q=label%3Av0.2) | Все issues с меткой v0.2 |
| [PRs (v0.2)](https://github.com/danilivashyna/Atlas/pulls?q=label%3Av0.2) | Все PRs с меткой v0.2 |
| [Branches](https://github.com/danilivashyna/Atlas/branches) | Все feature branches |
| [Actions](https://github.com/danilivashyna/Atlas/actions) | CI/CD результаты |

---

## 💡 Типичный Workflow

### День 1: Развёртывание

```bash
# 1. Вытащить все изменения
git pull origin main

# 2. Посмотреть PR-ы
gh pr list --repo danilivashyna/Atlas -l v0.2
```

### День 2-7: Разработка

```bash
# 1. Выбрать feature
git checkout feature/v0.2-01-encoder-bert

# 2. Разработать (см. docs/v0.2_DEVELOPMENT_STATUS.md)
# ... write code ...
# ... run tests ...

# 3. Коммитить и пушить
git add -A
git commit -m "feat: Add TextEncoder5D implementation"
git push origin feature/v0.2-01-encoder-bert
```

### День 8: Review & Merge

```bash
# 1. Конвертировать PR в готовый (не draft)
./tools/manage_v0.2.sh ready
# или
gh pr ready 5 --repo danilivashyna/Atlas

# 2. Добавить описание PR с checklist-ом
# ... GitHub web UI ...

# 3. Запросить review
./tools/manage_v0.2.sh review danilivashyna

# 4. После approval - merge
gh pr merge 5 --repo danilivashyna/Atlas --squash
```

---

## 🛠️ Полезные Скрипты

### Проверить Статус Всех Веток

```bash
git fetch --all
git branch -vv | grep "feature/v0.2"
```

### Обновить Все Ветки из Main

```bash
for branch in $(git branch | grep feature/v0.2); do
  git checkout "$branch"
  git rebase origin/main
done
git checkout main
```

### Посмотреть Кто Что Делает

```bash
gh issue list --repo danilivashyna/Atlas -l v0.2 \
  --json number,title,assignees \
  -q '.[] | "\(.number): \(.title) - @\(.assignees[].login // "unassigned")"'
```

---

## 📚 Документация

| Файл | Содержимое |
|------|-----------|
| `docs/v0.2_DEVELOPMENT_STATUS.md` | Подробное описание всех 8 features |
| `docs/v0.2_LAUNCH_CHECKLIST.md` | Чеклист для onboarding команды |
| `docs/GITHUB_CLI_CHEATSHEET.md` | Полный справочник gh CLI (200+ примеров) |
| `docs/GITHUB_AUTOMATION_STATUS.md` | Статус автоматизации |
| `tools/manage_v0.2.sh` | Основной скрипт управления |

---

## ❓ FAQ

**Q: Как я узнаю что мне нужно делать?**
A: Прочитай `docs/v0.2_DEVELOPMENT_STATUS.md` для своего feature, смотри Issue и PR.

**Q: Как запустить тесты?**
A: `pytest tests/ -q` (или для своей feature: `pytest tests/test_v0.2_*.py -q`)

**Q: Как убедиться в покрытии?**
A: `pytest --cov=src/atlas tests/ --cov-report=html` (нужно >80%)

**Q: Что если конфликт при merge?**
A: Решить конфликты локально, коммитить, пушить - автоматизм заработает.

**Q: Как линковать Issue в PR?**
A: Добавить в описание PR: "Closes #14" или "Relates to #14"

**Q: Где я могу помочь помимо своего feature?**
A: Issues помечены `help wanted` - можно брать по инициативе.

---

## ✅ Checklist для Успешной Разработки

- [ ] Клонировал branch: `git checkout feature/v0.2-0X-*`
- [ ] Прочитал описание в Issue #X
- [ ] Понял requirements в `docs/v0.2_DEVELOPMENT_STATUS.md`
- [ ] Запустил существующие тесты: `pytest tests/ -q`
- [ ] Реализовал feature с unit tests
- [ ] Запустил все тесты - все проходят ✅
- [ ] Проверил покрытие: `pytest --cov` >80%
- [ ] Не добавил deprecation warnings
- [ ] Код прошёл Black formatter
- [ ] Добавил docstring'и
- [ ] Коммиты имеют смысл (не 1 гигантский коммит)
- [ ] Пушнул в GitHub
- [ ] Конвертировал PR из Draft в Ready
- [ ] Запросил review

---

## 🚀 Speed Tips

```bash
# Быстро переключаться между ветками
alias v0.2-1='git checkout feature/v0.2-01-encoder-bert'
alias v0.2-2='git checkout feature/v0.2-02-decoder-transformer'
# и т.д.

# Быстро смотреть статус
alias v0.2-status='./tools/manage_v0.2.sh status'
alias v0.2-web='./tools/manage_v0.2.sh web'

# Быстро запустить тесты
alias test-v0.2='pytest tests/test_*_v0.2_*.py -q'
```

---

**Версия**: v0.2.0a2
**Последнее обновление**: 2025-10-19
**Контакт**: GitHub Issues с меткой v0.2
