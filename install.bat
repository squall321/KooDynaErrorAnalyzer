@echo off
chcp 65001 >nul 2>&1
echo ============================================
echo  KooDynaErrorAnalyzer 설치
echo ============================================
echo.

cd /d "%~dp0"

echo [1/3] 가상환경 생성 중...
python -m venv venv
if errorlevel 1 (
    echo 오류: Python이 설치되어 있지 않거나 PATH에 없습니다.
    echo https://www.python.org/downloads/ 에서 Python 3.10 이상을 설치하세요.
    pause
    exit /b 1
)

echo [2/3] 가상환경 활성화...
call venv\Scripts\activate.bat

echo [3/3] 의존성 설치 중...
pip install -r requirements.txt
echo.

echo ============================================
echo  설치 완료!
echo ============================================
echo.
echo 사용법:
echo   koodyna.bat [결과폴더경로]
echo   koodyna.bat D:\results\ --html report.html
echo   koodyna.bat D:\results\ -o report.json
echo   koodyna.bat D:\results\ --html report.html -o report.json
echo.
pause
