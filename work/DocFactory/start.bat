@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Сначала запустите INSTALL.bat из этой же папки.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
python app.py
if errorlevel 1 (
  echo.
  echo Приложение завершилось с ошибкой.
  pause
)
