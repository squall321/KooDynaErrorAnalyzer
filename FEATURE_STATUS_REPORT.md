# KooDynaDiag 종합 기능 보고서

**버전:** 0.2.0
**최종 갱신:** 2026-03-08
**프로젝트:** KooDynaDiag — LS-DYNA 시뮬레이션 자동 진단 도구

---

## 1. 프로젝트 개요

KooDynaDiag는 LS-DYNA MPP(Massively Parallel Processing) 유한요소 시뮬레이션 결과를 자동 파싱·분석하여 **수치 불안정**, **성능 병목**, **실패 원인**을 한국어로 진단하는 CLI/GUI 도구입니다.

실무 엔지니어가 수십~수백 MB 규모의 d3hsp, glstat, matsum 등 텍스트 출력을 직접 열어 보는 대신, 몇 초 만에 핵심 문제를 CRITICAL / WARNING / INFO 등급으로 분류하고 LS-DYNA 키워드 수준의 구체적 해결 방안을 제시합니다.

| 항목 | 내용 |
|------|------|
| 언어 | Python 3.10+ |
| 총 코드 규모 | **10,100줄** / **36개** 소스 파일 |
| 데이터 모델 | **27개** dataclass + **2개** Enum |
| 에러/경고 코드 DB | **68개** 코드 (한국어 FEM 이론 설명 포함) |
| 출력 형식 | 한국어 터미널(Rich) / HTML / JSON |
| 분석 대상 파일 | d3hsp, glstat, mesXXXX, matsum, rcforc, nodout, bndout, status.out, load_profile.csv, cont_profile.csv, slurm .err, 입력 덱(.k/.dyn) |
| 빌드 | PyInstaller 단일 실행파일 (Linux / Windows) |
| 검증 규모 | **/data 내 2,495개** 디렉터리 인덱싱, **2,440개** 분석 완료 |

### 핵심 실행 명령

```bash
# 단일 폴더 분석
PYTHONPATH=src python3 -m koodyna <결과폴더>/

# HTML 리포트 생성
PYTHONPATH=src python3 -m koodyna <결과폴더>/ --html report.html

# JSON 리포트 생성
PYTHONPATH=src python3 -m koodyna <결과폴더>/ -o report.json

# /data 전체 인덱싱
PYTHONPATH=src python3 -m koodyna --scan /data

# 인덱싱된 폴더 배치 분석 (JSON + HTML)
PYTHONPATH=src python3 -m koodyna --analyze --output-dir /data/koodyna_reports

# 인덱스 현황 조회
PYTHONPATH=src python3 -m koodyna --list-index
```

---

## 2. 아키텍처 — 6-Phase 분석 파이프라인

```
src/koodyna/                    (9,680 LOC / 34 files)
├── __main__.py                 진입점
├── cli.py                      CLI (argparse) — 단일/배치/GUI/스캔 모드
├── analyzer.py                 오케스트레이터 (6-Phase 파이프라인)
├── models.py                   데이터 모델 (24개 dataclass, 2개 Enum)
├── scanner.py                  디렉터리 인덱싱 + 배치 분석
├── parsers/                    파일 파서 11개
│   ├── d3hsp.py                스트리밍 상태 머신 파서 (146K+ 줄 처리)
│   ├── glstat.py               에너지·타임스텝 시계열
│   ├── messag.py               MPP mes0000~mesNNNN 파서
│   ├── matsum.py               재료별 에너지·운동량 시계열
│   ├── rcforc.py               접촉 반력 시계열 (SURFA/SURFB)
│   ├── nodout.py               노드 변위·속도 시계열
│   ├── bndout.py               경계 반력·모멘트 시계열
│   ├── slurm.py                Slurm HPC 잡 에러 파서
│   ├── element_mapper.py       입력 덱(.k/.dyn) 요소→파트 매핑
│   ├── profile.py              load_profile.csv / cont_profile.csv
│   └── status.py               status.out CPU/clock 타이밍
├── analysis/                   분석 엔진 10개
│   ├── diagnostics.py          종합 진단 (종료 상태·에너지·타임스텝·접촉)
│   ├── energy.py               에너지 보존·발산 분석
│   ├── timestep.py             타임스텝 제어·붕괴 분석
│   ├── warnings.py             경고/에러 코드 분석
│   ├── contact.py              접촉 인터페이스 비용 분석
│   ├── performance.py          성능 병목 분석
│   ├── numerical_instability.py  수치 불안정 감지 (nodout/bndout/glstat 기반)
│   ├── failure_analysis.py     실패 원인 교차 분석
│   ├── matsum_analysis.py      재료별 Hourglass 에너지 분석
│   └── implicit_diagnostics.py Implicit solver 수렴·안정성 진단
├── knowledge/                  에러/경고 지식 베이스
│   └── error_db.py             68개 코드 DB (한국어 FEM 이론 설명)
└── report/                     리포트 생성기 3개 + 차트 엔진
    ├── terminal.py             Rich 터미널 출력
    ├── html_report.py          독립형 HTML (임베디드 CSS + SVG 차트)
    ├── json_report.py          JSON 구조화 데이터
    └── svg_chart.py            순수 SVG 시계열 그래프 생성기
```

