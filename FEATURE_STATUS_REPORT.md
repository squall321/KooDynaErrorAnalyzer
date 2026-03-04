# KooDynaErrorAnalyzer 기능 현황 보고서

**문서 버전:** 1.3
**작성일:** 2026-03-04
**프로젝트:** KooDynaErrorAnalyzer - LS-DYNA 시뮬레이션 진단 도구

---

## 1. 프로젝트 개요

KooDynaErrorAnalyzer는 LS-DYNA 유한요소 시뮬레이션 결과를 자동 분석하여 수치적 문제, 성능 병목, 실패 원인을 진단하는 Python CLI 도구입니다.

| 항목 | 내용 |
|------|------|
| 언어 | Python 3.10+ |
| 총 코드 라인 | ~9,500줄 (src/koodyna/) |
| 소스 파일 수 | 33개 |
| 출력 언어 | 한국어 (터미널, HTML) / 영문 (JSON) |
| 실행 방법 | `PYTHONPATH=src python3 -m koodyna <결과폴더>` |
| 빌드 | PyInstaller 기반 독립 실행파일 (Linux/Windows) |

### 실행 예시

```bash
# 터미널 리포트 (한국어)
PYTHONPATH=src python3 -m koodyna results/

# HTML 리포트
PYTHONPATH=src python3 -m koodyna results/ --html report.html

# JSON 리포트
PYTHONPATH=src python3 -m koodyna results/ -o report.json

# /data 전체 인덱싱
PYTHONPATH=src python3 -m koodyna --scan /data

# 인덱스 목록 조회
PYTHONPATH=src python3 -m koodyna --list-index
```

---

## 2. 아키텍처

```
src/koodyna/
├── __init__.py              # 패키지 초기화
├── __main__.py              # 진입점 (python -m koodyna)
├── cli.py                   # CLI 인터페이스 (argparse)
├── analyzer.py              # 분석 오케스트레이터 (6-phase 파이프라인)
├── models.py                # 데이터 모델 (23개 dataclass, 2개 Enum)
├── scanner.py               # /data 인덱싱 + 배치 스캔 (NEW)
├── parsers/                 # 파서 모듈 (10개)
├── analysis/                # 분석 모듈 (8개)
├── knowledge/               # 지식 베이스 (error_db, warning_db)
└── report/                  # 리포트 생성기 (3개)
```

### 분석 파이프라인 (6-Phase)

| Phase | 이름 | 설명 |
|-------|------|------|
| Phase 1 | 파일 탐색 | d3hsp, glstat, mes*, status.out, load_profile 등 자동 탐지 |
| Phase 2 | 파싱 | 10개 파서를 통한 구조화된 데이터 추출 |
| Phase 3 | 리포트 조립 | 파싱 결과를 Report 데이터 모델에 통합 |
| Phase 4 | 분석 | 에너지, 타임스텝, 경고, 접촉, 성능 분석 |
| Phase 5 | 진단 | 수치 불안정, 실패 원인, Slurm 장애 진단 |
| Phase 6 | 후처리 | 중복/과민 Finding 제거 (_deduplicate_findings) |

---

## 3. 파서 모듈 현황 (10개)

### 3.1 핵심 파서

| 파서 | 파일 | 설명 |
|------|------|------|
| d3hsp | d3hsp.py | 스트리밍 상태머신 파서. 헤더, 모델 크기, 종료 상태, 경고/에러, 타임스텝, 파트 정의, 성능 타이밍, 접촉 타이밍, MPP 프로세서, 에너지, 접촉 정의, 분해 메트릭, 질량 속성 추출 |
| glstat | glstat.py | 글로벌 통계 파서. 에너지 스냅샷 추출 (KE, IE, HG, sliding, external work 등). NaN/Inf 감지, dt2ms 제어 포맷 지원 |
| messag | messag.py | MPP 메시지 파일 파서. 모든 mesXXXX 랭크 처리. 경고/에러 카운트, 에러 상세 메시지(요소 번호), 초기 관통, 인터페이스 경고 요약, 최소 타임스텝, 서프스 타임스텝, 접촉 안정성 dt 상한 |

### 3.2 보조 파서

