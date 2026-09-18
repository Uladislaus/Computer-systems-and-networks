# Как получить установщик DocFactory

Есть **два уровня** «установщика».

## Вариант 1 — быстрый (уже сейчас, на вашем ПК)

Подходит, если Python уже стоит (у вас 3.12 есть).

1. Скопируйте папку `DocFactory` в `D:\Work\DocFactory`
2. Дважды щёлкните **`INSTALL.bat`**
3. Дождитесь конца → появится `DocFactory.bat` и ярлык на рабочем столе
4. Запуск: **`DocFactory.bat`** или **`start.bat`**

Это и есть простой установщик под вашу машину / флешку с исходниками.

---

## Вариант 2 — классический Setup.exe (без Python у пользователя)

Нужно **один раз** собрать на Windows (ваш ПК или GitHub Actions).

### 2A. Сборка у себя

```cmd
cd /d D:\Work\DocFactory
build_exe.bat
```

Получите: `D:\Work\DocFactory\dist\DocFactory.exe`

Дальше (по желанию) полноценный Setup:

1. Установите [Inno Setup 6](https://jrsoftware.org/isinfo.php)
2. Откройте `installer\DocFactory.iss` → **Build → Compile**
3. Готово: `installer\Output\DocFactorySetup.exe`

`DocFactorySetup.exe` можно класть на флешку и ставить на другие ПК **без Python**.

> Для DOCX→PDF на целевом ПК всё равно желателен LibreOffice (или Word).

### 2B. Сборка через GitHub Actions

В репозитории есть workflow  
`.github/workflows/build-docfactory-windows.yml`.

1. GitHub → Actions → **Build DocFactory Windows installer** → Run workflow  
2. Скачайте артефакты:
   - `DocFactory-exe` → `DocFactory.exe`
   - `DocFactorySetup` → `DocFactorySetup.exe`

---

## Что положить на флешку

| Содержимое | Когда |
|------------|--------|
| Вся папка + `INSTALL.bat` | На ПК с Python |
| Только `DocFactory.exe` | Портативный запуск |
| `DocFactorySetup.exe` | Установка «как программа» в Program Files / AppData |

---

## Важно

- Облачный агент Linux **не может** напрямую выдать рабочий Windows `.exe`; сборка — на Windows или в Actions.
- После первой сборки Setup.exe вы используете его как обычный установщик.