### 6-Phase 파이프라인 상세

| Phase | 역할 | 주요 모듈 |
|-------|------|----------|
| 1. 파일 탐색 | d3hsp, glstat, mes*, matsum, nodout, bndout, slurm.err, 입력 덱 자동 탐지 | `analyzer._discover_files()` |
| 2. 파싱 | 10개 파서로 구조화된 데이터 추출 | `parsers/*` |
| 3. 리포트 조립 | 파싱 결과 → Report 데이터 모델 통합 + element_mapper 파트 보완 | `analyzer.run()` |
| 4. 분석 | 에너지·타임스텝·경고·접촉·성능·matsum 분석 | `analysis/*` |
| 5. 진단 | 수치 불안정·실패 원인·Implicit solver·Slurm 장애 진단 | `analysis/diagnostics.py` 등 |
| 6. 후처리 | 중복/과민 Finding 제거 (deduplication) | `analyzer._deduplicate_findings()` |

---

## 3. 파서 모듈 (11개)

### 3.1 핵심 파서

| 파서 | 대상 파일 | 추출 정보 |
|------|----------|----------|
| **d3hsp** | d3hsp | 시뮬레이션 헤더·모델 크기·종료 상태·경고/에러 카운트·키워드 카운트·타임스텝·파트 정의·성능 타이밍·접촉 정의·MPP 프로세서·에너지·질량 속성·도메인 분해 메트릭 |
| **glstat** | glstat | 사이클별 에너지 스냅샷 (KE, IE, HG, Sliding, External work, 에너지 비율). NaN/Inf 감지, dt2ms 포맷 지원, 제어 요소 추적 |
| **messag** | mes0000~mesNNNN | MPP 전 랭크 처리. 경고/에러 카운트, 에러 상세(요소 번호), 초기 관통, 인터페이스 경고 요약, 최소 타임스텝, 서프스 타임스텝, 접촉 dt 상한 |

### 3.2 보조 파서

| 파서 | 대상 파일 | 추출 정보 |
|------|----------|----------|
| **matsum** | matsum | 재료별(material ID) 에너지 시계열: IE, KE, HG, x/y/z momentum, eroded energy. 시간 스텝별 스냅샷 |
| **rcforc** | rcforc | 접촉 인터페이스별 반력·모멘트 시계열 (SURFA/SURFB). 레전드 파싱, single surface 감지 |
| **nodout** | nodout | 노드별 변위·속도 시계열. Shooting node(|v| > 1000 m/s) 및 고주파 진동(ZCR > 10kHz) 감지 |
| **bndout** | bndout | 경계 반력·모멘트 시계열. 반력 스파이크(max/mean > 100) 및 진동 감지 |
| **slurm** | slurm-*.err | Slurm HPC 잡 에러파일. Segfault·MPI 에러·exit code·스택 트레이스·노드명 |
| **element_mapper** | *.k / *.dyn | 입력 덱에서 *ELEMENT_SOLID/SHELL/BEAM 파싱 → 요소 ID→파트 ID 매핑 |
| **profile** | load_profile.csv, cont_profile.csv | 프로세서별 컴포넌트 부하 프로파일 |
| **status** | status.out | CPU/clock per zone-cycle 타이밍, 잔여 시간 예측 |

### 3.3 파서 기술 특징

- **d3hsp 스트리밍 파서**: 7-상태 유한 상태 머신(HEADER→KEYWORD_COUNTS→CONTROL_INFO→PART_DEFS→CONTACTS→BODY→TAIL). 146K+ 줄 파일을 한 줄씩 처리하여 메모리 효율적
- **NaN/Inf 안전 파싱**: glstat에서 `NaN`, `Inf`, `*****` 등 비정상 값을 안전하게 감지·기록
- **MPP 다중 파일 병합**: mes0000~mesNNNN 모든 랭크의 경고/에러를 병합하여 비-제로 랭크 에러도 포착
- **matsum 재료별 추적**: 각 material ID별 독립 시계열 구성, 재료명 자동 추출
- **rcforc 접촉 반력 파싱**: SURFA/SURFB(또는 slave/master) 양면 반력·모멘트 추출, 레전드 섹션에서 인터페이스 타이틀 매핑

---

## 4. 분석 엔진 (10개 모듈)

### 4.1 수치 불안정 분석 (numerical_instability.py) — 커버리지 약 95%

