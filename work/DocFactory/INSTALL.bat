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

REM Снять блокировку «скачано из интернета» (меньше окон про издателя)
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -LiteralPath '%CD%' -Recurse -ErrorAction SilentlyContinue | Unblock-File" >nul 2>&1

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

echo Создаю ярлык на рабочем столе ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell; $p = Join-Path $env:USERPROFILE 'Desktop\DocFactory.lnk'; $s = $ws.CreateShortcut($p); $s.TargetPath = '%CD%\DocFactory.bat'; $s.WorkingDirectory = '%CD%'; $s.Description = 'DocFactory by rva'; $s.Save()"

echo.
echo Проверка:
".venv\Scripts\python.exe" -c "import docx; print('docx OK')"
".venv\Scripts\python.exe" cli.py --engines
echo.

echo ============================================
echo   Готово. Запуск: start.bat или ярлык DocFactory
echo   Про издателя см. docs\PUBLISHER.md
echo   Для OCR сканов: поставьте Tesseract OCR (rus+eng)
echo ============================================
pause
