"""HTML report generator for LS-DYNA simulation analysis (Korean output)."""

import html
from pathlib import Path

from koodyna.models import Report, Severity, TerminationStatus

# Contact type code resolution (Korean)
_CONTACT_TYPE_KR = {
    ("", 1): "슬라이딩 전용",
    ("", 2): "Tied S2S",
    ("", 3): "Surface to Surface",
    ("", 4): "Single Surface",
    ("", 5): "Nodes to Surface",
    ("", 13): "Auto Single Surface",
    ("", 14): "Eroding S2S",
    ("", 15): "Eroding Single Surf",
    ("", 25): "Auto S2S (Offset)",
    ("", 26): "Auto Single (Offset)",
    ("o", 2): "Tied S2S",
    ("o", 3): "Tied S2S (OPTION)",
    ("o", 5): "Tied Nodes to Surf",
    ("a", 2): "Auto Tied S2S",
    ("a", 3): "Auto S2S",
    ("a", 4): "Auto Single Surface",
    ("a", 13): "Auto Single Surface",
}


def _esc(s: str) -> str:
    return html.escape(str(s))


def _fmt_sci(value: float) -> str:
    if value == 0.0:
        return "0"
    if abs(value) < 1e-3 or abs(value) > 1e6:
        return f"{value:.4E}"
    return f"{value:.4f}"


def _severity_class(severity: Severity) -> str:
    if severity == Severity.CRITICAL:
        return "critical"
    elif severity == Severity.WARNING:
        return "warning"
    return "info"


def _severity_kr(severity: Severity) -> str:
    if severity == Severity.CRITICAL:
        return "심각"
    elif severity == Severity.WARNING:
        return "경고"
    return "정보"