| 진단 항목 | 임계값 | 심각도 | 데이터 소스 |
|-----------|--------|--------|------------|
| Shooting node | \|v\| > 1,000 m/s | CRITICAL | nodout |
| 고주파 진동 | ZCR > 10 kHz | WARNING | nodout |
| 반력 스파이크 | max/mean > 100 | CRITICAL | bndout |
| 반력 진동 | ZCR 기반 | WARNING | bndout |
| Hourglass 에너지 지배 | HG/IE > 10% / 50% | WARNING / CRITICAL | glstat |
| 운동 에너지 폭발 | 100x 급증 | CRITICAL | glstat |
| KE/IE 비율 이상 | > 10 (준정적) | WARNING | glstat |
| 접촉 슬라이딩 에너지 과다 | Slide/IE > 30% | WARNING | glstat |
| 접촉 에너지 스파이크 | 50x 급증 | CRITICAL | glstat |
| 타임스텝 변동 | 10x 급락 | WARNING | glstat |
| NaN 에너지 감지 | glstat NaN/Inf | CRITICAL | glstat |
| 음수 에너지 성분 | IE < 0 또는 Slide < 0 | CRITICAL | glstat |
| Slurm 장애 진단 | segfault, MPI error, exit code | CRITICAL | slurm .err |

### 4.2 에너지 분석 (energy.py)

| 진단 항목 | 임계값 | 심각도 |
|-----------|--------|--------|
| 에너지 보존 편차 | ratio > 1.05 또는 < 0.95 | WARNING |
| 에너지 보존 심각 위반 | ratio > 1.10 또는 < 0.90 | CRITICAL |
| 에너지 발산 | 총 에너지 5% 이상 성장 | CRITICAL |
| Hourglass 비율 | > 10% / > 50% | WARNING / CRITICAL |
| Sliding 에너지 과다 | > 15% (total 대비) | WARNING |

> 음수 sliding CRITICAL 존재 시 Sliding 경고 자동 억제 (deduplication).

### 4.3 타임스텝 분석 (timestep.py)

- 100개 최소 타임스텝 추출 + 제어 파트 식별
- 타임스텝 붕괴 감지 (dt < 1E-11 + Warning 40509)
- 파트별 타임스텝 지배율 계산
- element_mapper 연동: 요소 ID → 파트 ID 보완 (d3hsp에 없는 경우)

### 4.4 성능 분석 (performance.py)

| 진단 항목 | 임계값 | 심각도 |
|-----------|--------|--------|
| 접촉 계산 과다 | > 40% / > 50% | WARNING / CRITICAL |
| Force gather 과다 | > 5% / > 10% | WARNING / CRITICAL |
| Mass scaling 과다 | > 5% | WARNING |
| MPP 부하 불균형 | > 15% / ≥ 100% | WARNING / CRITICAL |
| MPI 스케일링 예측 | Amdahl 법칙 기반 | INFO |

> 부하 균형이 양호한 경우 INFO를 발생시키지 않음 (노이즈 방지).

### 4.5 경고·에러 분석 (warnings.py)

- error_db에서 코드별 심각도·한국어 설명·FEM 이론·권장사항 조회
- Warning 50135/50136 tied contact — 인터페이스별 상세 진단
- MPP mes 파일 에러를 d3hsp와 병합 (비-제로 랭크 에러 포함)
- 미등록 코드: 코드 범위 기반 자동 심각도 판정 (fallback)

### 4.6 접촉 분석 (contact.py)

- 인터페이스별 CPU/Clock 비용 분석
- 병목 인터페이스 식별 (상위 비용 순)
- 접촉 dt 안정성 진단 (min_dt > contact_dt_limit → WARNING)

### 4.7 실패 원인 분석 (failure_analysis.py)

- messag + d3hsp 교차 분석
- 실패 요소 → 파트 역추적
- 에러 요소 번호 → element_mapper로 파트 식별

### 4.8 재료별 Hourglass 분석 (matsum_analysis.py) — **v0.2.0 신규**

matsum 파일에서 각 재료(material)별 Hourglass 에너지 / 내부 에너지 비율을 계산합니다.

| 진단 항목 | 임계값 | 심각도 |
|-----------|--------|--------|
| 재료별 HG/IE 비율 | > 20% | CRITICAL |
| 재료별 HG/IE 비율 | 10~20% | WARNING |

**의미**: 글로벌 HG/IE 비율이 낮아도 특정 재료/파트에 hourglass가 집중될 수 있습니다. matsum 분석은 이러한 **국소적 hourglass 집중**을 감지하여, 어떤 재료의 요소 공식(ELFORM)이나 메시 품질을 개선해야 하는지 구체적으로 안내합니다.

HTML 리포트에 재료별 HG 테이블 섹션이 추가되며, CRITICAL/WARNING 재료는 행 배경색으로 강조됩니다.

### 4.9 Implicit Solver 진단 (implicit_diagnostics.py) — **v0.2.0 신규**

*CONTROL_IMPLICIT_* 키워드 존재 여부로 implicit 해석을 자동 감지하고, 암묵적 시간 적분 특유의 수렴·안정성 문제를 진단합니다.

