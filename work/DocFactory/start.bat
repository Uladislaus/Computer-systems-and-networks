@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Сначала запустите INSTALL.bat из этой же папки.
  pause
  exit /b 1
)
echo Запуск DocFactory через .venv ...
echo Если окно не видно — Alt+Tab / панель задач.
".venv\Scripts\python.exe" app.py
if errorlevel 1 (
  echo.
  echo Приложение завершилось с ошибкой.
  echo Если написано No module named docx — снова запустите INSTALL.bat
  pause
)
