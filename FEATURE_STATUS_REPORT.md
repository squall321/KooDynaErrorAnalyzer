# KooDynaErrorAnalyzer 종합 기능 보고서

**버전:** 0.1.0
**작성일:** 2026-03-04
**프로젝트:** KooDynaErrorAnalyzer — LS-DYNA 시뮬레이션 자동 진단 도구

---

## 1. 프로젝트 개요

KooDynaErrorAnalyzer는 LS-DYNA MPP 유한요소 시뮬레이션 결과를 자동 파싱·분석하여 수치 불안정, 성능 병목, 실패 원인을 한국어로 진단하는 CLI/GUI 도구입니다.

| 항목 | 내용 |
|------|------|
| 언어 | Python 3.10+ |
| 총 코드 규모 | 8,932줄 / 32개 소스 파일 |
| 출력 형식 | 한국어 터미널(Rich) / HTML / JSON |
| 분석 대상 | d3hsp, glstat, mesXXXX, nodout, bndout, slurm.err 등 |
| 빌드 | PyInstaller 단일 실행파일 (Linux / Windows) |

### 핵심 실행 명령

```bash
# 단일 폴더 분석
PYTHONPATH=src python3 -m koodyna <결과폴더>/

# HTML 리포트 생성
PYTHONPATH=src python3 -m koodyna <결과폴더>/ --html report.html

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
src/koodyna/
├── __main__.py          진입점
├── cli.py               CLI (argparse) — 단일/배치/GUI/스캔 모드
├── analyzer.py          오케스트레이터 (6-Phase 파이프라인)
├── models.py            데이터 모델 (23개 dataclass, 2개 Enum)
├── scanner.py           디렉터리 인덱싱 + 배치 분석
├── parsers/             파일 파서 10개
├── analysis/            분석 엔진 8개
├── knowledge/           에러/경고 지식 베이스
└── report/              리포트 생성기 3개 (터미널/HTML/JSON)
```

| Phase | 역할 |
|-------|------|
| 1. 파일 탐색 | d3hsp, glstat, mes*, nodout, bndout, slurm.err 자동 탐지 |
| 2. 파싱 | 10개 파서로 구조화된 데이터 추출 |
| 3. 리포트 조립 | 파싱 결과 → Report 데이터 모델 통합 |
| 4. 분석 | 에너지·타임스텝·경고·접촉·성능 분석 |
| 5. 진단 | 수치 불안정·실패 원인·Slurm 장애 진단 |
| 6. 후처리 | 중복/과민 Finding 제거 (deduplication) |

---

## 3. 파서 모듈 (10개)

### 3.1 핵심 파서

| 파서 | 추출 정보 |
|------|----------|
| **d3hsp** | 시뮬레이션 헤더·모델 크기·종료 상태·경고/에러 카운트·타임스텝·파트·성능 타이밍·접촉·MPP 프로세서·에너지·질량 속성 |
| **glstat** | 사이클별 에너지 스냅샷 (KE, IE, HG, Sliding, External work, 에너지 비율). NaN/Inf 감지, dt2ms 포맷 지원 |
| **messag (mesXXXX)** | MPP 전 랭크 처리. 경고/에러 카운트, 에러 상세(요소 번호), 초기 관통, 인터페이스 경고 요약, 최소 타임스텝, 서프스 타임스텝, 접촉 dt 상한 |

### 3.2 보조 파서

| 파서 | 추출 정보 |
|------|----------|
| **nodout** | 노드 시계열 (변위·속도). Shooting node / 고주파 진동 감지 |
| **bndout** | 경계 반력·모멘트. 반력 스파이크·진동 감지 |
| **slurm** | Slurm HPC 잡 에러파일. Segfault·MPI 에러·exit code·스택 트레이스 |
| **matsum** | 재료별 에너지·운동량 |
| **profile** | load_profile.csv / cont_profile.csv 부하 프로파일 |
| **status** | status.out — CPU/clock 타이밍 |
| **element_mapper** | 입력 덱 파서 — 요소→파트 매핑 |

---

## 4. 분석 엔진 (8개 모듈)

### 4.1 수치 불안정 분석 (numerical_instability.py) — 커버리지 약 95%

