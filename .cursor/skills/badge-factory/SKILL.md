---
name: badge-factory
description: >-
  Portable badge + image factory with generation. When the user drops a picture
  and says «значок»/«медалька», OR asks to generate/regenerate a badge or any
  image from a brief — use this kit: prompt_engine → GenerateImage (or OpenAI/
  HTTP backend) → assemble_badge. Works in any repo once installed.
---

# Badge Factory — portable skill (с генерацией)

Читай `PLAYBOOK.md`. Рецепты: `recipes/`. Скрипты: `scripts/`.

## Генерация (обязательный контур)

Когда нужен **новый** или **перегенерированный** кадр:

1. Собери job через CLI (промпт уже с нашими hard-rules):
   ```bash
   python scripts/factory.py pipeline \
     --brief "..." --text "НАДПИСЬ" --rim gold_wide \
     -o out/badge.png --backend cursor
   ```
   Exit code `3` + файл `jobs/last_generate_job.json` = норма: локальной модели нет.

2. **Ты (агент Cursor)** сразу вызываешь tool `GenerateImage` с полями из job:
   - `description` ← `job["description"]` (не сочиняй заново слабый промпт)
   - `aspect_ratio` ← `job["aspect_ratio"]` (обычно `1:1`)
   - `reference_image_paths` ← `job["reference_image_paths"]` если не пусто
   - `filename` ← basename выхода

3. Прогони сборку:
   ```bash
   python scripts/assemble_badge.py GENERATED.png -o out/badge.png --rim gold_wide
   ```
   (rim можно опустить, если металл уже идеален в кадре)

4. QC из PLAYBOOK → отдай файл.

### Любая картинка «как скажу» (не только значок)

```bash
python scripts/generate_badge.py \
  --brief "что нарисовать" --freeform \
  -o out/image.png --backend cursor
```
Потом `GenerateImage` по job; `--freeform` **не** навязывает badge-shell и не assemble.

### Локальные API (без Cursor tool)

```bash
export OPENAI_API_KEY=...
python scripts/generate_badge.py --brief "..." --text "..." --rim gold_wide \
  -o out/badge.png --backend openai

# или свой шлюз:
export BADGE_GEN_URL=https://...
python scripts/generate_badge.py --brief "..." -o out/badge.png --backend http
```

## Неявный бриф (картинка + «значок»)

1. Круглая металлическая медалька под печать.
2. Один объёмный ободок под настроение кадра.
3. `1371×1371` PNG, прозрачность снаружи.
4. Не ужимать арт, не двойной кантик, не плоский белый текст-наклейка.
5. Шире ободок → inset всей композиции, rim снаружи.
6. Реген сюжета → контур генерации выше, не «дорисовать в PIL».

## Сборка без регена

```bash
python scripts/assemble_badge.py INPUT.png -o OUT.png
python scripts/assemble_badge.py INPUT.png -o OUT.png --rim gold_wide --inner 0.875
```

## Ответ

Коротко: brief → backend/tool → файл. Если сработал `cursor`-backend — не останавливайся на job JSON, добей GenerateImage + assemble в том же ходе.
