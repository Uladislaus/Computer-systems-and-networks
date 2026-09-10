@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================
echo   DocFactory — установка
echo ============================================
echo.
echo Папка: %CD%
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ОШИБКА] Python не найден в PATH.
  pause
  exit /b 1
)

echo Python:
python --version
where.exe python
echo.

if not exist "app.py" (
  echo [ОШИБКА] Не найден app.py
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Создаю .venv ...
  python -m venv .venv
  if errorlevel 1 (
    echo [ОШИБКА] Не удалось создать .venv
    pause
    exit /b 1
  )
) else (
  echo .venv уже есть
)

echo Устанавливаю пакеты в .venv ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ОШИБКА] pip install не удался
  pause
  exit /b 1
)

echo.
echo Пишу DocFactory.bat ...
(
  echo @echo off
  echo cd /d "%%~dp0"
  echo ".venv\Scripts\python.exe" app.py
  echo if errorlevel 1 pause
) > "DocFactory.bat"

echo.
echo Проверка:
".venv\Scripts\python.exe" -c "import docx; print('docx OK')"
".venv\Scripts\python.exe" cli.py --engines
echo.

echo ============================================
echo   Готово. Запуск: start.bat
echo ============================================
pause