| 진단 항목 | 에러 코드 | 심각도 | 설명 |
|-----------|----------|--------|------|
| 강성 행렬 특이 | Error 60004 | CRITICAL | K 행렬 역행렬 불가 — 구속 불충분, 좌굴, 재료 softening |
| Line search 실패 | Error 60303 | CRITICAL | 에너지 감소 스텝 크기 미발견 — 급격한 비선형성 |
| Newton-Raphson 발산 | Error 60315 | CRITICAL | 잔차 증가 — 구조적 불안정, 접촉 상태 변화 |
| 수렴 속도 저하 | Warning 60121 | WARNING | 과다 반복 — 하중 스텝 또는 수렴 기준 조정 필요 |
| 에너지 수지 불균형 | (비율 > 2.0) | CRITICAL | Newmark-β/HHT-α 안정 조건 위반 |
| 정상 수행 | — | INFO | Implicit 감지, 수렴 오류 없음 |

**의미**: Implicit 해석은 explicit과 완전히 다른 수렴 메커니즘(Newton-Raphson 반복, 선형 시스템 풀이)을 사용합니다. 이 모듈은 implicit 해석 특유의 실패 모드를 전문적으로 진단하며, 각 에러에 대해 LS-DYNA 키워드 수준의 해결 방안(NSOLVR, LSOLVR, DTMIN, IMFLAG 등)을 제시합니다.

### 4.10 종합 진단 (diagnostics.py)

| 진단 항목 | 설명 |
|-----------|------|
| 종료 상태 — INCOMPLETE 3분류 | 초기화 미시작 / 첫 사이클 미도달 / 실행 중 크래시 (진행률 %) |
| 접촉 dt 안정성 | min_dt > contact_dt_limit → WARNING |
| 에너지 비율 폭주 | ratio > 4.0 → CRITICAL, > 3.0 → WARNING |
| 파트 타임스텝 지배율 | 특정 파트 > 50% → WARNING |
| MPP 도메인 분해 불균형 | max_cost/min_cost 기반 |

#### INCOMPLETE 종료 상태 3분류 (v0.2.0 개선)

기존에는 모든 INCOMPLETE 케이스에 동일한 메시지를 출력했으나, 이제 원인에 따라 3가지로 구분합니다:

1. **초기화 단계 종료** (actual=0, target=0): 시뮬레이션이 시작조차 되지 않음 — 입력 파일 오류, 라이선스 실패 등
2. **첫 사이클 미도달** (actual=0, target>0): 초기화 후 첫 사이클에서 즉시 실패 — 초기 관통, 재료 초기화 오류 등
3. **실행 중 크래시** (actual>0): X% 진행 후 비정상 종료 — segfault, 수치 발산, 음수 볼륨 등

### 4.11 Finding 중복 제거 (_deduplicate_findings, analyzer.py)

| 억제 대상 | 조건 |
|-----------|------|
| "High sliding interface energy" (WARNING) | "Excessive contact sliding" 또는 "Negative sliding" 이 CRITICAL/WARNING으로 이미 존재 |

---

## 5. 지식 베이스 (error_db.py) — 68개 코드

LS-DYNA 에러·경고 코드 데이터베이스. 각 코드에 대해 **한국어 FEM 이론적 배경 설명** + **LS-DYNA 키워드 수준 해결 방안**을 포함합니다.

### 5.1 코드 분류 (68개)

| 범위 | 카테고리 | 등록 코드 수 | 주요 코드 |
|------|----------|-------------|----------|
| 10xxx, 11xxx | 요소 에러 | 7 | 10100, 10103, 10133, 10246, 10305, 11507, 40100 |
| 20xxx | 재료 | 9 | 20018, 20200, 20216, 20248, 20268, 20282, 20385, 20430, 20471, 20546, 20661 |
| 21xxx | 곡선/테이블 | 3 | 21129, 21287, 21302, 21329 |
| 30xxx | 초기화/제약/접촉 | 11 | 30001, 30010, 30060, 30062, 30099, 30100, 30128, 30131, 30200, 30210, 30358, 30364, 30455 |
| 40xxx | 런타임 경고 | 18 | 40003, 40004, 40024, 40455, 40456, 40509, 40515, 40532, 40533, 40534, 40538, 40540, 40552, 40565, 40571, 40864, 41200, 41213, 41234, 41314 |
| 50xxx | 타이드 접촉 | 4 | 50120, 50134, 50135, 50136 |
| 60xxx | 암시적 해석 | 5 | 60004, 60100, 60121, 60303, 60315 |
| 70xxx, 80xxx | SPH/입자 | 3 | 70021, 70100, 80100 |
| 90xxx | 라이선스 | 1 | 90001 |
| Fallback | 미등록 코드 | — | 범위 기반 자동 심각도 판정 |

### 5.2 고빈도 코드 (실측 발생 건수 기준, /data 2,440개 케이스)

