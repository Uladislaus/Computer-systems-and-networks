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
  echo Установите Python 3.12 и галочку Add to PATH.
  echo Или откройте cmd и выполните: where.exe python
  echo.
  pause
  exit /b 1
)

echo Python:
python --version
where.exe python
echo.

if not exist "app.py" (
  echo [ОШИБКА] Не найден app.py — вы не в папке DocFactory?
  echo Нужно: D:\Work\DocFactory\INSTALL.bat
  echo.
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

call ".venv\Scripts\activate.bat"
echo Устанавливаю пакеты...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
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
  echo call .venv\Scripts\activate.bat
  echo python app.py
  echo if errorlevel 1 pause
) > "DocFactory.bat"

echo.
echo Проверка движков:
python cli.py --engines
echo.

echo ============================================
echo   Готово. Запуск: start.bat или DocFactory.bat
echo ============================================
echo.
pause

echo Запустить сейчас? Закройте окно = Нет. Или введите Y и Enter:
set /p ANS=Y/N: 
if /I "%ANS%"=="Y" (
  call start.bat
)
