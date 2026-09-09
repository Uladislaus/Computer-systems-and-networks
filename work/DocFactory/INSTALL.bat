@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================
echo   DocFactory — установка (Python + venv)
echo ============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ОШИБКА] Python не найден в PATH.
  echo Установите Python 3.12 с python.org и галочку Add to PATH,
  echo либо укажите полный путь к python.exe ниже в этом bat.
  pause
  exit /b 1
)

python --version
echo.

if not exist ".venv\Scripts\python.exe" (
  echo Создаю виртуальное окружение .venv ...
  python -m venv .venv
  if errorlevel 1 (
    echo [ОШИБКА] Не удалось создать .venv
    pause
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ОШИБКА] Не удалось установить зависимости
  pause
  exit /b 1
)

echo.
echo Создаю ярлыки запуска...
(
  echo @echo off
  echo cd /d "%%~dp0"
  echo call .venv\Scripts\activate.bat
  echo python app.py
) > "DocFactory.bat"

set "DESKTOP=%USERPROFILE%\Desktop"
if exist "%DESKTOP%" (
  (
    echo @echo off
    echo cd /d "%CD%"
    echo call .venv\Scripts\activate.bat
    echo python app.py
  ) > "%DESKTOP%\DocFactory.bat"
  echo Ярлык: %DESKTOP%\DocFactory.bat
)

echo.
echo ============================================
echo   Установка завершена.
echo   Запуск: DocFactory.bat  или  start.bat
echo ============================================
echo.
choice /C YN /M "Запустить DocFactory сейчас"
if errorlevel 2 goto :eof
if errorlevel 1 call start.bat
