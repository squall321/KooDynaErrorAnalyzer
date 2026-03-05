"""Generate FEATURE_STATUS_REPORT.docx from FEATURE_STATUS_REPORT.md."""

from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import re


def set_table_style(table):
    table.style = "Table Grid"
    for row in table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                para.paragraph_format.space_before = Pt(2)
                para.paragraph_format.space_after = Pt(2)
                for run in para.runs:
                    run.font.size = Pt(9)


def shade_row(row, hex_color="D9E1F2"):
    for cell in row.cells:
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_color)
        tcPr.append(shd)


def bold_row(row, size=9):
    for cell in row.cells:
        for para in cell.paragraphs:
            for run in para.runs:
                run.bold = True
                run.font.size = Pt(size)


def add_heading(doc, text, level):
    h = doc.add_heading(text, level=level)
    h.paragraph_format.space_before = Pt(10 if level == 1 else 6)
    h.paragraph_format.space_after = Pt(4)
    return h


def add_para(doc, text, size=10, bold=False, italic=False, color=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)
    p.paragraph_format.space_after = Pt(3)
    return p


def add_code_block(doc, text):
    for line in text.strip().split("\n"):
        p = doc.add_paragraph(style="No Spacing")
        run = p.add_run(line if line else " ")
        run.font.name = "Courier New"
        run.font.size = Pt(8)
        # light gray background via character shading not easy in docx,
        # so we just use monospace font
    doc.add_paragraph()


def make_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    set_table_style(table)

    # Header row
    hdr_row = table.rows[0]
    shade_row(hdr_row, "2F5496")
    for i, h in enumerate(headers):
        cell = hdr_row.cells[i]
        p = cell.paragraphs[0]
        run = p.add_run(h)
        run.bold = True
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # Data rows
    for ri, row_data in enumerate(rows):
        row = table.rows[ri + 1]
        if ri % 2 == 0:
            shade_row(row, "EEF2F9")
        for ci, cell_text in enumerate(row_data):
            cell = row.cells[ci]
            p = cell.paragraphs[0]
            run = p.add_run(str(cell_text))
            run.font.size = Pt(9)

    if col_widths:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Inches(w)

    doc.add_paragraph()
    return table