| 코드 | 제목 | 누적 발생 건수 |
|------|------|---------------|
| 40533 | Contact velocity too high (slave node) | 250,000+ |
| 40538 | Slave node released from contact (energy conserved) | 198,000+ |
| 21129 | Curve extrapolation beyond defined range | 102,000+ |
| 40532 | Slave node penetration velocity limit exceeded | 57,000+ |
| 50134 | Tied contact slave node not found | 8,651 |
| 30099 | Contact pair definition error | 3,654 |
| 40540 | Contact force limit exceeded | 1,158 |
| 21302 | Curve ID reference invalid or undefined | 320 |
| 40565 | Contact shooting node detected | 180 |
| 30060 | Part section initialization inconsistency | 144 |
| 40864 | Contact surface penetration limit | 91 |
| 30210 | Constrained node initialization | 78 |
| 40534 | Contact slave penetration depth exceeded | 68 |
| 21287 | Curve interpolation warning | 56 |
| 60303 / 60315 | Implicit solver 수렴 실패 | 55 |
| 20661 | Material model convergence issue | 31 |
| 41234 | Contact interface removal threshold | 23 |
| 11507 | SPG particle stretch parameter error | 5 |

### 5.3 코드 설명 구성 (예시: Error 40509)

각 코드에 대해 다음 4개 필드를 제공합니다:

```python
{
    "severity": "CRITICAL",
    "title": "음수 체적 (Negative volume) 발생",
    "description": (
        "Lagrangian 요소의 야코비안(Jacobian) 행렬식 det(J) < 0으로 전환되어 "
        "요소 체적이 음수가 되었습니다. 이는 물리적으로 불가능한 상태이며, "
        "대변형·고속 충돌 시뮬레이션에서 요소가 과도하게 압축/왜곡될 때 발생합니다. "
        "요소 공식(ELFORM)과 재료 모델의 조합, 접촉 관통, "
        "또는 초기 메시 품질 불량이 주요 원인입니다."
    ),
    "recommendation": (
        "1. 요소 공식 변경 — ELFORM=-2(fully integrated solid)로 음수 체적 억제\n"
        "2. Erosion 설정 — *MAT_ADD_EROSION에 MXEPS(최대 유효 변형률) 기준으로 "
        "파괴된 요소를 삭제\n"
        "3. 메시 개선 — 변형 집중 영역의 요소 크기를 작게, 종횡비(aspect ratio)를 "
        "5 이하로 유지"
    ),
}
```

### 5.4 Fallback 메커니즘

DB에 미등록된 코드는 코드 번호 범위에 따라 자동으로 심각도를 판정합니다:

| 범위 | 자동 분류 |
|------|----------|
| 10000~19999 | Element error (CRITICAL) |
| 20000~29999 | Material/Curve (WARNING~CRITICAL) |
| 30000~39999 | Initialization/Constraint (WARNING) |
| 40000~49999 | Runtime warning (WARNING) |
| 50000~59999 | Contact warning (WARNING) |
| 60000~69999 | Implicit solver (CRITICAL) |
| 70000+ | SPH/Particle (WARNING) |

---

## 6. 결과 디렉터리 인덱싱 시스템 (scanner.py)

### 6.1 기능

대규모 결과 디렉터리 트리를 재귀 탐색하여 d3plot이 있는 모든 폴더를 JSON 인덱스로 관리합니다.

| 함수 | 역할 |
|------|------|
| `scan_for_result_dirs(base_dir)` | d3plot 재귀 탐색 |
| `update_index(index, dirs)` | 신규 폴더만 추가 (기존 유지) |
| `mark_analyzed(index, dir, status)` | 분석 상태 기록 |
| `run_batch_scan(base_dir)` | 탐색 + 인덱스 갱신 |
| `run_batch_analyze(index_path, output_dir, html, limit)` | 배치 분석 실행 |
| `print_index(index_path)` | 인덱스 현황 테이블 출력 |

### 6.2 인덱스 파일 구조

기본 위치: `~/.koodyna/index.json`

```json
{
  "version": 1,
  "last_scan": "2026-03-08T12:00:00+00:00",
  "directories": {
    "/data/floor_wave_study/case_01": {
      "study_type": "floor_wave_study",
      "files": ["d3plot", "d3hsp", "glstat", "mes0000"],
      "first_indexed": "2026-03-04T12:00:00+00:00",
      "last_analyzed": "2026-03-08T10:00:00+00:00",
      "status": "analyzed"
    }
  }
}
```

상태값: `pending` / `analyzed` / `failed` / `skipped`

### 6.3 /data 스캔 실측 결과

| 항목 | 값 |
|------|----|
| 탐색 기반 디렉터리 | /data |
| 총 인덱스 항목 | **2,495개** |
| 분석 완료 | **2,440개** (97.8%) |
| 미분석 (pending) | 54개 |
| 건너뜀 (skipped) | 1개 |
| Study 타입 수 | **38개** 이상 |

주요 Study 타입 (상위): floor_wave_study(143), vapor_chamber(93), shield_can_forming(92), pcb_vibration(88), rubber_advanced_study(56), battery_study, warpage_study, ball_drop_v3~v7 등

