@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Сначала выполните INSTALL.bat
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
python app.py
