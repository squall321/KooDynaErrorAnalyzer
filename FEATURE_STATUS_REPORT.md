# KooDynaErrorAnalyzer 기능 현황 보고서

**문서 버전:** 1.0  
**작성일:** 2026-03-03  
**프로젝트:** KooDynaErrorAnalyzer - LS-DYNA 시뮬레이션 진단 도구

---

## 1. 프로젝트 개요

KooDynaErrorAnalyzer는 LS-DYNA 유한요소 시뮬레이션 결과를 자동 분석하여 수치적 문제, 성능 병목, 실패 원인을 진단하는 Python CLI 도구입니다.

| 항목 | 내용 |
|------|------|
| 언어 | Python 3.10+ |
| 총 코드 라인 | 7,742줄 (src/koodyna/) |
| 소스 파일 수 | 32개 |
| 출력 언어 | 한국어 (터미널, HTML) / 영문 (JSON) |
| 실행 방법 | `PYTHONPATH=src python3 -m koodyna <결과폴더>` |
| 빌드 | PyInstaller 기반 독립 실행파일 (Linux/Windows) |

### 실행 예시

```bash
# 터미널 리포트 (한국어)
PYTHONPATH=src python3 -m koodyna results/

# HTML 리포트 (브라우저 자동 오픈)
PYTHONPATH=src python3 -m koodyna results/ --html report.html

# JSON 리포트
PYTHONPATH=src python3 -m koodyna results/ -o report.json
```

---

## 2. 아키텍처

```
src/koodyna/
├── __init__.py              # 패키지 초기화
├── __main__.py              # 진입점 (python -m koodyna)
├── cli.py (273줄)           # CLI 인터페이스 (argparse)
├── analyzer.py (349줄)      # 분석 오케스트레이터 (5-phase 파이프라인)
├── models.py (321줄)        # 데이터 모델 (23개 dataclass, 2개 Enum)
├── parsers/                 # 파서 모듈 (10개, 2,438줄)
├── analysis/                # 분석 모듈 (8개, 2,633줄)
├── knowledge/               # 지식 베이스 (625줄)
└── report/                  # 리포트 생성기 (3개, 1,346줄)
```

### 분석 파이프라인 (5-Phase)

| Phase | 이름 | 설명 |
|-------|------|------|
| Phase 1 | 파일 탐색 | d3hsp, glstat, mes*, status.out, load_profile 등 자동 탐지 |
| Phase 2 | 파싱 | 10개 파서를 통한 구조화된 데이터 추출 |
| Phase 3 | 리포트 조립 | 파싱 결과를 Report 데이터 모델에 통합 |
| Phase 4 | 분석 | 에너지, 타임스텝, 경고, 접촉, 성능 분석 |
| Phase 5 | 진단 | 수치 불안정, 실패 원인, Slurm 장애 진단 |

---

## 3. 파서 모듈 현황 (10개)

### 3.1 핵심 파서

| 파서 | 파일 | 라인 | 설명 |
|------|------|------|------|
| d3hsp | d3hsp.py | 908 | 스트리밍 상태머신 파서. 헤더, 모델 크기, 종료 상태, 경고/에러, 타임스텝, 파트 정의, 성능 타이밍, 접촉 타이밍, MPP 프로세서, 에너지, 접촉 정의, 분해 메트릭, 질량 속성 추출 |
| glstat | glstat.py | 149 | 글로벌 통계 파서. 에너지 스냅샷 추출 (KE, IE, HG, sliding, external work 등). NaN/Inf 감지, dt2ms 제어 포맷 지원 |
| messag | messag.py | 214 | MPP 메시지 파일 파서. 모든 mesXXXX 랭크 처리. 경고/에러 카운트, 에러 상세 메시지(요소 번호), 초기 관통, 인터페이스 경고 요약, 최소 타임스텝, 서프스 타임스텝, 접촉 안정성 dt 상한 |

### 3.2 보조 파서

| 파서 | 파일 | 라인 | 설명 |
|------|------|------|------|
| nodout | nodout.py | 160 | 노드 시계열 파서. 변위/속도 추출, shooting node 감지 |
| bndout | bndout.py | 136 | 경계 반력 파서. 반력/모멘트 추출, 반력 스파이크 감지 |
| matsum | matsum.py | 157 | 재료 요약 파서. 재료별 에너지/운동량 추출 |
| profile | profile.py | 144 | 부하 프로파일 파서 (load_profile.csv, cont_profile.csv) |
| status | status.py | 43 | status.out 파서. CPU/clock 타이밍 |
| slurm | slurm.py | 160 | Slurm HPC 잡 에러 파서. segfault, MPI 에러, exit code, 스택 트레이스 |
| element_mapper | element_mapper.py | 106 | 입력 데크 파서. 요소→파트 매핑 |

