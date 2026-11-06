@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist config.json (
    echo [!] config.json not found, copying from config.example.json
    copy config.example.json config.json
    echo     Edit config.json first.
    pause
    exit /b 1
)
python main.py %*
pause