| 진단 항목 | 임계값 | 심각도 |
|-----------|--------|--------|
| Shooting node | \|v\| > 1,000 m/s | CRITICAL |
| 고주파 진동 | ZCR > 10 kHz | WARNING |
| 반력 스파이크 | max/mean > 100 | CRITICAL |
| 반력 진동 | ZCR 기반 | WARNING |
| Hourglass 에너지 지배 | HG/IE > 10% / 50% | WARNING / CRITICAL |
| 운동 에너지 폭발 | 100x 급증 | CRITICAL |
| 접촉 슬라이딩 에너지 과다 | Slide/IE > 30% | WARNING |
| 타임스텝 변동 | 10x 급락 | WARNING |
| NaN 에너지 감지 | glstat NaN/Inf | CRITICAL |
| 음수 에너지 성분 | IE < 0 또는 Slide < 0 | CRITICAL |
| Slurm 장애 진단 | segfault, MPI error, exit code | CRITICAL |

### 4.2 에너지 분석 (energy.py)

| 진단 항목 | 임계값 | 심각도 |
|-----------|--------|--------|
| 에너지 보존 편차 | ratio > 1.05 또는 < 0.95 | WARNING |
| 에너지 보존 심각 위반 | ratio > 1.10 또는 < 0.90 | CRITICAL |
| 에너지 발산 | 총 에너지 5% 이상 성장 | CRITICAL |
| Hourglass 비율 | > 10% / > 50% | WARNING / CRITICAL |
| Sliding 에너지 과다 | > 15% (total 대비) | WARNING |

> 음수 sliding CRITICAL 존재 시 Sliding 경고 자동 억제.

### 4.3 타임스텝 분석 (timestep.py)

- 100개 최소 타임스텝 추출 + 제어 파트 식별
- 타임스텝 붕괴 감지 (dt < 1E-11 + Warning 40509)
- 파트별 타임스텝 지배율 계산

### 4.4 성능 분석 (performance.py)

| 진단 항목 | 임계값 | 심각도 |
|-----------|--------|--------|
| 접촉 계산 과다 | > 40% / > 50% | WARNING / CRITICAL |
| Force gather 과다 | > 5% / > 10% | WARNING / CRITICAL |
| Mass scaling 과다 | > 5% | WARNING |
| MPP 부하 불균형 | > 15% / ≥ 100% | WARNING / CRITICAL |
| MPI 스케일링 예측 | Amdahl 법칙 기반 | INFO |

### 4.5 경고·에러 분석 (warnings.py)

- error_db에서 코드별 심각도·설명 조회
- Warning 50135/50136 tied contact — 인터페이스별 상세 진단
- MPP mes 파일 에러를 d3hsp와 병합 (비-제로 랭크 에러 포함)

### 4.6 접촉 분석 (contact.py)

- 인터페이스별 CPU 비용 분석
- 병목 인터페이스 식별

### 4.7 실패 원인 분석 (failure_analysis.py)

- messag + d3hsp 교차 분석
- 실패 요소→파트 역추적

### 4.8 진단 엔진 (diagnostics.py)

- 접촉 dt 안정성 진단 (min_dt > contact_dt_limit → WARNING, 그 외 → INFO)
- 에너지 비율 폭주 감지
- 파트 타임스텝 지배율 진단
- MPP 도메인 분해 불균형 진단

### 4.9 Finding 중복 제거 (_deduplicate_findings, analyzer.py)

| 억제 대상 | 조건 |
|-----------|------|
| "High sliding interface energy" (WARNING) | "Excessive contact sliding" 또는 "Negative sliding" 이 CRITICAL/WARNING으로 이미 존재 |

---

## 5. 지식 베이스 (error_db.py)

LS-DYNA 에러·경고 코드 데이터베이스 — 한국어 FEM 이론 설명 + 권장사항 포함.

### 5.1 전체 등록 코드 (약 50개)