---

## 4. 분석 모듈 현황 (8개)

### 4.1 수치 불안정 분석 (numerical_instability.py — 1,122줄)

전체 수치 건전성 검사의 약 95% 커버리지를 달성합니다.

| 진단 항목 | 함수명 | 임계값 | 심각도 |
|-----------|--------|--------|--------|
| Shooting node | detect_shooting_nodes | |v| > 1000 m/s | CRITICAL |
| 고주파 진동 | detect_high_freq_oscillation | ZCR > 10 kHz | WARNING |
| 반력 스파이크 | detect_reaction_force_spike | max/mean > 100 | CRITICAL |
| 반력 진동 | detect_reaction_force_oscillation | ZCR 기반 | WARNING |
| Hourglass 지배 | detect_hourglass_dominance | HG/IE > 10%/20% | WARNING/CRITICAL |
| KE 폭발 | detect_ke_explosion | 100x 급증 | CRITICAL |
| KE/IE 비율 이상 | detect_ke_ie_anomaly | > 10 (준정적) | WARNING |
| 접촉 에너지 과다 | detect_contact_energy_excessive | Slide/IE > 30% | WARNING |
| 접촉 에너지 스파이크 | detect_contact_energy_spike | 50x 급증 | CRITICAL |
| 타임스텝 변동 | detect_timestep_volatility | 10x 급락/진동 | WARNING/INFO |
| NaN 에너지 감지 | detect_nan_in_energy | NaN in glstat | CRITICAL |
| 음수 에너지 성분 | detect_negative_energy_components | IE < 0 또는 Slide < 0 | CRITICAL |
| Slurm 장애 진단 | diagnose_slurm_failures | segfault, MPI, exit code | CRITICAL |

### 4.2 성능 병목 분석 (performance.py — 181줄)

| 진단 항목 | 임계값 | 심각도 |
|-----------|--------|--------|
| Force gather 과다 | > 5%/10% | WARNING/CRITICAL |
| Mass scaling 과다 | > 5% | WARNING |
| 접촉 알고리즘 과다 | > 40%/50% | WARNING/CRITICAL |
| MPP 부하 불균형 | > 30%/50% | WARNING/CRITICAL |
| MPI 스케일링 예측 | Amdahl 법칙 기반 | INFO |

### 4.3 에너지 분석 (energy.py — 156줄)

| 진단 항목 | 임계값 | 심각도 |
|-----------|--------|--------|
| 에너지 보존 위반 | ratio > 1.10 / < 0.90 | WARNING |
| 에너지 심각 위반 | ratio > 3.0 / 4.0 | WARNING/CRITICAL |
| Hourglass 비율 | > 10% | WARNING |
| Sliding interface | > 10% | WARNING |

### 4.4 진단 엔진 (diagnostics.py — 691줄)

| 진단 항목 | 설명 |
|-----------|------|
| 접촉 dt 상한 | LS-DYNA 권장 접촉 안정성 dt 진단 |
| 에너지 불균형 | 에너지 비율 추세 분석 |
| 경고 패턴 | Warning 50135/50136 tied contact 인터페이스별 분석 |
| 파트 타임스텝 지배 | 특정 파트가 전체 dt를 지배하는지 분석 |
| 분해 불균형 | MPP 도메인 분해 품질 |

### 4.5 기타 분석 모듈

| 모듈 | 라인 | 설명 |
|------|------|------|
| warnings.py | 101 | 경고/에러 코드 분류 및 심각도 판정 |
| timestep.py | 120 | 타임스텝 행동 분석, 제어 파트 식별 |
| contact.py | 101 | 접촉 CPU 시간 분석, 병목 인터페이스 식별 |
| failure_analysis.py | 172 | 실패 근본 원인 분석, 요소/파트 교차참조 |

---

## 5. 지식 베이스 (error_db.py — 625줄)

LS-DYNA 에러/경고 코드 데이터베이스로 이론적 설명(한국어)과 구체적 권장사항을 포함합니다.

