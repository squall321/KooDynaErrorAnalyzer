# KooDynaErrorAnalyzer

LS-DYNA 해석 결과를 자동 분석하여 디버깅 리포트를 생성하는 도구.
GUI 모드(더블클릭)와 CLI 모드 모두 지원.

## GUI 모드 (더블클릭 실행)

EXE 파일을 **인자 없이 실행** (더블클릭)하면:
1. 폴더 선택 다이얼로그가 열림
2. LS-DYNA 결과 폴더를 선택
3. 진행 창에서 분석 과정을 실시간 확인
4. 분석 완료 후 브라우저에서 HTML 리포트 자동 오픈
5. HTML 파일은 결과 폴더에 `koodyna_report.html`로 저장됨

## CLI 모드 (터미널/명령 프롬프트)

`dist/koodyna` 파일을 LS-DYNA 결과 폴더가 있는 리눅스 머신에 복사하면 바로 사용 가능.
Python 설치 불필요.

```bash
# 바이너리에 실행 권한 부여 (처음 1회)
chmod +x koodyna

# 기본 실행 (터미널에 한글 리포트 출력)
./koodyna /path/to/results/

# HTML 리포트 생성 (브라우저에서 열 수 있는 파일)
./koodyna /path/to/results/ --html report.html

# JSON 리포트 생성 (후처리/자동화용)
./koodyna /path/to/results/ -o report.json

# HTML + JSON 동시 생성
./koodyna /path/to/results/ --html report.html -o report.json

# 파싱 진행 상황 표시
./koodyna /path/to/results/ -v

# 색상 없이 출력 (로그 파일 저장용)
./koodyna /path/to/results/ --no-color > analysis.txt
```

## 필요한 파일

결과 폴더에 다음 파일들이 있어야 합니다 (최소 d3hsp 또는 mes0000):

| 파일 | 필수 | 파싱 내용 |
|------|------|----------|
| `d3hsp` | O | 모델 정보, 파트, 접촉, 성능, 타임스텝, 경고/오류 |
| `glstat` | | 에너지 수지, 타임스텝 제어 타임라인 |
| `mes0000`~`mesNNNN` | | 인터페이스별 경고 요약, 메모리 사용량 |
| `status.out` | | 진행 상태 예측 |
| `load_profile.csv` | | 프로세서별 부하 분포 |
| `cont_profile.csv` | | 인터페이스별 프로세서 타이밍 |

## 리포트 섹션 설명

### 1. 모델 요약
노드, 요소, 파트, 접촉 수 등 기본 모델 정보.

### 2. 종료 상태
정상/오류/미완료 여부, 사이클 수, CPU/경과 시간.

### 3. 진단 결과
자동 분석으로 발견된 문제점과 권장 조치:
- **심각**: Hourglass 에너지 과다, 에너지 비율 이상 등
- **경고**: 슬라이딩 인터페이스 에너지, 다량의 경고, MPI 통신 오버헤드
- **정보**: 주요 성능 병목, 부하 균형 상태

### 4. 경고/오류 요약
LS-DYNA 경고 코드별 발생 횟수와 관련 인터페이스.

### 5. 접촉 인터페이스 요약
27개(예시) 접촉 인터페이스의 타입, 제목, 경고 수, CPU 시간.
- 인터페이스별 경고 수가 100건 초과시 노란색 강조
- Clock 시간 기준으로 병목 인터페이스 확인 가능

### 6. 에너지 수지
운동/내부/Hourglass/슬라이딩 에너지의 초기~최종값 비교.
- Hourglass/내부에너지 비율이 10% 초과시 경고

### 7. 최소 타임스텝 요소 (상위 20개)
dt가 가장 작은 요소 20개의 **요소 ID**, 파트 번호, dt 값.
- 어떤 요소가 타임스텝을 제한하는지 직접 확인 가능

### 8. 파트별 타임스텝 요약
100 최소 타임스텝 요소들의 파트별 그룹화.

### 9. 타임스텝 제어 타임라인
시뮬레이션 진행 중 타임스텝을 제어하는 요소의 전환 이력.
- 같은 요소가 연속 제어하면 구간으로 합쳐서 표시

### 10. 성능 프로파일링
컴포넌트별 CPU/Clock 시간과 비율 바 차트.

### 11. 부하 프로파일 요약
프로세서별 컴포넌트 부하의 최소/최대/평균/편차.
- 편차 8% 초과시 부하 불균형 경고

### 12. MPI 스케일링 예측
현재 코어 수에서 32/64/128/256코어로 확장 시 예상 성능:
- **효율 50% 미만**: 빨간색 (코어 추가 비효율적)
- **효율 50~70%**: 노란색 (주의)
- 통신 비율이 높으면 모델 대비 코어가 너무 많은 것

### 13. 접촉 프로파일
인터페이스별 프로세서 간 타이밍 분포와 불균형도.

### 14. MPP 부하 균형
각 프로세서의 CPU/평균 비율. 1.0에 가까울수록 균형.

### 15. 파트 정의
모든 파트의 재료 타입, 밀도, 탄성계수, 포아송비, 요소 공식.

## 소스에서 직접 실행

```bash
# Python 3.10+ 필요
pip install rich

# 실행
PYTHONPATH=src python3 -m koodyna /path/to/results/
PYTHONPATH=src python3 -m koodyna /path/to/results/ --html report.html
```

## 빌드 방법

```bash
pip install pyinstaller rich

PYTHONPATH=src pyinstaller --onefile --name koodyna \
  --hidden-import=koodyna \
  --hidden-import=koodyna.parsers \
  --hidden-import=koodyna.parsers.d3hsp \
  --hidden-import=koodyna.parsers.glstat \
  --hidden-import=koodyna.parsers.status \
  --hidden-import=koodyna.parsers.profile \
  --hidden-import=koodyna.parsers.messag \
  --hidden-import=koodyna.analysis \
  --hidden-import=koodyna.analysis.energy \
  --hidden-import=koodyna.analysis.timestep \
  --hidden-import=koodyna.analysis.warnings \
  --hidden-import=koodyna.analysis.contact \
  --hidden-import=koodyna.analysis.performance \
  --hidden-import=koodyna.analysis.diagnostics \
  --hidden-import=koodyna.report \
  --hidden-import=koodyna.report.terminal \
  --hidden-import=koodyna.report.json_report \
  --hidden-import=koodyna.report.html_report \
  --hidden-import=koodyna.knowledge \
  --hidden-import=koodyna.knowledge.warning_db \
  --paths=src \
  src/koodyna/__main__.py

# 결과: dist/koodyna (단일 실행 파일)
```

## 주의사항

- 빌드된 바이너리는 **같은 OS 아키텍처**에서만 실행 가능
  - Linux x86-64에서 빌드 → Linux x86-64에서만 사용 가능
  - Windows에서 사용하려면 Windows에서 별도 빌드 필요
- d3hsp 파일이 매우 클 수 있음 (100K+ 줄) — 스트리밍 파서로 메모리 효율적 처리
- HTML 리포트는 외부 의존성 없이 단일 파일로 생성 (오프라인 열람 가능)