| 범위 | 카테고리 | 주요 코드 |
|------|----------|----------|
| 10xxx, 11xxx | 요소 에러 | 10100, 10103, 10133, 10246, 10305, 11507, 40100 |
| 20xxx | 재료 | 20018, 20200, 20216, 20248, 20268, 20282, 20546 |
| 21xxx | 곡선/테이블 | 21129, 21302, 21329 |
| 30xxx | 초기화/제약/접촉 | 30001, 30010, 30062, 30099, 30100, 30128, 30131, 30200, 30358, 30455 |
| 40xxx | 런타임 경고 | 40003, 40004, 40455, 40456, 40509, 40532, 40533, 40538, 40552, 40571, 41200, 41314 |
| 50xxx | 타이드 접촉 | 50120, 50135, 50136 |
| 60xxx | 암시적 해석 | 60004, 60100, 60121, 60303, 60315 |
| 70xxx, 80xxx | SPH/입자 | 70021, 70100, 80100 |
| 90xxx | 라이선스 | 90001 |
| Fallback | 미등록 코드 | 범위 기반 자동 심각도 판정 |

### 5.2 고빈도 코드 (실측 발생 건수 기준)

| 코드 | 제목 | 발생 건수 |
|------|------|----------|
| 40533 | Contact velocity too high (slave node) | 250,000+ |
| 40538 | Slave node released from contact | 198,000+ |
| 21129 | Curve extrapolation beyond defined range | 102,000+ |
| 40532 | Slave node penetration velocity limit exceeded | 57,000+ |
| 30099 | Contact pair definition error | 3,654 |
| 21302 | Curve ID reference invalid or undefined | 320 |
| 60303 / 60315 | Implicit solver 수렴 실패 | 55 |
| 11507 | SPG particle stretch parameter error | 5 |

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
  "last_scan": "2026-03-04T12:00:00+00:00",
  "directories": {
    "/data/floor_wave_study/case_01": {
      "study_type": "floor_wave_study",
      "files": ["d3plot", "d3hsp", "glstat", "mes0000"],
      "first_indexed": "2026-03-04T12:00:00+00:00",
      "last_analyzed": null,
      "status": "pending"
    }
  }
}
```

상태값: `pending` / `analyzed` / `failed` / `skipped`

### 6.3 /data 스캔 실측 결과

| 항목 | 값 |
|------|----|
| 탐색 기반 디렉터리 | /data |
| 발견된 d3plot 폴더 | 2,397개 |
| results/ 추가 | 10개 |
| 총 인덱스 항목 | 2,407개 |
| Study 타입 수 | 38개 이상 |

주요 Study 타입 (상위):
floor_wave_study(143), vapor_chamber(93), shield_can_forming(92), pcb_vibration(88), rubber_advanced_study(56), ball_drop_v3~v7 등

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
    case_02.json
    ...
  vapor_chamber/
    ...
```

---

## 7. 리포트 시스템 (3개 형식)

| 형식 | 모듈 | 특징 |
|------|------|------|
| 터미널 | terminal.py | Rich 컬러 출력, 한국어, 14개 섹션 |
| HTML | html_report.py | 독립형 (임베디드 CSS), 브라우저 자동 오픈 |
| JSON | json_report.py | 구조화 데이터, 배치 처리·비교 분석용 |

### 리포트 14개 섹션

1. 시뮬레이션 헤더 (버전·날짜·호스트·정밀도·라이선스)
2. 모델 요약 (노드·요소·파트·접촉·SPC 수)
3. 종료 상태 (정상/에러/미완료·목표시간·사이클·CPU)
4. **진단 결과** (CRITICAL / WARNING / INFO 분류 + 설명 + 권장사항)
5. 경고/에러 요약 (코드별 횟수·심각도·인터페이스)
6. 에너지 분석 (비율 범위·HG/Sliding 비율)
7. 타임스텝 분석 (100개 최소 dt·제어 파트)
8. 성능 타이밍 (컴포넌트별 CPU/Clock 비율)
9. 접촉 타이밍 (인터페이스별 비용)
10. MPP 부하 균형 (프로세서별 CPU 비율)
11. MPI 스케일링 예측 (Amdahl 법칙·코어별 효율)
12. 접촉 서프스 타임스텝 (인터페이스별 dt)
13. 파트 정의 (재료·밀도·탄성계수·ELFORM)
14. Slurm 잡 정보 (exit code·signal·MPI 에러)

---

## 8. 검증 — 10개 테스트 케이스 결과

### 8.1 케이스별 진단 결과

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

### 8.2 감지된 실패 모드 분포