### 등록된 에러/경고 코드

| 카테고리 | 코드 | 제목 |
|----------|------|------|
| 접촉/인터페이스 | 50135 | Tied contact 노드 미구속 |
| | 50136 | Tied contact 노드 거리 초과 |
| | 50120 | 접촉 세그먼트 법선 불일치 |
| | 20248 | 초기 관통 |
| | 20200 | 접촉 인터페이스 세그먼트 없음 |
| Negative Volume | 30010 | Negative volume (에러 종료) |
| | 40003 | Negative volume (솔리드) |
| | 40004 | Negative volume (쉘) |
| | 40509 | Negative volume 경고 |
| NaN 검출 | 40455 | NaN detected (프로세서별) |
| | 40456 | NaN detected (전역) |
| | 30200 | NaN 속도 검출 |
| | 30100 | NaN 응력 계산 |
| 제약조건 | 30358 | Constraint matrix 에러 |
| 메모리 | 10103 | 메모리 부족 |
| | 10100 | 분해 메모리 부족 |
| 요소 품질 | 40100 | Degenerate 요소 감지 |
| 타임스텝 | 30001 | 요소 타임스텝 TSMIN 미만 |
| 재료 | 41200 | 재료 파괴 기준 충족 |
| 강체 | 60100 | 강체 질량 과소 |
| 적응/리메싱 | 70100 | Adaptive remeshing 문제 |
| SPH | 80100 | SPH 입자 문제 |
| 라이선스 | 90001 | 라이선스 에러 |
| 기타 | Fallback | 미등록 코드 자동 처리 (범위 기반 심각도) |

---

## 6. 리포트 모듈 현황 (3개)

| 모듈 | 라인 | 형식 | 설명 |
|------|------|------|------|
| terminal.py | 630 | 터미널 | Rich 라이브러리 기반 컬러 터미널 출력 |
| html_report.py | 654 | HTML | 독립형 HTML 리포트, 임베디드 CSS |
| json_report.py | 62 | JSON | 구조화된 JSON 출력 |

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

## 7. 빌드 및 배포 (8개 스크립트)

| 파일 | 플랫폼 | 용도 |
|------|--------|------|
| build_linux.sh | Linux | PyInstaller 빌드 |
| build_windows.ps1 | Windows | PyInstaller 빌드 (PowerShell) |
| build_windows.bat | Windows | PyInstaller 빌드 (CMD) |
| install.sh | Linux | venv 생성 + 의존성 설치 |
| install.bat | Windows | venv 생성 + 의존성 설치 |
| koodyna.sh | Linux | 실행 래퍼 |
| koodyna.bat | Windows | 실행 래퍼 |
| koodyna.spec | 공통 | PyInstaller 스펙 파일 |

---

## 8. 테스트 검증 결과

### 8.1 테스트 데이터 폴더 (10개)

| # | 폴더명 | 종료 상태 | 진단 건수 | 주요 실패 원인 |
|---|--------|-----------|-----------|----------------|
| 1 | results/ (기본) | 정상 종료 | 2C / 10W / 6I = 18 | 정상 완료 (HG 에너지 경고) |
| 2 | ball_drop_v2_dp_ex09 | 에러 종료 | 4C / 5W / 4I = 13 | Negative volume (40509, 5건) |
| 3 | ball_drop_v2_dp_ex16 | 에러 종료 | 6C / 3W / 6I = 15 | NaN 감지 (40455/40456) |
| 4 | ball_drop_v2_sp_ex06 | 에러 종료 | 4C / 5W / 3I = 12 | Negative volume (40509, 4건) |
| 5 | ball_drop_v2_sp_ex09 | 미완료 | 5C / 2W / 1I = 8 | Segfault, 음수 sliding |
| 6 | ball_drop_v2_sp_ex14 | 미완료 | 5C / 2W / 1I = 8 | Segfault, NaN |
| 7 | ball_drop_v2_sp_ex16 | 미완료 | 2C / 3W / 1I = 6 | Segfault |
| 8 | ball_drop_v4_ex12 | 에러 종료 | 3C / 3W / 4I = 10 | Negative volume (40509, 3건) |
| 9 | level_study_ex06 | 에러 종료 | 9C / 3W / 1I = 13 | NaN, 타임스텝 붕괴 |
| 10 | level_study_ex08 | 미완료 | 4C / 2W / 0I = 6 | KE 폭발, MPI 에러 |

