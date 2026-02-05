@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
    echo 가상환경이 없습니다. install.bat을 먼저 실행하세요.
    pause
    exit /b 1
)

set PYTHONPATH=%~dp0src
venv\Scripts\python.exe -m koodyna %*
