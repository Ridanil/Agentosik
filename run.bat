@echo off
@echo off
call venv\Scripts\activate.bat

if not exist ".env" (
    echo [ОШИБКА] Файл .env не найден. Запустите install.bat и заполните .env
    pause
    exit /b 1
)

echo Проверяю, запущен ли Ollama...
curl -s http://localhost:11434 >nul 2>nul
if %errorlevel% neq 0 (
    echo [ПРЕДУПРЕЖДЕНИЕ] Ollama не отвечает на localhost:11434.
    echo Убедитесь, что Ollama запущен, иначе AI-анализ не будет работать.
    echo.
)

echo Запуск Telegram AI Agent...
python main.py

pause
