# DocFactory — офлайн генератор и конвертер документов

Лёгкое приложение на **Python + tkinter + python-docx**.  
Интернет для работы не нужен. Рекомендуемый путь: `D:\Work\DocFactory\`.

## Установка (выберите один способ)

### А. Простой установщик (рекомендуется сначала)

1. Скопируйте папку `DocFactory` в `D:\Work\DocFactory`
2. Запустите **`INSTALL.bat`**
3. Запускайте через **`DocFactory.bat`** / **`start.bat`**

Нужен уже установленный Python 3.12.

### Б. Setup.exe / один EXE без Python

См. подробности: [`installer/README_INSTALLER.md`](installer/README_INSTALLER.md)

Кратко на своём ПК:

```cmd
cd /d D:\Work\DocFactory
build_exe.bat
```

→ `dist\DocFactory.exe`  
Далее Inno Setup: `installer\DocFactory.iss` → `DocFactorySetup.exe`

Или скачайте готовый артефакт из GitHub Actions (**Build DocFactory Windows installer**).

---

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
| **MD → DOCX** | встроено | — |
| **DOCX → MD** | встроено | — |
| **DOCX → PDF** | LibreOffice / docx2pdf | LibreOffice или Word |
| **PDF → DOCX** | pdf2docx | в requirements |
| **MD → PDF** / **PDF → MD** | цепочки | как выше |

## Ручная установка (без INSTALL.bat)

```cmd
cd /d D:\Work\DocFactory
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python app.py
```

## CLI

```cmd
python cli.py --list
python cli.py --engines
python cli.py --type resume_cv --out output
python cli.py --convert notes.md --to notes.docx
```

## Структура

```
DocFactory/
  INSTALL.bat / start.bat / build_exe.bat
  app.py / cli.py
  DocFactory.spec
  installer/DocFactory.iss
  docfactory/
  output/
```

## Важно

- Шаблоны для печати, не гербовые бланки организации.
- Приложение офлайн, без встроенного ИИ.
- Для PDF желателен LibreOffice.