_CSS = """\
:root {
  --bg: #1a1b26;
  --bg2: #24283b;
  --bg3: #292e42;
  --fg: #c0caf5;
  --fg-dim: #565f89;
  --red: #f7768e;
  --orange: #ff9e64;
  --yellow: #e0af68;
  --green: #9ece6a;
  --cyan: #7dcfff;
  --blue: #7aa2f7;
  --magenta: #bb9af7;
  --border: #3b4261;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  background: var(--bg);
  color: var(--fg);
  font-family: 'Pretendard', 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 14px;
  line-height: 1.6;
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}
h1 {
  font-size: 22px;
  color: var(--blue);
  border-bottom: 2px solid var(--blue);
  padding-bottom: 8px;
  margin-bottom: 20px;
}
h2 {
  font-size: 16px;
  color: var(--cyan);
  margin: 28px 0 12px 0;
  padding: 6px 12px;
  background: var(--bg2);
  border-left: 3px solid var(--cyan);
  border-radius: 0 4px 4px 0;
}
.header-panel {
  background: var(--bg2);
  border: 1px solid var(--blue);
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 20px;
}
.header-panel .row { display: flex; gap: 24px; flex-wrap: wrap; }
.header-panel .label { color: var(--fg-dim); font-size: 12px; }
.header-panel .value { color: var(--fg); font-size: 14px; font-weight: 500; }
.status-normal { color: var(--green); font-weight: 700; }
.status-error { color: var(--red); font-weight: 700; }
.status-incomplete { color: var(--yellow); font-weight: 700; }
.term-panel {
  background: var(--bg2);
  border: 1px solid var(--cyan);
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 20px;
}
.term-panel .row { display: flex; gap: 32px; flex-wrap: wrap; margin-top: 8px; }
.term-panel .item { }
.term-panel .label { color: var(--fg-dim); font-size: 12px; }
.term-panel .value { font-size: 14px; }
.findings-summary {
  display: flex; gap: 16px; margin-bottom: 16px;
  padding: 12px 16px; background: var(--bg2); border-radius: 6px;
}
.findings-summary .badge {
  padding: 4px 12px; border-radius: 4px; font-weight: 600; font-size: 13px;
}
.badge-critical { background: rgba(247,118,142,0.15); color: var(--red); }
.badge-warning { background: rgba(224,175,104,0.15); color: var(--yellow); }
.badge-info { background: rgba(122,162,247,0.15); color: var(--blue); }
.finding {
  margin-bottom: 12px;
  padding: 10px 14px;
  background: var(--bg2);
  border-radius: 6px;
  border-left: 3px solid var(--border);
}
.finding.critical { border-left-color: var(--red); }
.finding.warning { border-left-color: var(--yellow); }
.finding.info { border-left-color: var(--blue); }
.finding .tag {
  font-size: 11px; font-weight: 700; padding: 2px 6px;
  border-radius: 3px; margin-right: 8px; display: inline-block;
}
.finding .tag.critical { background: rgba(247,118,142,0.2); color: var(--red); }
.finding .tag.warning { background: rgba(224,175,104,0.2); color: var(--yellow); }
.finding .tag.info { background: rgba(122,162,247,0.2); color: var(--blue); }
.finding .title { font-weight: 600; }
.finding .desc { color: var(--fg-dim); font-size: 13px; margin-top: 4px; }
.finding .rec { color: var(--green); font-size: 13px; margin-top: 4px; font-style: italic; }
table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 16px;
  font-size: 13px;
}
thead th {
  background: var(--bg3);
  color: var(--cyan);
  padding: 8px 10px;
  text-align: left;
  font-weight: 600;
  border-bottom: 2px solid var(--border);
  white-space: nowrap;
}
thead th.r { text-align: right; }
thead th.c { text-align: center; }
tbody td {
  padding: 5px 10px;
  border-bottom: 1px solid var(--bg3);
}
tbody td.r { text-align: right; font-variant-numeric: tabular-nums; }
tbody td.c { text-align: center; }
tbody td.id { color: var(--cyan); text-align: right; font-variant-numeric: tabular-nums; }
tbody td.mono { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 12px; }
tbody tr:hover { background: var(--bg3); }
.warn-high { color: var(--yellow); font-weight: 600; }
.eff-bad { color: var(--red); font-weight: 600; }
.eff-mid { color: var(--yellow); font-weight: 600; }
.bar-container { width: 100%; background: var(--bg3); border-radius: 3px; height: 16px; overflow: hidden; }
.bar-fill { height: 100%; background: var(--green); border-radius: 3px; min-width: 2px; }
.note { color: var(--fg-dim); font-size: 12px; margin-top: 4px; margin-bottom: 12px; }
.model-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 8px; margin-bottom: 16px;
}
.model-card {
  background: var(--bg2); border-radius: 6px; padding: 10px 14px; text-align: center;
}
.model-card .num { font-size: 20px; font-weight: 700; color: var(--fg); }
.model-card .lbl { font-size: 11px; color: var(--fg-dim); }
.footer { margin-top: 32px; padding-top: 12px; border-top: 1px solid var(--border); color: var(--fg-dim); font-size: 12px; }
"""