| 파서 | 파일 | 설명 |
|------|------|------|
| nodout | nodout.py | 노드 시계열 파서. 변위/속도 추출, shooting node 감지 |
| bndout | bndout.py | 경계 반력 파서. 반력/모멘트 추출, 반력 스파이크 감지 |
| matsum | matsum.py | 재료 요약 파서. 재료별 에너지/운동량 추출 |
| profile | profile.py | 부하 프로파일 파서 (load_profile.csv, cont_profile.csv) |
| status | status.py | status.out 파서. CPU/clock 타이밍 |
| slurm | slurm.py | Slurm HPC 잡 에러 파서. segfault, MPI 에러, exit code, 스택 트레이스 |
| element_mapper | element_mapper.py | 입력 덱 파서. 요소→파트 매핑 |

---

## 4. 분석 모듈 현황 (8개)

### 4.1 수치 불안정 분석 (numerical_instability.py)

전체 수치 건전성 검사의 약 95% 커버리지를 달성합니다.

| 진단 항목 | 함수명 | 임계값 | 심각도 |
|-----------|--------|--------|--------|
| Shooting node | detect_shooting_nodes | \|v\| > 1000 m/s | CRITICAL |
| 고주파 진동 | detect_high_freq_oscillation | ZCR > 10 kHz | WARNING |
| 반력 스파이크 | detect_reaction_force_spike | max/mean > 100 | CRITICAL |
| 반력 진동 | detect_reaction_force_oscillation | ZCR 기반 | WARNING |
| Hourglass 지배 | detect_hourglass_dominance | HG/IE > 10%/50% | WARNING/CRITICAL |
| KE 폭발 | detect_kinetic_energy_explosion | 100x 급증 | CRITICAL |
| 접촉 에너지 과다 | detect_contact_energy_anomaly | Slide/IE > 30% | WARNING |
| 타임스텝 변동 | detect_timestep_volatility | 10x 급락/진동 | WARNING/INFO |
| NaN 에너지 감지 | detect_nan_in_energy | NaN in glstat | CRITICAL |
| 음수 에너지 성분 | detect_negative_energy_components | IE < 0 또는 Slide < 0 | CRITICAL |
| Slurm 장애 진단 | diagnose_slurm_failures | segfault, MPI, exit code | CRITICAL |

### 4.2 성능 병목 분석 (performance.py)

| 진단 항목 | 임계값 | 심각도 |
|-----------|--------|--------|
| Force gather 과다 | > 5%/10% | WARNING/CRITICAL |
| Mass scaling 과다 | > 5% | WARNING |
| 접촉 알고리즘 과다 | > 40%/50% | WARNING/CRITICAL |
| MPP 부하 불균형 | > 15%/100% | WARNING/CRITICAL |
| MPI 스케일링 예측 | Amdahl 법칙 기반 | INFO |

> **변경사항**: MPP 부하 불균형 CRITICAL 임계값 신규 추가 (imbalance ≥ 100%)

### 4.3 에너지 분석 (energy.py)

| 진단 항목 | 임계값 | 심각도 |
|-----------|--------|--------|
| 에너지 보존 위반 | ratio > 1.05 또는 < 0.95 | WARNING |
| 에너지 심각 위반 | ratio > 1.10 또는 < 0.90 | CRITICAL |
| Hourglass 비율 | > 10% / > 50% | WARNING/CRITICAL |
| Sliding 에너지 과다 | > 15% (total 대비) | WARNING |

> **변경사항**: SLIDING_RATIO_WARN 5% → 15% (노이즈 감소). 음수 sliding CRITICAL이 있으면 경고 억제.

### 4.4 진단 엔진 (diagnostics.py)

| 진단 항목 | 설명 |
|-----------|------|
| 접촉 dt 상한 | min_dt > contact_dt_limit → WARNING, 그 외 → INFO |
| 에너지 불균형 | 에너지 비율 추세 + 폭주 감지 |
| 경고 패턴 | Warning 50135/50136 tied contact 인터페이스별 분석 |
| 파트 타임스텝 지배 | 특정 파트가 전체 dt를 지배하는지 분석 |
| 분해 불균형 | MPP 도메인 분해 품질 |

> **변경사항**: 접촉 dt 진단 — 실제로 상한을 초과할 때만 WARNING, 일반적 정보는 INFO

### 4.5 기타 분석 모듈

| 모듈 | 설명 |
|------|------|
| warnings.py | 경고/에러 코드 분류 및 심각도 판정 |
| timestep.py | 타임스텝 행동 분석, 제어 파트 식별 |
| contact.py | 접촉 CPU 시간 분석, 병목 인터페이스 식별 |
| failure_analysis.py | 실패 근본 원인 분석, 요소/파트 교차참조 |

### 4.6 Finding 중복 제거 (_deduplicate_findings, analyzer.py)

