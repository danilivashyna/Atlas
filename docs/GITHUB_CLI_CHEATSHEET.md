# 🔧 GitHub CLI v0.2 Шпаргалка

Практический гайд для управления 8 feature branches, PR-ами и Issues через GitHub CLI.

**Требования**:
- Установить: `brew install gh` (macOS)
- Авторизоваться: `gh auth login`

---

## 🚀 Быстрый Старт

```bash
# Проверить, что всё работает
gh auth status

# Установить репо по умолчанию в переменную
export REPO="danilivashyna/Atlas"

# Список всех v0.2 PR-ов
gh pr list --repo "$REPO" -l v0.2

# Список всех v0.2 Issues
gh issue list --repo "$REPO" -l v0.2
```

---

## 📋 PR-операции

### Просмотр и управление

```bash
# Показать все draft PR-ы
gh pr list --repo "$REPO" --search "is:draft" -q '.[] | .number'

# Показать PR с деталями
gh pr view 5 --repo "$REPO"

# Открыть PR в браузере
gh pr view 5 --repo "$REPO" --web

# Показать последние изменения в PR
gh pr diff 5 --repo "$REPO"
```

### Метки и назначение

```bash
# Добавить метку к PR
gh pr edit 5 --repo "$REPO" --add-label "v0.2,urgent"

# Убрать метку
gh pr edit 5 --repo "$REPO" --remove-label "draft"

# Назначить разработчика
gh pr edit 5 --repo "$REPO" --add-assignee "alice"

# Назначить ревьюера
gh pr edit 5 --repo "$REPO" --add-reviewer "bob,charlie"

# Удалить ревьюера
gh pr edit 5 --repo "$REPO" --remove-reviewer "bob"
```

### Draft ↔ Ready

```bash
# Конвертировать Draft → Ready (готово к review)
gh pr ready 5 --repo "$REPO"

# Конвертировать Ready → Draft
gh pr ready 5 --repo "$REPO" --undo

# Скрыть/развернуть PR
gh pr close 5 --repo "$REPO"    # Закрыть
gh pr reopen 5 --repo "$REPO"   # Открыть
```

### Связь с Issues

```bash
# Добавить комментарий в PR (с ссылкой на issue)
gh pr comment 5 --repo "$REPO" --body "Closes #42"

# Прочитать все комментарии в PR
gh pr view 5 --repo "$REPO" --json comments -q '.comments'

# Перечитать PR (обновить кеш)
gh pr refresh 5 --repo "$REPO"
```

### Merge & Auto-merge

```bash
# Смержить PR (интерактивно)
gh pr merge 5 --repo "$REPO"

# Смержить с squash
gh pr merge 5 --repo "$REPO" --squash

# Смержить с rebase
gh pr merge 5 --repo "$REPO" --rebase

# Включить auto-merge при получении approval-а
gh pr merge 5 --repo "$REPO" --auto --squash

# Отменить auto-merge
gh pr merge 5 --repo "$REPO" --auto --disable
```

### Bulk операции

```bash
# Добавить метку ко ВСЕМ v0.2 PR-ам
for n in 5 6 7 8 9 10 11 12; do
  gh pr edit $n --repo "$REPO" --add-label "v0.2"
done

# Назначить всем ревьюера
for n in 5 6 7 8 9 10 11 12; do
  gh pr edit $n --repo "$REPO" --add-reviewer "danilivashyna"
done

# Конвертировать все draft в ready
gh pr list --repo "$REPO" --search "is:draft" \
  -q '.[] | .number' | while read n; do
  gh pr ready "$n" --repo "$REPO"
done
```

---

## 🎯 Issue-операции

### Создание

```bash
# Создать issue
gh issue create --repo "$REPO" \
  --title "Add metric X" \
  --body "Description here" \
  --label "v0.2,enhancement" \
  --assignee "alice"

# Создать с из шаблона
gh issue create --repo "$REPO" --template bug

# Создать с телом из файла
gh issue create --repo "$REPO" \
  --title "Feature request" \
  --body-file issue_template.md
```