### 6.4 배치 분석 CLI

```bash
# 스캔 + 분석 동시 실행
koodyna --scan /data --analyze --output-dir /data/koodyna_reports

# 이미 인덱싱된 상태에서 분석만
koodyna --analyze --output-dir /data/koodyna_reports

# 일부만 (100건)
koodyna --analyze --limit 100

# JSON만 생성 (빠름)
koodyna --analyze --no-html

# 재분석 (이미 완료된 항목 포함)
koodyna --analyze --reanalyze
```

리포트 구조:
```
/data/koodyna_reports/
  floor_wave_study/
    case_01.json
    case_01.html
  vapor_chamber/
    case_01.json
    case_01.html
  ...
```

---

## 7. 리포트 시스템 (3개 형식)

| 형식 | 모듈 | 특징 |
|------|------|------|
| 터미널 | terminal.py | Rich 컬러 출력, 한국어, 15개 섹션 |
| HTML | html_report.py | 독립형 (임베디드 CSS + SVG 차트), 브라우저 자동 오픈, matsum 테이블 포함 |
| JSON | json_report.py | 구조화 데이터, 배치 처리·비교 분석용 |
| SVG 차트 | svg_chart.py | 순수 SVG 시계열 그래프 — 외부 의존성 없음 (matplotlib 불필요) |

### 리포트 18개 섹션

1. 시뮬레이션 헤더 (버전·날짜·호스트·정밀도·라이선스)
2. 모델 요약 (노드·요소·파트·접촉·SPC 수)
3. 종료 상태 (정상/에러/미완료·목표시간·사이클·CPU)
4. **진단 결과** (CRITICAL / WARNING / INFO 분류 + 설명 + 권장사항)
5. 경고/에러 요약 (코드별 횟수·심각도·인터페이스)
6. 에너지 분석 (비율 범위·HG/Sliding 비율)
7. **에너지 시계열 그래프** (SVG 4종: 에너지 성분, 외부일/접촉, 에너지 비율, 타임스텝) — **v0.2.1 신규**
8. **재료별 Hourglass 에너지** (matsum 기반, CRITICAL/WARNING 행 강조)
9. **접촉 반력 시계열 그래프** (rcforc SVG: 상위 인터페이스 합력 + 개별 Fx/Fy/Fz) — **v0.2.1 신규**
10. 타임스텝 분석 (100개 최소 dt·제어 파트)
11. 성능 타이밍 (컴포넌트별 CPU/Clock 비율)
12. 접촉 타이밍 (인터페이스별 비용)
13. MPP 부하 균형 (프로세서별 CPU 비율)
14. MPI 스케일링 예측 (Amdahl 법칙·코어별 효율)
15. 접촉 서프스 타임스텝 (인터페이스별 dt)
16. 파트 정의 (재료·밀도·탄성계수·ELFORM)
17. Slurm 잡 정보 (exit code·signal·MPI 에러)
18. 질량 속성 (파트별 질량·관성)

---

## 8. 검증 — 대규모 실증 분석 결과

### 8.1 검증 규모

| 항목 | 값 |
|------|----|
| 총 인덱스 디렉터리 | 2,495개 |
| 분석 완료 | 2,440개 |
| ERROR 종료 케이스 | ~200개 |
| INCOMPLETE 종료 케이스 | 64개 |
| NORMAL 종료 케이스 | ~2,176개 |
| Study 타입 | 38+ 종류 |

### 8.2 진단 커버리지

| 메트릭 | 값 | 의미 |
|--------|-----|------|
| ERROR/INCOMPLETE → CRITICAL | **100%** | 모든 실패 케이스에서 최소 1개 CRITICAL finding 발생 |
| WARNING+ 보유 비율 | **95.8%** | 전체 케이스의 95.8%에서 WARNING 이상 소견 발생 |
| INFO-only 케이스 | 93개 (3.8%) | 대부분 정상 implicit thermal 시뮬레이션 |
| Finding 없음 | 10개 (0.4%) | d3hsp만 있고 glstat/mes 없는 최소 케이스 |

### 8.3 감지된 실패 모드 분포

| 실패 모드 | 감지 건수 |
|-----------|----------|
| 에너지 발산 (에너지 비율 > 1.10) | 다수 |
| Negative volume (Error 40509) | 다수 (가장 빈번한 에러) |
| Segmentation fault (Signal 11) | 다수 |
| NaN 검출 (Error 40455/40456) | 다수 |
| 타임스텝 붕괴 (dt < 1E-11) | 다수 |
| MPP 부하 불균형 ≥ 100% | 소수 |
| MPI 통신 에러 | 소수 |
| Implicit solver 수렴 실패 | 55건 (60303/60315) |
| 재료별 HG 과다 (>20%) | matsum 보유 케이스에서 감지 |

### 8.4 10개 초기 테스트 케이스 (상세)