분석 파이프라인 후처리 단계에서 하위 우선순위 finding을 제거합니다.

| 억제 대상 | 억제 조건 |
|-----------|-----------|
| "High sliding interface energy" (WARNING) | "Negative sliding..." 또는 "Excessive contact sliding..." 가 CRITICAL 또는 WARNING으로 이미 존재 |

---

## 5. 지식 베이스 (error_db.py)

LS-DYNA 에러/경고 코드 데이터베이스 — 한국어 이론 설명 + 구체적 권장사항 포함.

### 5.1 등록 코드 현황

**총 등록 코드: 약 50개** (2026-03-04 기준)

| 카테고리 | 코드 범위 | 등록 코드 |
|----------|-----------|----------|
| 요소 에러 | 10xxx, 11xxx | 10103, 10100, 10133, 10246, 10305, 11507, 40100 |
| 재료 | 20xxx | 20018, 20200, 20216, 20248, 20268, 20282, 20546 |
| 곡선/테이블 | 21xxx | 21129, 21302, 21329 |
| 초기화/제약 | 30xxx | 30001, 30010, 30062, 30099, 30100, 30128, 30131, 30200, 30358, 30455 |
| 런타임 경고 | 40xxx | 40003, 40004, 40100, 40455, 40456, 40509, 40532, 40533, 40538, 40552, 40571, 41200, 41314 |
| 타이드 접촉 | 50xxx | 50120, 50135, 50136 |
| 암시적 해석 | 60xxx | 60004, 60100, 60121, 60303, 60315 |
| SPH/입자 | 70xxx, 80xxx | 70021, 70100, 80100 |
| 라이선스 | 90xxx | 90001 |
| 기타 | Fallback | 범위 기반 자동 심각도 판정 |

### 5.2 2026-03-04 신규 추가 코드 (28개)

**접촉 속도/해제 경고 (40xxx)**
- 40532: Slave node penetration velocity limit exceeded
- 40533: Contact velocity too high (slave node) ← 250K건 발생
- 40538: Slave node released from contact ← 198K건 발생
- 40552: Contact penetration depth limit reached
- 40571: Initial penetration corrected at contact interface
- 41314: Contact slave node velocity exceeds removal threshold

**곡선/테이블 경고 (21xxx)**
- 21129: Curve extrapolation beyond defined range ← 102K건 발생
- 21329: Curve discretization error

**재료 경고 (20xxx)**
- 20268: Material parameter out of recommended range
- 20282: Material density too low or too high
- 20546: Material model convergence warning

**초기화 경고 (30xxx)**
- 30062: Part/section initialization inconsistency
- 30128: ALE mesh initialization warning
- 30131: Constrained node initialization warning
- 30455: Contact segment not found during initialization

**암시적 경고 (60xxx)**
- 60121: Implicit solver convergence slow

**접촉/인터페이스 에러**
- 30099: Contact pair definition error ← 3,654건 발생

**곡선 에러**
- 21302: Curve ID reference invalid or undefined ← 320건 발생

**재료 에러**
- 20018: Material model initialization failed
- 20216: Material parameter physically invalid

**요소 에러**
- 10133: Solid element connectivity error
- 10246: Solid element excessive distortion
- 10305: Solid element zero-volume detected
- 11507: SPG particle stretch parameter error ← 5건 발생

**암시적 해석 에러**
- 60004: Implicit solver stiffness matrix singular
- 60303: Implicit solver line search failure ← 55건 발생
- 60315: Implicit solver diverged (Newton-Raphson) ← 55건 발생

**SPH 에러**
- 70021: SPH particle interaction error

---

## 6. 결과 디렉터리 인덱싱 (scanner.py)

### 6.1 기능 개요

`/data`와 같은 대규모 결과 디렉터리 트리를 재귀 탐색하여 d3plot 파일이 있는 모든 폴더를 인덱스 JSON에 등록하고 관리합니다.

### 6.2 주요 함수

| 함수 | 설명 |
|------|------|
| `scan_for_result_dirs(base_dir)` | d3plot 파일이 있는 모든 서브디렉터리 반환 |
| `load_index(index_path)` | 기존 인덱스 JSON 로드 |
| `save_index(index, index_path)` | 인덱스 JSON 저장 |
| `update_index(index, dirs)` | 새 디렉터리만 추가 (기존 항목 유지) |
| `mark_analyzed(index, dir_path, status)` | 분석 완료/실패 상태 기록 |
| `run_batch_scan(base_dir, index_path)` | 탐색 + 인덱스 갱신 실행 |
| `print_index(index_path)` | 인덱스 내용 테이블 출력 |