| 실패 모드 | 감지 건수 |
|-----------|----------|
| 에너지 발산 (에너지 비율 > 1.10) | 5 케이스 |
| Negative volume (Error 40509) | 4 케이스 |
| Segmentation fault (Signal 11) | 4 케이스 |
| NaN 검출 (Error 40455/40456) | 2 케이스 |
| MPP 부하 불균형 > 100% (CRITICAL) | 1 케이스 |
| MPI 통신 에러 | 1 케이스 |
| 타임스텝 붕괴 | 1 케이스 |

---

## 9. 빌드 및 배포

### 9.1 빌드 스크립트

| 파일 | 플랫폼 | 용도 |
|------|--------|------|
| build_linux.sh | Linux | PyInstaller 단일 실행파일 빌드 |
| build_windows.bat | Windows (CMD) | PyInstaller 빌드 |
| build_windows.ps1 | Windows (PowerShell) | PyInstaller 빌드 |
| install.sh / install.bat | Linux / Windows | venv + 의존성 설치 |
| koodyna.sh / koodyna.bat | Linux / Windows | 실행 래퍼 |

### 9.2 의존성

- **rich** — 터미널 출력
- **PyInstaller** — 빌드 전용

Python 표준 라이브러리 외 최소 의존성으로 설계.

---

## 10. 개발 이력

### 2026-03-04 (현재 버전)

**배치 분석 시스템**
- `run_batch_analyze()`: pending 항목 자동 분석, JSON + HTML 동시 저장, 50건 단위 인덱스 중간 저장
- CLI: `--analyze`, `--output-dir`, `--limit`, `--no-html`, `--reanalyze` 추가
- reports/ 폴더: 10개 검증 케이스 HTML + JSON 통합

**진단 품질 개선**
- `_deduplicate_findings()`: Excessive contact sliding (WARNING) 있을 때 High sliding interface energy 억제
- MPP 부하 불균형 ≥ 100% → CRITICAL 승격
- 접촉 dt: min_dt > contact_dt_limit일 때만 WARNING (나머지 INFO)
- SLIDING_RATIO_WARN: 5% → 15%

**/data 인덱싱 + 배치 스캔**
- `scanner.py` 신규: 2,397개 폴더 인덱싱 완료 (총 2,407개)
- error_db 28개 코드 신규 등록 (실측 고빈도 기반)
- CLI: `--scan`, `--index`, `--list-index` 추가

### 2026-03-03

**Slurm 파서 + NaN/음수 에너지 진단**
- slurm.py: Slurm HPC 잡 에러 파싱
- detect_nan_in_energy(), detect_negative_energy_components() 추가
- MPP mes 파일 에러 d3hsp 병합 (비-제로 랭크 포함)
- Error 40455/40456 error_db 등록
- 이론적 설명 강화: 전 코드 한국어 FEM 이론 설명

### 이전

- 수치 불안정 진단 95% 커버리지 달성
  - nodout/bndout/glstat/성능/경고패턴/파트레벨 진단
- 진단 메시지 이론적 설명 강화
- Linux/Windows 빌드 스크립트 완성

---

## 11. 현재 상태 및 향후 계획

### 11.1 현재 상태

| 항목 | 상태 |
|------|------|
| 단일 폴더 분석 | 완료 |
| HTML/JSON/터미널 리포트 | 완료 |
| 10개 검증 케이스 | 완료 |
| error_db 50개 코드 | 완료 |
| /data 인덱싱 (2,407개) | 완료 |
| /data 배치 분석 실행 | **진행 중** (백그라운드) |
| Linux/Windows 빌드 | 완료 |
| GUI 모드 (tkinter) | 완료 |

### 11.2 알려진 제한사항

1. 단위 테스트 없음 (데이터 기반 검증만)
2. SMP 모드 미지원 (MPP만)
3. Implicit 해석 심층 진단 미구현 (코드 등록은 완료)
4. 대용량 nodout/bndout 스트리밍 최적화 미완
5. ALE/SPH 진단 제한적

### 11.3 향후 개발 방향

| 우선순위 | 항목 |
|----------|------|
| 높음 | /data 배치 분석 결과 취합·패턴 분석 |
| 높음 | 단위 테스트 (pytest) |
| 중간 | 다중 케이스 비교 리포트 |
| 중간 | Implicit 해석 심층 진단 |
| 중간 | matplotlib 에너지 시계열 그래프 HTML 내장 |
| 낮음 | CI/CD 자동 빌드 |
