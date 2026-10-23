# Badge Factory — переносимая фабрика значков (+ генерация)

Самодостаточный kit: **промпт → генерация → сборка 1371**.
Не привязан к одному репозиторию.

## Установка

```bash
cp -R badge-factory <проект>/.cursor/skills/badge-factory
# или user skills:
# cp -R badge-factory ~/.cursor/skills/badge-factory
```

## Быстрый старт

### Агент Cursor (рекомендуется)
```bash
python scripts/factory.py pipeline \
  --brief "рыжий кот в стиральной машине, мемный значок" \
  --text "СТИРОЧКА ГОТОВА" \
  --rim gold_wide \
  -o out/stirochka.png \
  --backend cursor
```
Агент читает `jobs/last_generate_job.json` → tool `GenerateImage` → `assemble_badge.py`.

### OpenAI ключ (CLI без Cursor tool)
```bash
export OPENAI_API_KEY=sk-...
python scripts/generate_badge.py \
  --brief "..." --text "..." --rim gold_wide \
  -o out/badge.png --backend openai
```

### Только сборка готовой картинки
```bash
python scripts/assemble_badge.py photo.png -o badge.png --rim gold_wide
```

### Любая картинка «как скажу»
```bash
python scripts/generate_badge.py --brief "описание" --freeform \
  -o out/art.png --backend cursor   # или openai / http
```

## Состав

| Путь | Зачем |
|------|--------|
| `SKILL.md` | Бриф для агента + контур генерации |
| `PLAYBOOK.md` | План цеха |
| `recipes/gen_shell.json` | Hard-rules промпта значка |
| `recipes/rim-palettes.json` | Палитры ободков |
| `scripts/prompt_engine.py` | Сборщик промптов |
| `scripts/generate_badge.py` | Генерация (cursor/openai/http) |
| `scripts/assemble_badge.py` | Круг + alpha + rim |
| `scripts/factory.py` | Единый CLI |
| `jobs/` | last_generate_job.json / last_prompt.json |

## Честно про качество

- **Промпт + правила** — уровень нашего диалога (зашиты в factory).
- **Картинку рисует** backend: Cursor `GenerateImage`, OpenAI Images, или твой HTTP.
- Без ключа / без агента CLI **сам не рисует** — отдаёт job для генератора.