### Просмотр и управление

```bash
# Список всех открытых issues с меткой v0.2
gh issue list --repo "$REPO" -l v0.2 -s open

# Показать issue с деталями
gh issue view 42 --repo "$REPO"

# Открыть issue в браузере
gh issue view 42 --repo "$REPO" --web

# Закрыть issue
gh issue close 42 --repo "$REPO"

# Переоткрыть issue
gh issue reopen 42 --repo "$REPO"
```

### Метки, назначение, приоритет

```bash
# Добавить метку
gh issue edit 42 --repo "$REPO" --add-label "bug,critical"

# Удалить метку
gh issue edit 42 --repo "$REPO" --remove-label "todo"

# Назначить разработчика
gh issue edit 42 --repo "$REPO" --add-assignee "alice,bob"

# Назначить milestone
gh issue edit 42 --repo "$REPO" --milestone "v0.2.0-beta"

# Добавить в проект
gh issue edit 42 --repo "$REPO" --add-project "Atlas Roadmap"
```

### Комментарии

```bash
# Добавить комментарий
gh issue comment 42 --repo "$REPO" --body "Great idea! Let's do it."

# Прочитать все комментарии
gh issue view 42 --repo "$REPO" --json comments

# Удалить комментарий (можно только свой)
gh issue comment 42 --repo "$REPO" --body "Nevermind, ignore this"
```

### Bulk операции

```bash
# Добавить метку "help wanted" ко ВСЕМ открытым v0.2-issues
for num in $(gh issue list --repo "$REPO" -l v0.2 -s open -q '.[] | .number'); do
  gh issue edit "$num" --repo "$REPO" --add-label "help wanted"
done

# Назначить всем одного разработчика
gh issue list --repo "$REPO" -l v0.2 -s open \
  -q '.[] | .number' | while read num; do
  gh issue edit "$num" --repo "$REPO" --add-assignee "alice"
done

# Закрыть все resolved issues с меткой v0.2
gh issue list --repo "$REPO" -l v0.2,resolved -s open -q '.[] | .number' \
  | while read num; do
  gh issue close "$num" --repo "$REPO"
done
```

---

## 🔄 Workflow: PR + Issue Связь

### Вариант 1: Issue → PR

```bash
# 1. Создать issue
ISSUE_NUM=$(gh issue create --repo "$REPO" \
  --title "Add H-Coherence metric" \
  --body "Implementation in v0.2-06" \
  --label "v0.2,metrics" \
  --json number -q '.number')

echo "Created issue #$ISSUE_NUM"

# 2. Соединить с PR через комментарий
gh pr comment 10 --repo "$REPO" --body "Implements #$ISSUE_NUM"

# 3. Добавить milestone/проект
gh issue edit "$ISSUE_NUM" --repo "$REPO" --milestone "v0.2.0-beta"
```

### Вариант 2: Автоматическое закрытие Issue из PR

В описании PR добавить:

```
Closes #42
Closes #43, #44

Fixes #100
Resolves #200
```

При merge такого PR → Issues автоматически закроются.

---

## 📊 CI/Workflow Операции

```bash
# Показать последние прогоны GitHub Actions
gh run list --repo "$REPO" --limit 10

# Показать статус конкретного прогона
gh run view 18635047091 --repo "$REPO"

# Подождать завершения
gh run watch 18635047091 --repo "$REPO"

# Запустить workflow вручную
gh workflow list --repo "$REPO"
gh workflow run "CI" --repo "$REPO" --ref main

# Посмотреть логи прогона
gh run view 18635047091 --repo "$REPO" --log

# Скачать артефакты
gh run download 18635047091 --repo "$REPO" -D /tmp/artifacts
```

---

## 🎓 Advanced: JSON Queries

GitHub CLI поддерживает мощный JQ фильтр. Примеры:

```bash
# Показать все PR-ы с их авторами
gh pr list --repo "$REPO" -l v0.2 \
  --json number,title,author \
  -q '.[] | "\(.number): \(.title) by \(.author.login)"'

# Группировать по статусу draft
gh pr list --repo "$REPO" -l v0.2 \
  --json number,isDraft,state \
  -q 'group_by(.isDraft) | .[] | {draft: .[0].isDraft, count: length}'

# Найти PR-ы с > 10 comments
gh pr list --repo "$REPO" -l v0.2 \
  --json number,title,comments \
  -q '.[] | select(.comments | length > 10)'

# Экспортировать в CSV
gh pr list --repo "$REPO" -l v0.2 \
  --json number,title,isDraft,state \
  -q '.[] | [.number, .title, .isDraft, .state] | @csv'
```

---

## 🧰 Автоматизация: Алиасы

Создать быстрые команды:

```bash
# Добавить алиас
gh alias set prme 'pr list --assignee @me'
gh alias set issueme 'issue list --assignee @me'

# Использовать
gh prme --repo "$REPO" -l v0.2
gh issueme --repo "$REPO" -l v0.2

# Алиас с параметром
gh alias set prdraft 'pr list --search "is:draft"'
gh prdraft --repo "$REPO" -l v0.2

# Мощный алиас для статуса v0.2
gh alias set v0.2status \
  '!echo "=== v0.2 Status ===" && \
   gh pr list -l v0.2 --json number,isDraft && \
   echo "---" && \
   gh issue list -l v0.2 --json number,state'

gh v0.2status --repo "$REPO"
```

---

## 📚 Наши Скрипты

### 1. `tools/create_prs_v0.2.sh` — Создание PR-ов

```bash
./tools/create_prs_v0.2.sh                # создать draft PRs #5-12
./tools/create_prs_v0.2.sh yourorg/repo   # для другого репо
```

### 2. `tools/create_issues_v0.2.sh` — Создание Issues

```bash
./tools/create_issues_v0.2.sh             # создать 8 issues + линки на PRs
./tools/create_issues_v0.2.sh yourorg/repo
```

### 3. `tools/manage_v0.2.sh` — Управление проектом

```bash
./tools/manage_v0.2.sh status             # показать статус
./tools/manage_v0.2.sh ready              # draft → ready
./tools/manage_v0.2.sh assign alice,bob   # назначить разработчиков
./tools/manage_v0.2.sh review danilivashyna  # запросить review
./tools/manage_v0.2.sh web                # открыть все PR в браузере
./tools/manage_v0.2.sh help               # справка
```

---

## 🐛 Debugging & Troubleshooting

```bash
# Проверить конфиг gh
gh config list

# Проверить токен
gh auth token

# Увидеть, какие команды выполняются (verbose)
gh --verbose pr list --repo "$REPO" -l v0.2

# Проверить permissions
gh api user

# Проверить rate limit
gh api rate_limit
```

---

## 📖 Дополнительные Ресурсы

- **Официальная документация**: https://cli.github.com/manual
- **JQ документация**: https://stedolan.github.io/jq/
- **GitHub API**: https://docs.github.com/en/rest

---

## ✨ Pro Tips

1. **Окружение по умолчанию**: Добавить в `~/.zshrc`:
   ```bash
   export GITHUB_REPO="danilivashyna/Atlas"
   alias gh='gh --repo "$GITHUB_REPO"'
   ```

2. **Batch processing**: Всегда используй `for` циклы для bulk операций:
   ```bash
   for n in $(gh pr list -q '.[] | .number'); do
     gh pr edit "$n" --add-label "reviewed"
   done
   ```

3. **Error handling**: Всегда добавляй `2>/dev/null || true` для non-critical операций:
   ```bash
   gh label create v0.2 2>/dev/null || true  # ignore if exists
   ```

4. **Проверка перед выполнением**: Используй `--dry-run` (где доступен):
   ```bash
   gh pr list --repo "$REPO" --search "is:draft" -q '.'  # preview
   ```

---

**Последнее обновление**: 2025-10-19
**Автор**: GitHub Copilot
**Версия**: v0.2 CLI Workflow