### 6.3 인덱스 파일 형식

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

### 6.4 /data 스캔 결과

| 항목 | 수치 |
|------|------|
| 탐색 디렉터리 | /data |
| 발견된 d3plot 폴더 | 2,397개 |
| results/ 추가 폴더 | 10개 |
| 총 인덱스 항목 | 2,407개 |
| 대표 study 타입 수 | 38개 이상 |

주요 study 타입: floor_wave_study (143), vapor_chamber (93), shield_can_forming (92), pcb_vibration (88), rubber_advanced_study (56), ball_drop v3-v7 등

### 6.5 CLI 사용법

```bash
# /data 전체 스캔 + 인덱스 갱신
koodyna --scan /data

# 커스텀 인덱스 파일 지정
koodyna --scan /data --index /home/user/my_index.json

# 인덱스 내용 조회 (study_type, status, last_analyzed 포함)
koodyna --list-index

# 커스텀 인덱스 조회
koodyna --list-index --index /home/user/my_index.json
```

---

## 7. 리포트 모듈 현황 (3개)

| 모듈 | 형식 | 설명 |
|------|------|------|
| terminal.py | 터미널 | Rich 라이브러리 기반 컬러 터미널 출력 |
| html_report.py | HTML | 독립형 HTML 리포트, 임베디드 CSS |
| json_report.py | JSON | 구조화된 JSON 출력 |

### 리포트 섹션 구성 (14개)

1. 시뮬레이션 헤더 — 버전, 날짜, 호스트, 정밀도, 라이선스
2. 모델 요약 — 노드, 요소, 파트, 접촉, SPC 수
3. 종료 상태 — 정상/에러/미완료, 목표/도달 시간, 사이클, CPU
4. 진단 결과 — 심각/경고/정보 분류, 설명 및 권장사항
5. 경고/에러 요약 — 코드별 횟수, 심각도, 인터페이스
6. 에너지 분석 — 에너지 비율 범위, HG/Sliding 비율
7. 타임스텝 분석 — 100 최소 타임스텝, 제어 파트
8. 성능 타이밍 — 컴포넌트별 CPU/Clock 비율
9. 접촉 타이밍 — 인터페이스별 비용
10. MPP 부하 균형 — 프로세서별 CPU 비율
11. MPI 스케일링 예측 — 코어 수별 효율/속도향상 예측
12. 접촉 서프스 타임스텝 — 인터페이스별 서프스 dt
13. 파트 정의 — 재료 타입, 밀도, 탄성계수, ELFORM
14. Slurm 잡 정보 — exit code, signal, MPI 에러

---

## 8. 빌드 및 배포

| 파일 | 플랫폼 | 용도 |
|------|--------|------|
| build_linux.sh | Linux | PyInstaller 빌드 |
| build_windows.ps1 | Windows | PyInstaller 빌드 (PowerShell) |
| build_windows.bat | Windows | PyInstaller 빌드 (CMD) |
| install.sh | Linux | venv 생성 + 의존성 설치 |
| install.bat | Windows | venv 생성 + 의존성 설치 |
| koodyna.sh | Linux | 실행 래퍼 |
| koodyna.bat | Windows | 실행 래퍼 |

---

## 9. 테스트 검증 결과 (2026-03-04 기준)

### 9.1 테스트 폴더별 진단 결과

| # | 폴더명 | 종료 상태 | CRIT | WARN | INFO | 주요 실패 원인 |
|---|--------|-----------|------|------|------|----------------|
| 1 | results/ (기본) | 정상 종료 | 0 | 2 | 7 | 정상 완료 (HG 에너지 경고) |
| 2 | ball_drop_v2_dp_ex09 | 에러 종료 | 4 | 3 | 5 | Negative volume (40509), 에너지 발산 |
| 3 | ball_drop_v2_dp_ex16 | 에러 종료 | 6 | 1 | 7 | NaN 감지 (40455/40456), 에너지 발산 |
| 4 | ball_drop_v2_sp_ex06 | 에러 종료 | 4 | 3 | 4 | Negative volume, 음수 sliding |
| 5 | ball_drop_v2_sp_ex09 | 미완료 | 5 | 0 | 2 | Segfault (Signal 11), 음수 sliding |
| 6 | ball_drop_v2_sp_ex14 | 미완료 | 5 | 0 | 2 | Segfault, NaN 에너지 |
| 7 | ball_drop_v2_sp_ex16 | 미완료 | 2 | 1 | 2 | Segfault, 에너지 편차 |
| 8 | ball_drop_v4_ex12 | 에러 종료 | 4 | 0 | 5 | Negative volume, MPP 불균형 (129%) |
| 9 | level_study_ex06 | 에러 종료 | 9 | 1 | 2 | NaN, 타임스텝 붕괴, 에너지 폭주 |
| 10 | level_study_ex08 | 미완료 | 4 | 1 | 1 | KE 폭발, MPI 에러 |

