@echo off
echo ===============================================
echo  Установка Telegram AI Agent
echo ===============================================

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ОШИБКА] Python не найден. Установите Python 3.11+ с python.org
    pause
    exit /b 1
)

echo Создаю виртуальное окружение...
python -m venv venv

echo Активирую окружение и ставлю зависимости...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

if not exist ".env" (
    copy .env.example .env
    echo.
    echo [ВАЖНО] Создан файл .env — заполните его перед запуском:
    echo   TELEGRAM_API_ID, TELEGRAM_API_HASH, BOT_TOKEN
)

echo.
echo ===============================================
echo Установка завершена.
echo Не забудьте:
echo   1. Установить Ollama: https://ollama.com/download
echo   2. Выполнить: ollama pull qwen3:8b
echo   3. Заполнить файл .env
echo   4. Запустить run.bat
echo ===============================================
pause
