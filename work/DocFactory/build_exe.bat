@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================
echo   Сборка DocFactory.exe
echo ============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ОШИБКА] Python не найден
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt
if errorlevel 1 (
  echo [ОШИБКА] зависимости
  pause
  exit /b 1
)

echo Собираю EXE...
pyinstaller --noconfirm DocFactory.spec
if errorlevel 1 (
  echo [ОШИБКА] PyInstaller
  pause
  exit /b 1
)

if not exist "dist\DocFactory.exe" (
  echo [ОШИБКА] dist\DocFactory.exe не найден
  pause
  exit /b 1
)

echo.
echo Готово: dist\DocFactory.exe
echo.
explorer dist
pause