def write_html_report(report: Report, filepath: Path):
    """Write an HTML report file with Korean labels."""
    parts: list[str] = []
    _w = parts.append

    _w("<!DOCTYPE html>")
    _w('<html lang="ko">')
    _w("<head>")
    _w('<meta charset="UTF-8">')
    _w('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    _w(f"<title>LS-DYNA 해석 분석 리포트 — {_esc(report.header.input_file)}</title>")
    _w(f"<style>{_CSS}</style>")
    _w("</head><body>")

    _w(f"<h1>LS-DYNA 해석 분석 리포트</h1>")

    # === Header Panel ===
    h = report.header
    _w('<div class="header-panel">')
    _w('<div class="row">')
    for lbl, val in [
        ("버전", f"{h.version} ({h.revision})"),
        ("일시", f"{h.date} {h.time}"),
        ("호스트", h.hostname),
        ("입력 파일", h.input_file),
        ("정밀도", h.precision),
        ("플랫폼", h.platform),
        ("MPI 프로세서", f"{h.num_procs}개"),
        ("라이선스", h.licensee),
    ]:
        _w(f'<div><div class="label">{lbl}</div><div class="value">{_esc(val)}</div></div>')
    _w("</div></div>")

    # === Model Size ===
    _w("<h2>모델 요약</h2>")
    ms = report.model_size
    _w('<div class="model-grid">')
    for lbl, val in [
        ("노드", ms.num_nodes), ("솔리드 요소", ms.num_solid_elements),
        ("쉘 요소", ms.num_shell_elements), ("빔 요소", ms.num_beam_elements),
        ("파트", ms.num_parts), ("재료", ms.num_materials),
        ("접촉", ms.num_contacts), ("SPC 노드", ms.num_spc_nodes),
    ]:
        _w(f'<div class="model-card"><div class="num">{val:,}</div><div class="lbl">{lbl}</div></div>')
    _w("</div>")

    # === Termination ===
    _w("<h2>종료 상태</h2>")
    term = report.termination
    if term.status == TerminationStatus.NORMAL:
        s_class, s_label = "status-normal", "정상 종료"
    elif term.status == TerminationStatus.ERROR:
        s_class, s_label = "status-error", "오류 종료"
    else:
        s_class, s_label = "status-incomplete", "미완료 (출력 중단)"

    _w('<div class="term-panel">')
    _w(f'<span class="{s_class}">{s_label}</span>')
    _w('<div class="row">')
    for lbl, val in [
        ("목표 시간", _fmt_sci(term.target_time)),
        ("도달 시간", _fmt_sci(term.actual_time)),
        ("사이클 수", f"{term.total_cycles:,}"),
        ("CPU 시간", f"{term.total_cpu_seconds:.0f}초"),
        ("경과 시간", f"{term.elapsed_seconds:.0f}초"),
        ("CPU/zone-cycle", f"{term.cpu_per_zone_cycle_ns:.1f} ns"),
        ("Clock/zone-cycle", f"{term.clock_per_zone_cycle_ns:.1f} ns"),
    ]:
        _w(f'<div class="item"><div class="label">{lbl}</div><div class="value">{_esc(val)}</div></div>')
    _w("</div>")
    if term.start_datetime:
        _w(f'<div class="row" style="margin-top:8px">')
        _w(f'<div class="item"><div class="label">시작</div><div class="value">{_esc(term.start_datetime)}</div></div>')
        _w(f'<div class="item"><div class="label">종료</div><div class="value">{_esc(term.end_datetime)}</div></div>')
        _w("</div>")
    _w("</div>")

    # === Findings ===
    if report.findings:
        _w("<h2>진단 결과</h2>")
        c_cnt = sum(1 for f in report.findings if f.severity == Severity.CRITICAL)
        w_cnt = sum(1 for f in report.findings if f.severity == Severity.WARNING)
        i_cnt = sum(1 for f in report.findings if f.severity == Severity.INFO)
        _w('<div class="findings-summary">')
        _w(f'<span class="badge badge-critical">심각 {c_cnt}</span>')
        _w(f'<span class="badge badge-warning">경고 {w_cnt}</span>')
        _w(f'<span class="badge badge-info">정보 {i_cnt}</span>')
        _w("</div>")

        for f in report.findings:
            cls = _severity_class(f.severity)
            kr = _severity_kr(f.severity)
            _w(f'<div class="finding {cls}">')
            _w(f'<span class="tag {cls}">{kr}</span>')
            _w(f'<span class="title">{_esc(f.title)}</span>')
            if f.description:
                _w(f'<div class="desc">{_esc(f.description)}</div>')
            if f.recommendation:
                _w(f'<div class="rec">→ {_esc(f.recommendation)}</div>')
            _w("</div>")

    # === Warning Summary ===
    if report.warnings:
        _w("<h2>경고/오류 요약</h2>")
        _w("<table><thead><tr>")
        _w('<th class="r">코드</th><th class="r">횟수</th><th class="c">심각도</th><th>설명</th><th>인터페이스</th>')
        _w("</tr></thead><tbody>")
        for w in report.warnings[:20]:
            cls = _severity_class(w.severity)
            kr = _severity_kr(w.severity)
            intf_str = ""
            if w.affected_interfaces:
                intf_list = w.affected_interfaces[:8]
                intf_str = ", ".join(str(i) for i in intf_list)
                if len(w.affected_interfaces) > 8:
                    intf_str += f" (+{len(w.affected_interfaces)-8})"
            _w(f'<tr><td class="r id">{w.code}</td><td class="r">{w.count:,}</td>')
            _w(f'<td class="c"><span class="tag {cls}">{kr}</span></td>')
            _w(f'<td>{_esc(w.message[:80])}</td><td>{_esc(intf_str)}</td></tr>')
        _w("</tbody></table>")

    # === Contact Interface Summary ===
    if report.contact_definitions:
        _w("<h2>접촉 인터페이스 요약</h2>")
        ct_lookup = {ct.interface_id: ct for ct in report.contact_timing}
        warn_lookup = report.interface_warning_counts

        _w("<table><thead><tr>")
        _w('<th class="r">ID</th><th>타입</th><th>제목</th><th class="r">경고 수</th><th class="r">Clock (s)</th><th class="r">Clock %</th>')
        _w("</tr></thead><tbody>")
        for cd in report.contact_definitions:
            type_name = _CONTACT_TYPE_KR.get(
                (cd.type_prefix, cd.type_number), cd.type_code
            )
            wc = warn_lookup.get(cd.contact_id, 0)
            wc_cls = ' class="warn-high"' if wc > 100 else ""
            wc_str = f"{wc:,}" if wc > 0 else ""
            ct = ct_lookup.get(cd.contact_id)
            clock_s = f"{ct.clock_seconds:.4f}" if ct else ""
            clock_p = f"{ct.clock_percent:.2f}" if ct else ""
            _w(f'<tr><td class="id">{cd.contact_id}</td><td>{_esc(type_name)}</td>')
            _w(f'<td>{_esc(cd.title[:40])}</td><td class="r"{wc_cls}>{wc_str}</td>')
            _w(f'<td class="r mono">{clock_s}</td><td class="r">{clock_p}</td></tr>')
        _w("</tbody></table>")

    # === Energy Balance ===
    energy = report.energy
    if energy.snapshots:
        _w("<h2>에너지 수지</h2>")
        initial = energy.snapshots[0]
        final = energy.snapshots[-1]

        _w("<table><thead><tr>")
        _w('<th>항목</th><th class="r">초기값</th><th class="r">최종값</th>')
        _w("</tr></thead><tbody>")
        for lbl, iv, fv in [
            ("운동 에너지", initial.kinetic, final.kinetic),
            ("내부 에너지", initial.internal, final.internal),
            ("Hourglass 에너지", initial.hourglass, final.hourglass),
            ("슬라이딩 인터페이스", initial.sliding_interface, final.sliding_interface),
            ("총 에너지", initial.total, final.total),
            ("에너지 비율", initial.energy_ratio, final.energy_ratio),
        ]:
            _w(f'<tr><td>{lbl}</td><td class="r mono">{_fmt_sci(iv)}</td><td class="r mono">{_fmt_sci(fv)}</td></tr>')
        _w(f'<tr><td>최대 HG/내부에너지 비율</td><td class="r"></td><td class="r">{energy.max_hourglass_ratio:.1%}</td></tr>')
        _w("</tbody></table>")

    # === Smallest Timestep Elements ===
    ts = report.timestep
    if ts.smallest_timesteps:
        _w("<h2>최소 타임스텝 요소 (상위 20개)</h2>")
        sorted_entries = sorted(ts.smallest_timesteps, key=lambda e: e.timestep)

        has_proc = any(e.processor_id >= 0 for e in sorted_entries[:20])
        _w("<table><thead><tr>")
        _w('<th class="r">#</th><th>타입</th><th class="r">요소 ID</th><th class="r">파트</th><th class="r">dt</th>')
        if has_proc:
            _w('<th class="r">코어</th>')
        _w("</tr></thead><tbody>")
        for i, entry in enumerate(sorted_entries[:20], 1):
            _w(f'<tr><td class="r">{i}</td><td>{_esc(entry.element_type)}</td>')
            _w(f'<td class="id">{entry.element_number}</td><td class="r">{entry.part_number}</td>')
            _w(f'<td class="r mono">{entry.timestep:.4E}</td>')
            if has_proc:
                proc_str = f"#{entry.processor_id}" if entry.processor_id >= 0 else "?"
                _w(f'<td class="r">{proc_str}</td>')
            _w('</tr>')
        _w("</tbody></table>")

        # Part summary
        _w("<h2>파트별 타임스텝 요약 (100 최소)</h2>")
        part_info: dict[int, dict] = {}
        for entry in ts.smallest_timesteps:
            if entry.part_number not in part_info:
                part_info[entry.part_number] = {
                    "count": 0, "min_dt": entry.timestep,
                    "max_dt": entry.timestep, "elem_type": entry.element_type,
                }
            pi = part_info[entry.part_number]
            pi["count"] += 1
            pi["min_dt"] = min(pi["min_dt"], entry.timestep)
            pi["max_dt"] = max(pi["max_dt"], entry.timestep)

        _w("<table><thead><tr>")
        _w('<th class="r">파트</th><th class="r">개수</th><th class="r">최소 dt</th><th class="r">최대 dt</th><th>타입</th>')
        _w("</tr></thead><tbody>")
        for pid, info in sorted(part_info.items(), key=lambda x: x[1]["min_dt"]):
            _w(f'<tr><td class="id">{pid}</td><td class="r">{info["count"]}</td>')
            _w(f'<td class="r mono">{info["min_dt"]:.4E}</td><td class="r mono">{info["max_dt"]:.4E}</td>')
            _w(f'<td>{_esc(info["elem_type"])}</td></tr>')
        _w("</tbody></table>")
        _w(f'<div class="note">TSSFAC: {ts.dt_scale_factor} | 초기 dt: {_fmt_sci(ts.initial_dt)} | 최종 dt: {_fmt_sci(ts.final_dt)}</div>')

    # === Timestep Control Timeline ===
    snapshots = report.energy.snapshots
    if snapshots and snapshots[0].controlling_part > 0:
        runs: list[dict] = []
        for snap in snapshots:
            if snap.controlling_part == 0:
                continue
            key = (snap.controlling_part, snap.controlling_element)
            if runs and (runs[-1]["part"], runs[-1]["elem"]) == key:
                runs[-1]["end_cycle"] = snap.cycle
                runs[-1]["end_time"] = snap.time
                runs[-1]["count"] += 1
                runs[-1]["min_dt"] = min(runs[-1]["min_dt"], snap.timestep)
            else:
                runs.append({
                    "part": snap.controlling_part, "elem": snap.controlling_element,
                    "elem_type": snap.controlling_element_type,
                    "start_cycle": snap.cycle, "end_cycle": snap.cycle,
                    "start_time": snap.time, "end_time": snap.time,
                    "min_dt": snap.timestep, "count": 1,
                })

        if runs:
            _w("<h2>타임스텝 제어 타임라인</h2>")
            _w("<table><thead><tr>")
            _w('<th class="r">사이클</th><th>시간 구간</th><th class="r">파트</th>')
            _w('<th class="r">요소</th><th>타입</th><th class="r">최소 dt</th><th class="r">스냅</th>')
            _w("</tr></thead><tbody>")
            for r in runs:
                _w(f'<tr><td class="r">{r["start_cycle"]:,}–{r["end_cycle"]:,}</td>')
                _w(f'<td class="mono">{r["start_time"]:.4E} – {r["end_time"]:.4E}</td>')
                _w(f'<td class="id">{r["part"]}</td><td class="r">{r["elem"]}</td>')
                _w(f'<td>{_esc(r["elem_type"])}</td><td class="r mono">{r["min_dt"]:.4E}</td>')
                _w(f'<td class="r">{r["count"]}</td></tr>')
            _w("</tbody></table>")

    # === Performance Timing ===
    if report.performance:
        _w("<h2>성능 프로파일링</h2>")
        _w("<table><thead><tr>")
        _w('<th>컴포넌트</th><th class="r">CPU (s)</th><th class="r">CPU %</th>')
        _w('<th class="r">Clock (s)</th><th class="r">Clock %</th><th style="min-width:150px">비율</th>')
        _w("</tr></thead><tbody>")
        for pt in report.performance:
            bar_w = max(2, int(pt.clock_percent * 2))
            _w(f'<tr><td>{_esc(pt.component)}</td>')
            _w(f'<td class="r mono">{pt.cpu_seconds:.2f}</td><td class="r">{pt.cpu_percent:.1f}</td>')
            _w(f'<td class="r mono">{pt.clock_seconds:.2f}</td><td class="r">{pt.clock_percent:.1f}</td>')
            _w(f'<td><div class="bar-container"><div class="bar-fill" style="width:{bar_w}%"></div></div></td></tr>')
        _w("</tbody></table>")

    # === Load Profile ===
    if report.load_profile_pct:
        entries = report.load_profile_pct
        _w(f"<h2>부하 프로파일 요약 ({len(entries)}개 프로세서)</h2>")
        components = [
            ("솔리드", "solids"), ("쉘", "shells"), ("접촉", "contact"),
            ("Force 공유", "force_shr"), ("Timestep 공유", "tstep_shr"),
            ("Element 공유", "elmnt_shr"), ("Switch 공유", "swtch_shr"),
            ("바이너리 DB", "e_other"), ("강체", "rigid_bdy"),
            ("기타", "others"),
        ]
        _w("<table><thead><tr>")
        _w('<th>컴포넌트</th><th class="r">최소 %</th><th class="r">최대 %</th><th class="r">평균 %</th><th class="r">편차</th>')
        _w("</tr></thead><tbody>")
        for label, attr in components:
            values = [getattr(e, attr) for e in entries]
            if not values or max(values) == 0:
                continue
            mn, mx = min(values), max(values)
            mean = sum(values) / len(values)
            rng = mx - mn
            rng_cls = ' class="warn-high"' if rng > 8 else ""
            _w(f'<tr><td>{label}</td><td class="r">{mn:.1f}</td><td class="r">{mx:.1f}</td>')
            _w(f'<td class="r">{mean:.1f}</td><td class="r"{rng_cls}>{rng:.1f}</td></tr>')
        _w("</tbody></table>")

    # === MPI Scaling Projection ===
    if report.scaling_projections:
        _w("<h2>MPI 스케일링 예측</h2>")
        _w("<table><thead><tr>")
        _w('<th class="r">코어 수</th><th class="r">예상 시간 (s)</th><th class="r">속도향상</th><th class="r">효율</th><th class="r">통신 비율</th>')
        _w("</tr></thead><tbody>")
        for sp in report.scaling_projections:
            is_current = (sp.target_cores == report.header.num_procs)
            label = f"{sp.target_cores}" + (" (현재)" if is_current else "")
            if sp.est_efficiency < 50:
                eff_cls = ' class="eff-bad"'
            elif sp.est_efficiency < 70:
                eff_cls = ' class="eff-mid"'
            else:
                eff_cls = ""
            _w(f'<tr><td class="r">{label}</td><td class="r">{sp.est_elapsed_seconds:.0f}</td>')
            _w(f'<td class="r">{sp.est_speedup:.1f}x</td><td class="r"{eff_cls}>{sp.est_efficiency:.0f}%</td>')
            _w(f'<td class="r">{sp.est_sharing_pct:.0f}%</td></tr>')
        _w("</tbody></table>")

    # === Contact Interface Timing (Top 10) ===
    if report.contact_timing:
        _w("<h2>접촉 인터페이스 타이밍 (상위 10)</h2>")
        title_lookup = {cd.contact_id: cd.title for cd in report.contact_definitions}
        sorted_ct = sorted(report.contact_timing, key=lambda x: x.clock_seconds, reverse=True)

        _w("<table><thead><tr>")
        _w('<th class="r">인터페이스 ID</th><th>제목</th><th class="r">Clock (s)</th><th class="r">Clock %</th>')
        _w("</tr></thead><tbody>")
        for ct in sorted_ct[:10]:
            title = title_lookup.get(ct.interface_id, "")
            _w(f'<tr><td class="id">{ct.interface_id}</td><td>{_esc(title[:40])}</td>')
            _w(f'<td class="r mono">{ct.clock_seconds:.4f}</td><td class="r">{ct.clock_percent:.2f}</td></tr>')
        _w("</tbody></table>")

    # === Contact Profile (per-interface across procs) ===
    if report.cont_profile_abs:
        entries = report.cont_profile_abs
        all_ids: set[int] = set()
        for e in entries:
            all_ids.update(e.interface_timings.keys())

        if all_ids:
            title_lookup = {cd.contact_id: cd.title for cd in report.contact_definitions}
            _w("<h2>접촉 프로파일 (인터페이스별 프로세서 분포)</h2>")
            _w("<table><thead><tr>")
            _w('<th class="r">인터페이스</th><th>제목</th><th class="r">최소 (s)</th><th class="r">최대 (s)</th><th class="r">평균 (s)</th><th class="r">불균형</th>')
            _w("</tr></thead><tbody>")
            for intf_id in sorted(all_ids):
                values = [e.interface_timings.get(intf_id, 0) for e in entries]
                values = [v for v in values if v > 0]
                if not values:
                    continue
                mn, mx = min(values), max(values)
                mean = sum(values) / len(values)
                imbal = (mx - mn) / mean * 100 if mean > 0 else 0
                imbal_cls = ' class="warn-high"' if imbal > 20 else ""
                title = title_lookup.get(intf_id, "")
                _w(f'<tr><td class="id">{intf_id}</td><td>{_esc(title[:30])}</td>')
                _w(f'<td class="r mono">{mn:.2f}</td><td class="r mono">{mx:.2f}</td><td class="r mono">{mean:.2f}</td>')
                _w(f'<td class="r"{imbal_cls}>{imbal:.0f}%</td></tr>')
            _w("</tbody></table>")

    # === MPP Load Balance ===
    if report.mpp_timing:
        _w("<h2>MPP 부하 균형</h2>")
        _w("<table><thead><tr>")
        _w('<th class="r">프로세서</th><th>호스트명</th><th class="r">CPU/평균</th><th class="r">CPU (s)</th>')
        _w("</tr></thead><tbody>")
        for m in report.mpp_timing:
            ratio_cls = ""
            if m.cpu_ratio > 1.05:
                ratio_cls = ' class="eff-bad"'
            elif m.cpu_ratio < 0.95:
                ratio_cls = ' class="eff-mid"'
            _w(f'<tr><td class="id">{m.processor_id}</td><td>{_esc(m.hostname)}</td>')
            _w(f'<td class="r"{ratio_cls}>{m.cpu_ratio:.5f}</td><td class="r">{m.cpu_seconds:.2f}</td></tr>')
        _w("</tbody></table>")

    # === Memory Per Rank ===
    if report.memory_per_rank and any(m > 0 for m in report.memory_per_rank):
        mem_list = report.memory_per_rank
        min_mem = min(m for m in mem_list if m > 0)
        max_mem = max(mem_list)
        avg_mem = sum(mem_list) / len(mem_list)
        max_rank = mem_list.index(max_mem)
        _w(f'<div class="note">메모리 (최대 d-words): 최소={min_mem:,} 최대={max_mem:,} '
           f'(~{max_mem * 8 / 1024 / 1024:.0f} MB) 평균={avg_mem:,.0f} '
           f'| 피크 랭크: #{max_rank}</div>')

    # === Interface Surface Timesteps ===
    if report.interface_surface_timesteps:
        active = [s for s in report.interface_surface_timesteps if s.is_active]
        if active:
            active_sorted = sorted(active, key=lambda s: s.surface_timestep)
            _w("<h2>접촉 서프스 타임스텝</h2>")
            if report.contact_dt_limit > 0:
                _w(f'<div class="warn">접촉 안정성 dt 상한: {report.contact_dt_limit:.3E} '
                   f'— 이 값을 초과하면 접촉 불안정 발생 가능</div>')
            _w("<table><thead><tr>")
            _w('<th class="r">인터페이스</th><th class="c">서프스</th><th>타입</th>')
            _w('<th class="r">서프스 dt</th><th class="r">제어 노드</th><th class="r">파트 ID</th>')
            _w("</tr></thead><tbody>")
            for s in active_sorted:
                dt_cls = ' class="r mono critical"' if s.surface_timestep < 5e-8 else ' class="r mono"'
                _w(f'<tr><td class="id">{s.interface_id}</td><td class="c">{_esc(s.surface)}</td>')
                _w(f'<td>{_esc(s.type_code)}</td>')
                _w(f'<td{dt_cls}>{s.surface_timestep:.3E}</td>')
                _w(f'<td class="r">{s.controlling_node_id}</td><td class="r">{s.part_id}</td></tr>')
            _w("</tbody></table>")

    # === Decomposition Metrics ===
    if report.decomp_metrics and report.decomp_metrics.min_cost > 0:
        dm = report.decomp_metrics
        ratio = dm.max_cost / dm.min_cost
        ratio_cls = ' class="critical"' if ratio > 1.05 else ''
        _w("<h2>Decomposition 부하 분포</h2>")
        _w(f'<div class="note">Min cost={dm.min_cost:.6f} | Max cost={dm.max_cost:.6f} | '
           f'StdDev={dm.std_deviation:.6f} | '
           f'Max/Min 비율: <span{ratio_cls}>{ratio:.5f}</span></div>')

    # === Mass Properties ===
    if report.mass_properties:
        _w("<h2>파트별 질량 특성</h2>")
        _w("<table><thead><tr>")
        _w('<th class="r">파트 ID</th><th class="r">총 질량</th>')
        _w('<th class="r">CG-X</th><th class="r">CG-Y</th><th class="r">CG-Z</th>')
        _w('<th class="r">I11</th><th class="r">I22</th><th class="r">I33</th><th class="r">I비율</th>')
        _w("</tr></thead><tbody>")
        for mp in report.mass_properties:
            i_vals = [mp.i11, mp.i22, mp.i33]
            i_min = min(i_vals)
            i_max = max(i_vals)
            ratio = (i_max / i_min) if i_min > 0 else 0.0
            ratio_cls = ' class="r mono critical"' if ratio > 100 else ' class="r mono"'
            _w(f'<tr><td class="id">{mp.part_id}</td><td class="r mono">{_fmt_sci(mp.total_mass)}</td>')
            _w(f'<td class="r mono">{_fmt_sci(mp.cx)}</td><td class="r mono">{_fmt_sci(mp.cy)}</td>')
            _w(f'<td class="r mono">{_fmt_sci(mp.cz)}</td>')
            _w(f'<td class="r mono">{_fmt_sci(mp.i11)}</td><td class="r mono">{_fmt_sci(mp.i22)}</td>')
            _w(f'<td class="r mono">{_fmt_sci(mp.i33)}</td><td{ratio_cls}>{ratio:.0f}x</td></tr>')
        _w("</tbody></table>")

    # === Part Definitions ===
    if report.parts:
        _w("<h2>파트 정의</h2>")
        _w("<table><thead><tr>")
        _w('<th class="r">ID</th><th>이름</th><th class="c">재료 타입</th><th>재료명</th>')
        _w('<th class="r">밀도</th><th class="r">탄성계수 (E)</th><th class="r">포아송비 (ν)</th><th class="c">ELFORM</th>')
        _w("</tr></thead><tbody>")
        for p in report.parts:
            _w(f'<tr><td class="id">{p.part_id}</td><td>{_esc(p.name[:25])}</td>')
            _w(f'<td class="c">{p.material_type}</td><td>{_esc(p.material_type_name[:25])}</td>')
            _w(f'<td class="r mono">{_fmt_sci(p.density)}</td><td class="r mono">{_fmt_sci(p.youngs_modulus)}</td>')
            nu_str = f"{p.poisson_ratio:.2f}" if p.poisson_ratio > 0 else ""
            ef_str = str(p.solid_formulation) if p.solid_formulation > 0 else ""
            _w(f'<td class="r">{nu_str}</td><td class="c">{ef_str}</td></tr>')
        _w("</tbody></table>")

    # === Footer ===
    if report.files_found:
        _w(f'<div class="footer">분석 파일: {_esc(", ".join(report.files_found))}</div>')

    _w("</body></html>")

    filepath.write_text("\n".join(parts), encoding="utf-8")
