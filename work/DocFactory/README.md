# DocFactory — офлайн генератор и конвертер документов

Лёгкое приложение на **Python + tkinter + python-docx**.  
Интернет для работы не нужен. Рекомендуемый путь на ПК: `D:\Work\DocFactory\`.

## Возможности

### 1) Шаблоны → DOCX

| Категория | Документы |
|-----------|-----------|
| Записки | служебная, докладная, объяснительная |
| Карьера | резюме (CV), характеристика |
| Акты | выполненных работ, приёма-передачи, проверки, списания |
| Повышение квалификации | заявление на ПК, план ПК, отчёт о ПК |
| Наставничество | план, журнал |
| Заявления | отпуск / день |
| Прочее | протокол совещания |

### 2) Конвертация файлов

| Направление | Как работает | Нужно дополнительно |
|-------------|--------------|---------------------|
| **MD → DOCX** | встроено (`python-docx`) | ничего |
| **DOCX → MD** | встроено | ничего |
| **DOCX → PDF** | LibreOffice `soffice` или `docx2pdf` | LibreOffice **или** Word + `pip install docx2pdf` |
| **PDF → DOCX** | `pdf2docx` | есть в `requirements.txt` |
| **MD → PDF** | MD→DOCX→PDF | как для DOCX→PDF |
| **PDF → MD** | PDF→DOCX→MD | `pdf2docx` |

> PDF↔DOCX сохраняет текст, но сложная вёрстка/сканы могут выглядеть иначе, чем оригинал.

## Установка (Windows)

```cmd
cd /d D:\Work\DocFactory
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

Для **DOCX → PDF** поставьте [LibreOffice](https://www.libreoffice.org/) (рекомендуется)  
или используйте установленный Microsoft Word + `pip install docx2pdf`.

## Запуск GUI

```cmd
cd /d D:\Work\DocFactory
.venv\Scripts\activate.bat
python app.py
```

Вкладки:
1. **Шаблоны → DOCX** — заполнить поля и собрать документ.
2. **Конвертация MD / DOCX / PDF** — выбрать файл и режим.

## CLI

```cmd
python cli.py --list
python cli.py --engines
python cli.py --type resume_cv --out output

python cli.py --convert notes.md --to notes.docx
python cli.py --convert plan.docx --to plan.pdf
python cli.py --convert scan.pdf --to scan.docx
```

## Структура

```
DocFactory/
  app.py
  cli.py
  requirements.txt
  docfactory/
    catalog.py
    engine.py
    generators.py
    convert.py      # MD/DOCX/PDF
  output/
```

## Важно

- Шаблоны — для печати; не замена гербовых бланков организации.
- Приложение не ходит в сеть и не содержит ИИ.
- Перед сдачей в кадры сверьте реквизиты и подписи.
