@echo off
chcp 65001 >nul 2>&1
echo ============================================
echo  KooDynaErrorAnalyzer Windows EXE 빌드
echo ============================================
echo.

cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
    echo 가상환경이 없습니다. install.bat을 먼저 실행하세요.
    pause
    exit /b 1
)

echo [1/2] PyInstaller 설치 중...
venv\Scripts\pip.exe install pyinstaller
echo.

echo [2/2] 빌드 중...
echo.
set PYTHONPATH=%~dp0src
venv\Scripts\pyinstaller.exe --onefile --log-level DEBUG --name koodyna --hidden-import=koodyna --hidden-import=koodyna.parsers --hidden-import=koodyna.parsers.d3hsp --hidden-import=koodyna.parsers.glstat --hidden-import=koodyna.parsers.status --hidden-import=koodyna.parsers.profile --hidden-import=koodyna.parsers.messag --hidden-import=koodyna.analysis --hidden-import=koodyna.analysis.energy --hidden-import=koodyna.analysis.timestep --hidden-import=koodyna.analysis.warnings --hidden-import=koodyna.analysis.contact --hidden-import=koodyna.analysis.performance --hidden-import=koodyna.analysis.diagnostics --hidden-import=koodyna.report --hidden-import=koodyna.report.terminal --hidden-import=koodyna.report.json_report --hidden-import=koodyna.report.html_report --hidden-import=koodyna.knowledge --hidden-import=koodyna.knowledge.warning_db --hidden-import=tkinter --hidden-import=tkinter.filedialog --hidden-import=tkinter.scrolledtext --hidden-import=webbrowser --paths=src src\koodyna\__main__.py
set BUILD_EXIT=%ERRORLEVEL%

echo.
if %BUILD_EXIT% neq 0 (
    echo ============================================
    echo  빌드 실패 (exit code %BUILD_EXIT%)
    echo ============================================
    pause
    exit /b 1
)

if exist dist\koodyna.exe (
    echo ============================================
    echo  빌드 성공: dist\koodyna.exe
    echo ============================================
    echo.
    echo 이 파일만 복사하면 Python 없이 실행 가능합니다.
    echo.
    echo 사용법:
    echo   dist\koodyna.exe [결과폴더경로]
    echo   dist\koodyna.exe D:\결과폴더\ --html report.html
) else (
    echo ============================================
    echo  빌드 실패: dist\koodyna.exe 생성되지 않음
    echo ============================================
)
pause
