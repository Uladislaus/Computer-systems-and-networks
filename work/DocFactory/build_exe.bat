@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================
echo   Сборка DocFactory.exe (PyInstaller)
echo   Запускать на Windows x64
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

echo.
echo Собираю one-file EXE (окно без консоли)...
pyinstaller --noconfirm DocFactory.spec
if errorlevel 1 (
  echo [ОШИБКА] PyInstaller не собрал EXE
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
echo Дальше (по желанию):
echo   1. Установите Inno Setup: https://jrsoftware.org/isinfo.php
echo   2. Откройте installer\DocFactory.iss и Build
echo   3. Получите installer\Output\DocFactorySetup.exe
echo.
echo Либо просто скопируйте dist\DocFactory.exe на флешку.
echo.
explorer dist
pause