| 케이스 | 종료 상태 | CRIT | WARN | 주요 실패 원인 |
|--------|-----------|------|------|----------------|
| results_normal | 정상 종료 | 0 | 2 | 기준 케이스 (HG 경고) |
| ball_drop_v2_dp_ex09 | 에러 종료 | 4 | 3 | Negative volume (40509), 에너지 발산 |
| ball_drop_v2_dp_ex16 | 에러 종료 | 6 | 1 | NaN (40455/40456), 음수 Sliding |
| ball_drop_v2_sp_ex06 | 에러 종료 | 4 | 3 | Negative volume, Slurm exit 3 |
| ball_drop_v2_sp_ex09 | 미완료 | 5 | 0 | Segfault (Signal 11), 음수 Sliding |
| ball_drop_v2_sp_ex14 | 미완료 | 5 | 0 | Segfault, NaN 에너지 |
| ball_drop_v2_sp_ex16 | 미완료 | 2 | 1 | Segfault, 에너지 편차 |
| ball_drop_v4_ex12 | 에러 종료 | 4 | 0 | Negative volume, MPP 불균형 129% (CRITICAL) |
| level_study_ex06 | 에러 종료 | 9 | 1 | NaN + 타임스텝 붕괴 + 에너지 폭주 |
| level_study_ex08 | 미완료 | 4 | 1 | KE 폭발, MPI 통신 에러 |

---

## 9. 노이즈 관리

대규모 배치 분석(2,440건)에서 발견된 불필요한 INFO finding을 체계적으로 제거했습니다.

| 제거된 항목 | 발생 빈도 | 이유 |
|------------|----------|------|
| nodout/bndout 부재 안내 (INFO) | 4,455건 (93% 케이스) | 대부분의 케이스에 해당하며 실질적 가치 없음 |
| MPP 부하 균형 양호 (INFO) | 1,332건 (55% 케이스) | 문제 없는 상태를 보고할 필요 없음 |

**원칙**: 분석 도구는 **문제를 감지**하는 것이 목적이며, 문제가 없는 항목을 일일이 보고하는 것은 노이즈입니다. CRITICAL과 WARNING만 어텐션을 요구하는 소견으로 출력합니다.

---

## 10. 빌드 및 배포

### 10.1 빌드 스크립트

| 파일 | 플랫폼 | 용도 |
|------|--------|------|
| build_linux.sh | Linux | PyInstaller 단일 실행파일 빌드 |
| build_windows.bat | Windows (CMD) | PyInstaller 빌드 |
| build_windows.ps1 | Windows (PowerShell) | PyInstaller 빌드 |
| install.sh / install.bat | Linux / Windows | venv + 의존성 설치 |
| koodyna.sh / koodyna.bat | Linux / Windows | 실행 래퍼 |

### 10.2 의존성

- **rich** — 터미널 출력
- **PyInstaller** — 빌드 전용

Python 표준 라이브러리 외 최소 의존성으로 설계.

### 10.3 Hidden Import 목록

빌드 스크립트에 등록된 모든 모듈:
```
koodyna, koodyna.parsers.{d3hsp, glstat, status, profile, messag, nodout, bndout, slurm, matsum, element_mapper, rcforc},
koodyna.analysis.{energy, timestep, warnings, contact, performance, diagnostics, numerical_instability, failure_analysis, matsum_analysis, implicit_diagnostics},
koodyna.report.{terminal, json_report, html_report, svg_chart},
koodyna.knowledge.{warning_db, error_db}, koodyna.scanner
```

---

## 11. 개발 이력

### v0.2.1 (2026-03-08, 현재 버전)

**에너지 시계열 SVG 그래프 (svg_chart.py)**
- 순수 SVG 생성 — matplotlib 등 외부 의존성 없음
- 4종 에너지 차트: 에너지 성분(KE/IE/HG/Total), 외부일·접촉 에너지, 에너지 비율, 타임스텝 이력
- Tokyonight dark 테마, 자동 눈금(nice ticks), 대량 데이터 다운샘플링(>500pts)
- HTML 리포트에 직접 임베딩 (에너지 분석 테이블 바로 뒤)

**rcforc 접촉 반력 파서 + 시계열 그래프**
- `parsers/rcforc.py`: SURFA/SURFB(slave/master) 양면 반력·모멘트 시계열 추출
- RcforcSnapshot, RcforcInterface 데이터 모델
- 레전드 섹션 파싱 (인터페이스 타이틀), single surface 감지
- SVG 차트: 상위 10개 인터페이스 합력 요약 + 상위 5개 Fx/Fy/Fz 상세
- analyzer.py 자동 연결 (rcforc 파일 발견 시)

### v0.2.0 (2026-03-08)

**재료별 Hourglass 분석 (matsum)**
- `matsum_analysis.py`: matsum 파서 데이터에서 재료별 HG/IE 비율 계산
- MaterialHGEntry 모델 추가
- HTML 리포트에 재료별 HG 테이블 섹션 + CRITICAL/WARNING 행 강조