### 8.2 총계

- 분석 대상 폴더: 10개
- 총 진단 건수: 109건 (44 CRITICAL, 38 WARNING, 27 INFO)
- 정상 종료: 1 / 에러 종료: 5 / 미완료: 4

### 8.3 감지된 실패 모드 분포

| 실패 모드 | 발생 폴더 수 |
|-----------|--------------|
| Negative volume (Error 40509) | 4 |
| 에너지 발산 | 5 |
| Segmentation fault (Signal 11) | 3 |
| NaN 검출 (Error 40455/40456) | 2 |
| 에너지 보존 심각 위반 | 4 |
| MPI 통신 에러 | 1 |

---

## 9. 데이터 모델 현황 (23개 dataclass)

| # | 클래스명 | 필드 수 | 역할 |
|---|---------|---------|------|
| 1 | Report | 22 | 최상위 리포트 컨테이너 |
| 2 | SimulationHeader | 12 | 시뮬레이션 메타데이터 |
| 3 | ModelSize | 10 | 모델 크기 |
| 4 | TerminationInfo | 12 | 종료 상태 |
| 5 | EnergySnapshot | 17 | 사이클별 에너지 |
| 6 | EnergyAnalysis | 6 | 에너지 분석 결과 |
| 7 | TimestepEntry | 5 | 타임스텝 항목 |
| 8 | TimestepAnalysis | 7 | 타임스텝 분석 |
| 9 | PartDefinition | 15 | 파트 정의 |
| 10 | PerformanceTiming | 5 | 성능 타이밍 |
| 11 | ContactTiming | 5 | 접촉 타이밍 |
| 12 | MPPProcessorTiming | 4 | MPP 프로세서 |
| 13 | LoadProfileEntry | 15 | 부하 프로파일 |
| 14 | ContactDefinition | 6 | 접촉 정의 |
| 15 | ContProfileEntry | 2 | 접촉 프로파일 |
| 16 | ScalingProjection | 5 | 스케일링 예측 |
| 17 | InterfaceSurfaceTimestep | 7 | 서프스 dt |
| 18 | DecompMetrics | 4 | 분해 메트릭 |
| 19 | MassProperty | 8 | 질량 속성 |
| 20 | StatusInfo | 7 | 실행 상태 |
| 21 | Finding | 5 | 진단 결과 항목 |
| 22 | WarningEntry | 7 | 경고 항목 |
| 23 | SlurmJobInfo | 10 | Slurm 잡 정보 |

---

## 10. 최근 주요 업데이트 이력

### 2026-03-03: MPP mes 파일 에러 통합
- MPP에서 비-제로 랭크 mes 파일의 에러를 d3hsp 에러와 병합
- error_db에 Error 40455/40456 코드 등록

### 2026-03-03: d3hsp 파서 상태전이 버그 수정
- 경고/에러 없는 d3hsp에서 CONTACTS→BODY 전이 실패 수정

### 2026-03-03: glstat dt2ms + NaN 감지
- dt2ms 포맷 파싱, NaN/Inf 문자열 매칭 추가

### 2026-03-03: Slurm 잡 에러 파서 신규
- slurm_*.err 파싱, 분석 파이프라인 통합

### 이전: 이론적 설명 강화
- error_db 전 코드에 한국어 FEM 이론 설명 추가

### 이전: 수치 불안정 진단 95% 커버리지
- nodout/bndout/glstat/성능/경고패턴/파트레벨 진단 완성

---

## 11. 알려진 제한사항

1. 단위 테스트 없음 (데이터 기반 검증만)
2. SMP 모드 미지원 (MPP만)
3. Implicit 해석 미지원
4. 대용량 nodout/bndout 스트리밍 최적화 미완
5. ALE/SPH 진단 제한

---

## 12. 향후 개발 방향

| 우선순위 | 항목 | 설명 |
|----------|------|------|
| 높음 | 단위 테스트 | pytest 기반 파서/분석 단위 테스트 |
| 높음 | Implicit 해석 | 수렴 이력, 반복 횟수 진단 |
| 중간 | 비교 분석 | 다중 폴더 간 비교 리포트 |
| 중간 | 시각화 강화 | matplotlib 그래프 HTML 내장 |
| 낮음 | GUI 모드 | 대화형 인터페이스 |
| 낮음 | CI/CD | GitHub Actions 자동 빌드/테스트 |
