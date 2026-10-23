# Agent notes

## Badge Factory (portable)

Переносимая фабрика **со сборкой и генерацией**. Источник правды: `badge-factory/`.

- `scripts/factory.py pipeline` → job → агент зовёт `GenerateImage` → `assemble_badge.py`
- Бэкенды: `cursor` (tool), `openai` (`OPENAI_API_KEY`), `http` (`BADGE_GEN_URL`)
- Freeform: любая картинка через `--freeform`

Копия skill: `.cursor/skills/badge-factory/`. Картинка + «значок» = полный бриф цеха.

## Выход цеха в ЭТОМ репозитории

- Папка: `work/File/badges_print_ready/`
- Zip: `badges.zip` там же
- Каталог уже сделанных сюжетов: `.cursor/skills/badges-print/badge-catalog.json`
- Ветка: `cursor/badges-print-black-bg-f67c`