### 9.2 총계

- 분석 대상 폴더: 10개
- 정상 종료: 1 / 에러 종료: 5 / 미완료: 4
- 총 진단 건수: 43 CRITICAL, 12 WARNING, 37 INFO = 92건

### 9.3 감지된 실패 모드 분포

| 실패 모드 | 발생 폴더 수 |
|-----------|--------------|
| Negative volume (Error 40509) | 4 |
| 에너지 발산 | 5 |
| Segmentation fault (Signal 11) | 4 |
| NaN 검출 (Error 40455/40456) | 2 |
| 에너지 보존 심각 위반 | 4 |
| MPI 통신 에러 | 1 |
| MPP 부하 불균형 CRITICAL (>100%) | 1 |

---

## 10. 주요 업데이트 이력

### 2026-03-04: 진단 품질 개선 (v1.3)

**Finding 중복/과민 제거**
- `_deduplicate_findings()`: "High sliding interface energy" (WARNING)를 더 구체적인 sliding 진단이 있을 때 억제 (CRITICAL→WARNING 모두 적용)
- `energy.py`: SLIDING_RATIO_WARN 5%→15% 상향, 음수 sliding CRITICAL 존재 시 경고 억제
- `diagnostics.py`: 접촉 dt 진단 — min_dt > contact_dt_limit일 때만 WARNING (나머지 INFO)

**MPP 불균형 임계값 개선**
- `performance.py`: MPP 부하 불균형 ≥ 100% → CRITICAL (기존: 모두 WARNING)

### 2026-03-04: /data 인덱싱 시스템 + 배치 스캔 (v1.2)

- `scanner.py` 신규 추가: /data 재귀 탐색, JSON 인덱스 관리, 배치 스캔
- CLI `--scan`, `--index`, `--list-index` 옵션 추가
- error_db 28개 코드 신규 등록 (40533, 40538, 21129, 30099, 21302 등 고빈도 포함)
- /data 스캔: 2,397개 폴더 발견, 총 2,407개 인덱싱
- 9개 테스트 케이스 배치 분석 → reports/ 저장

### 2026-03-03: Slurm 파서 + NaN/음수 에너지 감지 (v1.1)

- `slurm.py`: Slurm HPC 잡 에러 파싱 (segfault, MPI, exit code)
- `detect_nan_in_energy()`: glstat NaN/Inf 감지
- `detect_negative_energy_components()`: 음수 IE/sliding 감지
- MPP mes 파일 에러 병합: 비-제로 랭크 에러 d3hsp과 통합
- error_db: Error 40455/40456 등록

### 이전: 수치 불안정 진단 95% 커버리지

- nodout/bndout/glstat/성능/경고패턴/파트레벨 진단 완성
- 이론적 설명 강화: 모든 코드에 FEM 이론 배경 추가

---

## 11. 알려진 제한사항

1. 단위 테스트 없음 (데이터 기반 검증만)
2. SMP 모드 미지원 (MPP만)
3. Implicit 해석 진단 제한 (60xxx 코드 등록됨, 심층 분석 미구현)
4. 대용량 nodout/bndout 스트리밍 최적화 미완
5. ALE/SPH 진단 제한

---

## 12. 향후 개발 방향

| 우선순위 | 항목 | 설명 |
|----------|------|------|
| 높음 | /data 배치 분석 실행 | 인덱싱된 2,407개 폴더에 대한 배치 분석 및 결과 취합 |
| 높음 | 단위 테스트 | pytest 기반 파서/분석 단위 테스트 |
| 중간 | Implicit 해석 심층 진단 | 수렴 이력, 반복 횟수 진단 |
| 중간 | 비교 분석 | 다중 폴더 간 비교 리포트 |
| 중간 | 시각화 강화 | matplotlib 그래프 HTML 내장 |
| 낮음 | CI/CD | GitHub Actions 자동 빌드/테스트 |
