#!/bin/bash

echo "============================================"
echo " KooDynaErrorAnalyzer Linux Binary 빌드"
echo "============================================"
echo ""

cd "$(dirname "$0")"

if [ ! -f venv/bin/python ]; then
    echo "가상환경이 없습니다. install.sh를 먼저 실행하세요."
    exit 1
fi

echo "[1/2] PyInstaller 설치 중..."
venv/bin/pip install pyinstaller
echo ""

echo "[2/2] 빌드 중..."
echo ""
export PYTHONPATH="$(pwd)/src"
venv/bin/pyinstaller --onefile \
    --log-level DEBUG \
    --name koodyna \
    --hidden-import=koodyna \
    --hidden-import=koodyna.cli \
    --hidden-import=koodyna.analyzer \
    --hidden-import=koodyna.models \
    --hidden-import=koodyna.parsers \
    --hidden-import=koodyna.parsers.d3hsp \
    --hidden-import=koodyna.parsers.glstat \
    --hidden-import=koodyna.parsers.status \
    --hidden-import=koodyna.parsers.profile \
    --hidden-import=koodyna.parsers.messag \
    --hidden-import=koodyna.parsers.nodout \
    --hidden-import=koodyna.parsers.bndout \
    --hidden-import=koodyna.parsers.matsum \
    --hidden-import=koodyna.parsers.element_mapper \
    --hidden-import=koodyna.analysis \
    --hidden-import=koodyna.analysis.energy \
    --hidden-import=koodyna.analysis.timestep \
    --hidden-import=koodyna.analysis.warnings \
    --hidden-import=koodyna.analysis.contact \
    --hidden-import=koodyna.analysis.performance \
    --hidden-import=koodyna.analysis.diagnostics \
    --hidden-import=koodyna.analysis.numerical_instability \
    --hidden-import=koodyna.analysis.failure_analysis \
    --hidden-import=koodyna.report \
    --hidden-import=koodyna.report.terminal \
    --hidden-import=koodyna.report.json_report \
    --hidden-import=koodyna.report.html_report \
    --hidden-import=koodyna.knowledge \
    --hidden-import=koodyna.knowledge.warning_db \
    --hidden-import=koodyna.knowledge.error_db \
    --paths=src \
    src/koodyna/__main__.py

BUILD_EXIT=$?

echo ""
if [ $BUILD_EXIT -ne 0 ]; then
    echo "============================================"
    echo " 빌드 실패 (exit code $BUILD_EXIT)"
    echo "============================================"
    exit 1
fi

if [ -f dist/koodyna ]; then
    echo "============================================"
    echo " 빌드 성공: dist/koodyna"
    echo "============================================"
    echo ""
    echo "이 파일만 복사하면 Python 없이 실행 가능합니다."
    echo ""
    echo "사용법:"
    echo "  ./dist/koodyna [결과폴더경로]"
    echo "  ./dist/koodyna /path/to/results/ --html report.html"
    echo ""
    chmod +x dist/koodyna
    echo "실행 권한 부여 완료 (chmod +x)"
else
    echo "============================================"
    echo " 빌드 실패: dist/koodyna 생성되지 않음"
    echo "============================================"
    exit 1
fi