**Implicit Solver 진단**
- `implicit_diagnostics.py`: CONTROL_IMPLICIT_* 키워드 기반 implicit 해석 자동 감지
- Error 60004/60303/60315 (CRITICAL), Warning 60121 (WARNING) 전문 진단
- Implicit 에너지 수지 불균형 감지 (ratio > 2.0)

**element_mapper 연동**
- 입력 덱(.k/.dyn) 파싱으로 요소→파트 매핑 보완
- 타임스텝 제어 요소의 파트 식별률 향상

**INCOMPLETE 종료 상태 세분화**
- 기존 단일 메시지 → 3가지 분류 (초기화 실패 / 첫 사이클 크래시 / 실행 중 크래시)
- 실행 중 크래시 시 진행률(%) 표시

**error_db 대폭 확장**
- 51개 → **68개** 코드 (17개 신규)
- 신규 코드: 50134, 40540, 40565, 30060, 40864, 30210, 40534, 21287, 20661, 41234, 40024, 30364, 41213, 40515, 20471, 20385, 20430
- /data 실측 발생 빈도 기반 우선순위 등록

**노이즈 제거**
- nodout/bndout 부재 INFO 제거 (4,455건 → 0)
- MPP 부하 균형 양호 INFO 제거 (1,332건 → 0)

**대규모 검증**
- /data 2,495개 디렉터리 인덱싱 (2,440개 분석 완료)
- ERROR/INCOMPLETE → CRITICAL 100% 커버리지 확인
- 38+ study 타입 검증

### v0.1.0 (2026-03-04)

**배치 분석 시스템**
- `scanner.py`: /data 인덱싱 + 배치 분석
- CLI: `--scan`, `--analyze`, `--list-index` 등 추가
- error_db 28개 코드 신규 등록 (실측 고빈도 기반)

**진단 품질 개선**
- `_deduplicate_findings()`: Finding 중복 억제
- MPP 부하 불균형 ≥ 100% → CRITICAL 승격
- 접촉 dt 안정성 진단 개선

### v0.0.x (2026-03-03 이전)

- d3hsp/glstat/messag 핵심 파서 완성
- nodout/bndout/slurm 파서 추가
- 수치 불안정 진단 95% 커버리지 달성
- 성능 병목 진단 (Force gather, Mass scaling, Contact, MPP 불균형)
- 경고 패턴 분석 (tied contact 50135/50136)
- Linux/Windows 빌드 스크립트
- Rich 터미널 / HTML / JSON 리포트

---

## 12. 현재 상태 및 향후 계획

### 12.1 현재 상태 요약

| 항목 | 상태 |
|------|------|
| 단일 폴더 분석 | 완료 |
| HTML/JSON/터미널 리포트 (18개 섹션) | 완료 |
| 에너지 시계열 SVG 차트 (4종) | **완료** |
| rcforc 접촉 반력 파싱 + SVG 차트 | **완료** |
| error_db 68개 코드 | 완료 |
| /data 인덱싱 (2,495개) | 완료 |
| /data 배치 분석 (2,440개) | **완료** |
| matsum 재료별 HG 분석 | 완료 |
| Implicit solver 진단 | 완료 |
| element_mapper 파트 보완 | 완료 |
| INCOMPLETE 3분류 진단 | 완료 |
| 노이즈 제거 최적화 | 완료 |
| Linux/Windows 빌드 | 완료 |
| GUI 모드 (tkinter) | 완료 |

### 12.2 진단 커버리지 요약

```
                    ┌─────────────────────────────┐
                    │  KooDynaDiag v0.2.1          │
                    │  진단 커버리지 Dashboard      │
                    ├─────────────────────────────┤
                    │  에러 코드 DB:      68개     │
                    │  파서 모듈:         11개     │
                    │  분석 엔진:         10개     │
                    │  SVG 차트:          8종      │
                    │  진단 항목:         30+개    │
                    │  검증 케이스:     2,440개    │
                    │                             │
                    │  ERROR → CRITICAL:  100%    │
                    │  INCOMPLETE → CRIT: 100%    │
                    │  WARNING+ 비율:    95.8%    │
                    └─────────────────────────────┘
```

### 12.3 알려진 제한사항

1. 단위 테스트 없음 (데이터 기반 대규모 검증으로 대체)
2. SMP 모드 미지원 (MPP만)
3. 대용량 nodout/bndout 스트리밍 최적화 미완
4. ALE/SPH 진단 제한적 (기본 코드 등록은 완료)
5. Thermal-only 해석 심층 진단 미구현

### 12.4 향후 개발 방향

| 우선순위 | 항목 |
|----------|------|
| 높음 | 단위 테스트 (pytest) |
| 높음 | 다중 케이스 비교 리포트 (study 단위 집계) |
| 중간 | Thermal/Coupled 해석 심층 진단 |
| 중간 | d3plot 요소 품질 분석 (KooD3plotReader 연동 시) |
| 낮음 | CI/CD 자동 빌드 |
| 낮음 | SMP 모드 지원 |
