#!/bin/bash

echo "============================================"
echo " KooDynaErrorAnalyzer 설치"
echo "============================================"
echo ""

cd "$(dirname "$0")"

echo "[1/4] 시스템 패키지 확인 중..."
# Check if tkinter is available (optional, for GUI mode)
python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "주의: tkinter가 설치되어 있지 않습니다 (GUI 모드 사용 불가)."
    echo "GUI 모드를 사용하려면 다음 명령으로 설치하세요:"
    echo "  Ubuntu/Debian: sudo apt install python3-tk"
    echo "  RHEL/CentOS:   sudo yum install python3-tkinter"
    echo ""
    echo "CLI 모드는 tkinter 없이도 정상 작동합니다."
    echo ""
fi

echo "[2/4] 가상환경 생성 중..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "오류: Python3가 설치되어 있지 않거나 venv 모듈이 없습니다."
    echo "Ubuntu/Debian: sudo apt install python3-venv"
    echo "RHEL/CentOS: sudo yum install python3-venv"
    exit 1
fi

echo "[3/4] 가상환경 활성화..."
source venv/bin/activate

echo "[4/4] 의존성 설치 중..."
pip install -r requirements.txt
echo ""

echo "============================================"
echo " 설치 완료!"
echo "============================================"
echo ""
echo "사용법:"
echo "  ./koodyna.sh [결과폴더경로]"
echo "  ./koodyna.sh /path/to/results/ --html report.html"
echo "  ./koodyna.sh /path/to/results/ -o report.json"
echo "  ./koodyna.sh /path/to/results/ --html report.html -o report.json"
echo ""
echo "인자 없이 실행 시 GUI 모드로 실행됩니다 (tkinter 필요):"
echo "  ./koodyna.sh"
echo ""
