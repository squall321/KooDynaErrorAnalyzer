#!/bin/bash
# 배치 분석 완료 대기 → reports2 HTML 갱신 → ZIP 업데이트 → git commit
set -e
BATCH_PID=244761
LOG=/tmp/koodyna_finalize.log
exec > "$LOG" 2>&1

echo "=== 배치 완료 대기 시작 (PID $BATCH_PID) ==="

# 배치 프로세스 종료 대기
while kill -0 "$BATCH_PID" 2>/dev/null; do
    ANALYZED=$(python3 -c "
import json
from pathlib import Path
idx = json.loads(Path.home().joinpath('.koodyna/index.json').read_text())
n = sum(1 for e in idx['directories'].values() if e.get('status') in ('analyzed','failed','skipped'))
print(n)
" 2>/dev/null || echo "?")
    echo "[$(date '+%H:%M:%S')] 진행 중: $ANALYZED/2407 완료"
    sleep 60
done

echo "=== 배치 완료 감지 ==="

cd /home/koopark/claude/KooDynaErrorAnalyzer
export PYTHONPATH=src

# 최종 인덱스 통계
python3 -c "
import json
from pathlib import Path
idx = json.loads(Path.home().joinpath('.koodyna/index.json').read_text())
dirs = idx['directories']
statuses = {}
for e in dirs.values():
    s = e.get('status', 'pending')
    statuses[s] = statuses.get(s, 0) + 1
print('최종 인덱스 통계:')
for s, n in sorted(statuses.items()):
    print(f'  {s}: {n}')
"

echo "=== make_docx.py 실행 (베이스 DOCX 재생성) ==="
python3 make_docx.py

echo "=== post_batch.py 실행 (reports2 HTML + DOCX 섹션11 추가) ==="
python3 -u post_batch.py

echo "=== ZIP 재생성 ==="
python3 -c "
import zipfile
from pathlib import Path

z_path = Path('KooDynaAnalyzer_demo.zip')
with zipfile.ZipFile(z_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.write('FEATURE_STATUS_REPORT.docx', 'FEATURE_STATUS_REPORT.docx')
    for f in sorted(Path('reports').glob('*.html')):
        zf.write(f, f'reports/{f.name}')
    for f in sorted(Path('reports2').glob('*.html')):
        zf.write(f, f'reports2/{f.name}')
total = len(zf.namelist()) if False else sum(1 for _ in zipfile.ZipFile(z_path).namelist())
print(f'ZIP 생성 완료: {z_path} ({z_path.stat().st_size/1024/1024:.1f} MB, {total}개 파일)')
"

echo "=== git 커밋 ==="
git add -f KooDynaAnalyzer_demo.zip reports2/ FEATURE_STATUS_REPORT.docx
git status --short

ANALYZED=$(python3 -c "
import json
from pathlib import Path
idx = json.loads(Path.home().joinpath('.koodyna/index.json').read_text())
print(sum(1 for e in idx['directories'].values() if e.get('status') == 'analyzed'))
")
HTML_COUNT=$(ls reports2/*.html 2>/dev/null | wc -l)

git commit -m "배치 분석 완료 후 최종 업데이트 (${ANALYZED}개 분석)

- reports2/ HTML 갱신: ${HTML_COUNT}개 (전체 2407개 분석 기반)
- FEATURE_STATUS_REPORT.docx 섹션 11 최종 업데이트
- KooDynaAnalyzer_demo.zip 재생성

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

echo "=== 완료 ==="