def build_docx():
    doc = Document()

    # Page margins
    section = doc.sections[0]
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)

    # Default font
    doc.styles["Normal"].font.name = "맑은 고딕"
    doc.styles["Normal"].font.size = Pt(10)

    # ── Title ──────────────────────────────────────────────────────────────
    title = doc.add_heading("KooDynaErrorAnalyzer 종합 기능 보고서", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    mr = meta.add_run("버전: 0.1.0    |    작성일: 2026-03-04    |    총 코드: 8,932줄 / 32개 파일")
    mr.font.size = Pt(9)
    mr.font.italic = True
    doc.add_paragraph()

    # ── 1. 개요 ────────────────────────────────────────────────────────────
    add_heading(doc, "1. 프로젝트 개요", 1)
    add_para(doc, (
        "KooDynaErrorAnalyzer는 LS-DYNA MPP 유한요소 시뮬레이션 결과를 자동 파싱·분석하여 "
        "수치 불안정, 성능 병목, 실패 원인을 한국어로 진단하는 CLI/GUI 도구입니다. "
        "d3hsp, glstat, mesXXXX, nodout, bndout, slurm.err 등 주요 결과 파일을 모두 지원합니다."
    ))

    make_table(doc,
        ["항목", "내용"],
        [
            ["언어", "Python 3.10+"],
            ["총 코드 규모", "8,932줄 / 32개 소스 파일"],
            ["출력 형식", "한국어 터미널(Rich) / HTML / JSON"],
            ["분석 대상", "d3hsp, glstat, mesXXXX, nodout, bndout, slurm.err 등"],
            ["빌드", "PyInstaller 단일 실행파일 (Linux / Windows)"],
            ["GUI", "tkinter 기반 폴더 선택 → 자동 분석 → HTML 오픈"],
        ],
        col_widths=[2.0, 4.0]
    )

    add_heading(doc, "핵심 실행 명령", 2)
    add_code_block(doc, """\
# 단일 폴더 분석 (터미널 리포트)
PYTHONPATH=src python3 -m koodyna <결과폴더>/

# HTML 리포트 생성
PYTHONPATH=src python3 -m koodyna <결과폴더>/ --html report.html

# /data 전체 인덱싱
PYTHONPATH=src python3 -m koodyna --scan /data

# 배치 분석 (JSON + HTML, 진행 보존)
PYTHONPATH=src python3 -m koodyna --analyze --output-dir /data/koodyna_reports

# 인덱스 현황 조회
PYTHONPATH=src python3 -m koodyna --list-index""")

    # ── 2. 아키텍처 ────────────────────────────────────────────────────────
    add_heading(doc, "2. 아키텍처 — 6-Phase 분석 파이프라인", 1)
    add_code_block(doc, """\
src/koodyna/
├── __main__.py          진입점
├── cli.py               CLI (argparse) — 단일/배치/GUI/스캔 모드
├── analyzer.py          오케스트레이터 (6-Phase 파이프라인)
├── models.py            데이터 모델 (23개 dataclass, 2개 Enum)
├── scanner.py           디렉터리 인덱싱 + 배치 분석
├── parsers/             파일 파서 10개
├── analysis/            분석 엔진 8개
├── knowledge/           에러/경고 지식 베이스
└── report/              리포트 생성기 3개 (터미널/HTML/JSON)""")

    make_table(doc,
        ["Phase", "역할"],
        [
            ["1. 파일 탐색", "d3hsp, glstat, mes*, nodout, bndout, slurm.err 자동 탐지"],
            ["2. 파싱", "10개 파서로 구조화된 데이터 추출"],
            ["3. 리포트 조립", "파싱 결과 → Report 데이터 모델 통합"],
            ["4. 분석", "에너지·타임스텝·경고·접촉·성능 분석"],
            ["5. 진단", "수치 불안정·실패 원인·Slurm 장애 진단"],
            ["6. 후처리", "중복/과민 Finding 제거 (deduplication)"],
        ],
        col_widths=[1.8, 4.2]
    )

    # ── 3. 파서 ────────────────────────────────────────────────────────────
    add_heading(doc, "3. 파서 모듈 (10개)", 1)
    add_heading(doc, "3.1 핵심 파서", 2)
    make_table(doc,
        ["파서", "추출 정보"],
        [
            ["d3hsp", "시뮬레이션 헤더·모델 크기·종료 상태·경고/에러·타임스텝·파트·성능·접촉·MPP·에너지·질량 속성"],
            ["glstat", "사이클별 에너지 스냅샷 (KE, IE, HG, Sliding, External work, 에너지 비율). NaN/Inf 감지"],
            ["messag (mesXXXX)", "MPP 전 랭크 처리. 경고/에러·초기 관통·인터페이스 경고·최소 dt·서프스 dt·접촉 dt 상한"],
        ],
        col_widths=[1.5, 4.5]
    )

    add_heading(doc, "3.2 보조 파서", 2)
    make_table(doc,
        ["파서", "추출 정보"],
        [
            ["nodout", "노드 시계열 (변위·속도). Shooting node / 고주파 진동 감지"],
            ["bndout", "경계 반력·모멘트. 반력 스파이크·진동 감지"],
            ["slurm", "Slurm HPC 잡 에러. Segfault·MPI 에러·exit code·스택 트레이스"],
            ["matsum", "재료별 에너지·운동량"],
            ["profile", "load_profile.csv / cont_profile.csv 부하 프로파일"],
            ["status", "status.out — CPU/clock 타이밍"],
            ["element_mapper", "입력 덱 파서 — 요소→파트 매핑"],
        ],
        col_widths=[1.5, 4.5]
    )

    # ── 4. 분석 엔진 ───────────────────────────────────────────────────────
    add_heading(doc, "4. 분석 엔진 (8개 모듈)", 1)
    add_heading(doc, "4.1 수치 불안정 분석 — 커버리지 약 95%", 2)
    make_table(doc,
        ["진단 항목", "임계값", "심각도"],
        [
            ["Shooting node", "|v| > 1,000 m/s", "CRITICAL"],
            ["고주파 진동", "ZCR > 10 kHz", "WARNING"],
            ["반력 스파이크", "max/mean > 100", "CRITICAL"],
            ["Hourglass 에너지 지배", "HG/IE > 10% / 50%", "WARNING / CRITICAL"],
            ["운동 에너지 폭발", "100x 급증", "CRITICAL"],
            ["접촉 슬라이딩 에너지 과다", "Slide/IE > 30%", "WARNING"],
            ["타임스텝 변동", "10x 급락", "WARNING"],
            ["NaN 에너지 감지", "glstat NaN/Inf", "CRITICAL"],
            ["음수 에너지 성분", "IE < 0 또는 Slide < 0", "CRITICAL"],
            ["Slurm 장애 진단", "segfault, MPI error, exit code", "CRITICAL"],
        ],
        col_widths=[2.2, 2.2, 1.6]
    )

    add_heading(doc, "4.2 에너지 분석", 2)
    make_table(doc,
        ["진단 항목", "임계값", "심각도"],
        [
            ["에너지 보존 편차", "ratio > 1.05 또는 < 0.95", "WARNING"],
            ["에너지 보존 심각 위반", "ratio > 1.10 또는 < 0.90", "CRITICAL"],
            ["에너지 발산", "총 에너지 5% 이상 성장", "CRITICAL"],
            ["Hourglass 비율", "> 10% / > 50%", "WARNING / CRITICAL"],
            ["Sliding 에너지 과다", "> 15% (total 대비)", "WARNING"],
        ],
        col_widths=[2.2, 2.2, 1.6]
    )

    add_heading(doc, "4.3 성능 분석", 2)
    make_table(doc,
        ["진단 항목", "임계값", "심각도"],
        [
            ["접촉 계산 과다", "> 40% / > 50%", "WARNING / CRITICAL"],
            ["Force gather 과다", "> 5% / > 10%", "WARNING / CRITICAL"],
            ["Mass scaling 과다", "> 5%", "WARNING"],
            ["MPP 부하 불균형", "> 15% / ≥ 100%", "WARNING / CRITICAL"],
            ["MPI 스케일링 예측", "Amdahl 법칙 기반", "INFO"],
        ],
        col_widths=[2.2, 2.2, 1.6]
    )

    add_heading(doc, "4.4 Finding 중복 제거 (deduplication)", 2)
    add_para(doc, (
        "분석 파이프라인 Phase 6에서 더 구체적인 진단이 있을 때 하위 중복 진단을 자동 억제합니다. "
        "예: \"Excessive contact sliding energy\" (WARNING) 존재 시 "
        "\"High sliding interface energy\" (WARNING) 자동 억제."
    ))

    # ── 5. 지식 베이스 ─────────────────────────────────────────────────────
    add_heading(doc, "5. 지식 베이스 — error_db (약 50개 코드)", 1)
    add_para(doc, "LS-DYNA 에러·경고 코드 데이터베이스 — 한국어 FEM 이론 설명 + 구체적 권장사항 포함.")

    add_heading(doc, "5.1 코드 범위별 등록 현황", 2)
    make_table(doc,
        ["범위", "카테고리", "주요 코드"],
        [
            ["10xxx, 11xxx", "요소 에러", "10100, 10103, 10133, 10246, 10305, 11507"],
            ["20xxx", "재료", "20018, 20200, 20216, 20248, 20268, 20282, 20546"],
            ["21xxx", "곡선/테이블", "21129, 21302, 21329"],
            ["30xxx", "초기화/제약/접촉", "30001, 30010, 30062, 30099, 30100, 30128, 30131, 30200, 30358, 30455"],
            ["40xxx", "런타임 경고", "40003, 40004, 40455, 40456, 40509, 40532, 40533, 40538, 40552, 40571, 41200, 41314"],
            ["50xxx", "타이드 접촉", "50120, 50135, 50136"],
            ["60xxx", "암시적 해석", "60004, 60100, 60121, 60303, 60315"],
            ["70xxx, 80xxx", "SPH/입자", "70021, 70100, 80100"],
            ["90xxx", "라이선스", "90001"],
            ["Fallback", "미등록 자동 처리", "범위 기반 심각도 판정"],
        ],
        col_widths=[1.2, 1.5, 3.3]
    )

    add_heading(doc, "5.2 고빈도 코드 (실측 발생 건수)", 2)
    make_table(doc,
        ["코드", "제목", "발생 건수"],
        [
            ["40533", "Contact velocity too high (slave node)", "250,000+"],
            ["40538", "Slave node released from contact", "198,000+"],
            ["21129", "Curve extrapolation beyond defined range", "102,000+"],
            ["40532", "Slave node penetration velocity limit exceeded", "57,000+"],
            ["30099", "Contact pair definition error", "3,654"],
            ["21302", "Curve ID reference invalid or undefined", "320"],
            ["60303 / 60315", "Implicit solver 수렴 실패", "55"],
            ["11507", "SPG particle stretch parameter error", "5"],
        ],
        col_widths=[1.0, 3.5, 1.5]
    )

    # ── 6. 인덱싱 시스템 ──────────────────────────────────────────────────
    add_heading(doc, "6. 결과 디렉터리 인덱싱 시스템 (scanner.py)", 1)
    add_para(doc, (
        "대규모 결과 디렉터리 트리를 재귀 탐색하여 d3plot이 있는 모든 폴더를 "
        "JSON 인덱스(~/.koodyna/index.json)로 관리합니다. "
        "분석 상태(pending / analyzed / failed / skipped)를 추적하여 "
        "중단 후 재시작도 안전하게 지원합니다."
    ))

    add_heading(doc, "6.1 /data 스캔 실측 결과", 2)
    make_table(doc,
        ["항목", "값"],
        [
            ["탐색 기반 디렉터리", "/data"],
            ["발견된 d3plot 폴더", "2,397개"],
            ["results/ 추가", "10개"],
            ["총 인덱스 항목", "2,407개"],
            ["Study 타입 수", "38개 이상"],
            ["주요 Study 타입", "floor_wave_study(143), vapor_chamber(93), shield_can_forming(92), pcb_vibration(88), rubber_advanced_study(56) 등"],
        ],
        col_widths=[2.5, 3.5]
    )

    add_heading(doc, "6.2 배치 분석 CLI 옵션", 2)
    make_table(doc,
        ["옵션", "설명"],
        [
            ["--scan <BASE_DIR>", "BASE_DIR 재귀 탐색 → 인덱스 갱신"],
            ["--analyze", "인덱스 pending 항목 배치 분석 (JSON + HTML)"],
            ["--output-dir <DIR>", "리포트 저장 위치 (기본: ~/.koodyna/reports/)"],
            ["--limit N", "최대 처리 건수 (0 = 전체)"],
            ["--no-html", "JSON만 생성 (HTML 생략)"],
            ["--reanalyze", "이미 분석된 항목도 재실행"],
            ["--list-index", "인덱스 현황 테이블 출력"],
            ["--index <PATH>", "인덱스 파일 경로 지정"],
        ],
        col_widths=[2.0, 4.0]
    )

    add_code_block(doc, """\
# 리포트 저장 구조
/data/koodyna_reports/
  floor_wave_study/
    case_01.json
    case_01.html
    case_02.json
    ...
  vapor_chamber/
    ...""")

    # ── 7. 리포트 시스템 ──────────────────────────────────────────────────
    add_heading(doc, "7. 리포트 시스템 (3개 형식)", 1)
    make_table(doc,
        ["형식", "모듈", "특징"],
        [
            ["터미널", "terminal.py", "Rich 컬러 출력, 한국어, 14개 섹션"],
            ["HTML", "html_report.py", "독립형 (임베디드 CSS), 브라우저 자동 오픈"],
            ["JSON", "json_report.py", "구조화 데이터, 배치 처리·비교 분석용"],
        ],
        col_widths=[1.0, 1.5, 3.5]
    )

    add_heading(doc, "리포트 14개 섹션", 2)
    for i, sec in enumerate([
        "시뮬레이션 헤더 (버전·날짜·호스트·정밀도·라이선스)",
        "모델 요약 (노드·요소·파트·접촉·SPC 수)",
        "종료 상태 (정상/에러/미완료·목표시간·사이클·CPU)",
        "진단 결과 ★ (CRITICAL / WARNING / INFO 분류 + 설명 + 권장사항)",
        "경고/에러 요약 (코드별 횟수·심각도·인터페이스)",
        "에너지 분석 (비율 범위·HG/Sliding 비율)",
        "타임스텝 분석 (100개 최소 dt·제어 파트)",
        "성능 타이밍 (컴포넌트별 CPU/Clock 비율)",
        "접촉 타이밍 (인터페이스별 비용)",
        "MPP 부하 균형 (프로세서별 CPU 비율)",
        "MPI 스케일링 예측 (Amdahl 법칙·코어별 효율)",
        "접촉 서프스 타임스텝 (인터페이스별 dt)",
        "파트 정의 (재료·밀도·탄성계수·ELFORM)",
        "Slurm 잡 정보 (exit code·signal·MPI 에러)",
    ], 1):
        p = doc.add_paragraph(style="List Number")
        p.add_run(sec).font.size = Pt(9)
    doc.add_paragraph()

    # ── 8. 검증 결과 ──────────────────────────────────────────────────────
    add_heading(doc, "8. 검증 — 10개 테스트 케이스 결과", 1)
    make_table(doc,
        ["케이스", "종료 상태", "CRIT", "WARN", "주요 실패 원인"],
        [
            ["results_normal", "정상 종료", "0", "2", "기준 케이스 (HG 경고)"],
            ["ball_drop_v2_dp_ex09", "에러 종료", "4", "3", "Negative volume (40509), 에너지 발산"],
            ["ball_drop_v2_dp_ex16", "에러 종료", "6", "1", "NaN (40455/40456), 음수 Sliding"],
            ["ball_drop_v2_sp_ex06", "에러 종료", "4", "3", "Negative volume, Slurm exit 3"],
            ["ball_drop_v2_sp_ex09", "미완료", "5", "0", "Segfault (Signal 11), 음수 Sliding"],
            ["ball_drop_v2_sp_ex14", "미완료", "5", "0", "Segfault, NaN 에너지"],
            ["ball_drop_v2_sp_ex16", "미완료", "2", "1", "Segfault, 에너지 편차"],
            ["ball_drop_v4_ex12", "에러 종료", "4", "0", "Negative volume, MPP 불균형 129% (CRIT)"],
            ["level_study_ex06", "에러 종료", "9", "1", "NaN + 타임스텝 붕괴 + 에너지 폭주"],
            ["level_study_ex08", "미완료", "4", "1", "KE 폭발, MPI 통신 에러"],
        ],
        col_widths=[2.0, 1.2, 0.6, 0.6, 2.6]
    )

    add_heading(doc, "감지된 실패 모드 분포", 2)
    make_table(doc,
        ["실패 모드", "감지 케이스 수"],
        [
            ["에너지 발산 (에너지 비율 > 1.10)", "5"],
            ["Negative volume (Error 40509)", "4"],
            ["Segmentation fault (Signal 11)", "4"],
            ["NaN 검출 (Error 40455/40456)", "2"],
            ["MPP 부하 불균형 > 100% (CRITICAL)", "1"],
            ["MPI 통신 에러", "1"],
            ["타임스텝 붕괴", "1"],
        ],
        col_widths=[4.0, 2.0]
    )

    # ── 9. 개발 이력 ──────────────────────────────────────────────────────
    add_heading(doc, "9. 주요 개발 이력", 1)

    items_2026_03_04 = [
        "배치 분석: run_batch_analyze() — JSON + HTML 동시 생성, 50건 단위 중간 저장",
        "CLI: --analyze / --output-dir / --limit / --no-html / --reanalyze 추가",
        "Finding 중복 제거 강화: Excessive contact sliding(WARNING) 존재 시 High sliding 억제",
        "MPP 부하 불균형 ≥ 100% → CRITICAL 승격",
        "접촉 dt: min_dt > contact_dt_limit일 때만 WARNING (그 외 INFO)",
        "SLIDING_RATIO_WARN: 5% → 15% (노이즈 감소)",
        "/data 인덱싱: scanner.py 신규, 2,397개 폴더 발견 (총 2,407개)",
        "error_db 28개 코드 신규 등록 (실측 고빈도 기반)",
        "CLI: --scan / --index / --list-index 추가",
    ]
    add_heading(doc, "2026-03-04", 2)
    for item in items_2026_03_04:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(item).font.size = Pt(9)
    doc.add_paragraph()

    items_2026_03_03 = [
        "slurm.py: Slurm HPC 잡 에러 파싱 (segfault, MPI, exit code, 스택 트레이스)",
        "detect_nan_in_energy(): glstat NaN/Inf 감지",
        "detect_negative_energy_components(): 음수 IE/Sliding CRITICAL 진단",
        "MPP mes 파일 에러 병합: 비-제로 랭크 에러 d3hsp와 통합",
        "Error 40455/40456 (NaN detected) error_db 등록",
        "전체 error_db 코드에 한국어 FEM 이론 설명 강화",
        "수치 불안정 진단 95% 커버리지 달성 (nodout/bndout/glstat/성능/파트레벨)",
    ]
    add_heading(doc, "2026-03-03", 2)
    for item in items_2026_03_03:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(item).font.size = Pt(9)
    doc.add_paragraph()

    # ── 10. 현재 상태 ─────────────────────────────────────────────────────
    add_heading(doc, "10. 현재 상태 및 향후 계획", 1)

    add_heading(doc, "10.1 기능 완료 현황", 2)
    make_table(doc,
        ["항목", "상태"],
        [
            ["단일 폴더 분석 (터미널/HTML/JSON)", "✅ 완료"],
            ["10개 검증 케이스", "✅ 완료"],
            ["error_db 50개 코드", "✅ 완료"],
            ["/data 인덱싱 (2,407개)", "✅ 완료"],
            ["/data 배치 분석 실행", "🔄 진행 중 (백그라운드)"],
            ["Linux/Windows 빌드", "✅ 완료"],
            ["GUI 모드 (tkinter)", "✅ 완료"],
            ["단위 테스트", "❌ 미구현"],
            ["다중 케이스 비교 리포트", "❌ 미구현"],
        ],
        col_widths=[3.5, 2.5]
    )

    add_heading(doc, "10.2 알려진 제한사항", 2)
    for item in [
        "단위 테스트 없음 (데이터 기반 검증만)",
        "SMP 모드 미지원 (MPP만 지원)",
        "Implicit 해석 심층 진단 미구현 (코드 등록은 완료)",
        "대용량 nodout/bndout 스트리밍 최적화 미완",
        "ALE/SPH 진단 제한적",
    ]:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(item).font.size = Pt(9)
    doc.add_paragraph()

    add_heading(doc, "10.3 향후 개발 방향", 2)
    make_table(doc,
        ["우선순위", "항목"],
        [
            ["높음", "/data 배치 분석 결과 취합 및 패턴 분석"],
            ["높음", "단위 테스트 (pytest) 구축"],
            ["중간", "다중 케이스 비교 리포트"],
            ["중간", "Implicit 해석 심층 진단"],
            ["중간", "matplotlib 에너지 시계열 그래프 HTML 내장"],
            ["낮음", "CI/CD 자동 빌드 (GitHub Actions)"],
        ],
        col_widths=[1.5, 4.5]
    )

    doc.save("FEATURE_STATUS_REPORT.docx")
    print("FEATURE_STATUS_REPORT.docx 생성 완료")


if __name__ == "__main__":
    build_docx()
