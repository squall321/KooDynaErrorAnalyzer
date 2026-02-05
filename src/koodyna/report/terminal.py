"""Rich terminal output for the analysis report."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from koodyna.models import Report, Severity, TerminationStatus


def _severity_style(severity: Severity) -> str:
    if severity == Severity.CRITICAL:
        return "bold red"
    elif severity == Severity.WARNING:
        return "bold yellow"
    return "bold blue"


def _severity_icon(severity: Severity) -> str:
    if severity == Severity.CRITICAL:
        return "[심각]"
    elif severity == Severity.WARNING:
        return "[경고]"
    return "[정보]"


def _fmt_sci(value: float) -> str:
    if value == 0.0:
        return "0"
    if abs(value) < 1e-3 or abs(value) > 1e6:
        return f"{value:.4E}"
    return f"{value:.4f}"


# Contact type code resolution
_CONTACT_TYPE_RESOLVE = {
    ("", 1): "Sliding Only",
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


def render_report(report: Report, no_color: bool = False):
    """Render the analysis report to the terminal."""
    console = Console(force_terminal=not no_color, highlight=False)

    # === Header ===
    header = report.header
    header_text = (
        f"Version: {header.version} | Revision: {header.revision}\n"
        f"Date: {header.date} {header.time} | Host: {header.hostname}\n"
        f"Input: {header.input_file} | Precision: {header.precision}\n"
        f"Platform: {header.platform} | MPP: {header.num_procs} procs\n"
        f"Licensee: {header.licensee}"
    )
    console.print(Panel(header_text, title="LS-DYNA 해석 분석", border_style="blue"))

    # === Model Size ===
    ms = report.model_size
    model_table = Table(title="모델 요약", show_header=False, border_style="dim")
    model_table.add_column("항목", style="cyan")
    model_table.add_column("값", justify="right")
    model_table.add_row("노드", f"{ms.num_nodes:,}")
    model_table.add_row("솔리드 요소", f"{ms.num_solid_elements:,}")
    model_table.add_row("쉘 요소", f"{ms.num_shell_elements:,}")
    model_table.add_row("빔 요소", f"{ms.num_beam_elements:,}")
    model_table.add_row("파트", f"{ms.num_parts:,}")
    model_table.add_row("재료", f"{ms.num_materials:,}")
    model_table.add_row("접촉", f"{ms.num_contacts:,}")
    model_table.add_row("SPC 노드", f"{ms.num_spc_nodes:,}")
    console.print(model_table)

    # === Termination Status ===
    term = report.termination
    if term.status == TerminationStatus.NORMAL:
        term_style = "bold green"
        term_label = "정상 종료"
    elif term.status == TerminationStatus.ERROR:
        term_style = "bold red"
        term_label = "오류 종료"
    else:
        term_style = "bold yellow"
        term_label = "미완료 (출력 중단)"

    term_text = (
        f"Status: [{term_style}]{term_label}[/{term_style}]\n"
        f"목표 시간: {_fmt_sci(term.target_time)} | "
        f"도달 시간: {_fmt_sci(term.actual_time)}\n"
        f"사이클: {term.total_cycles:,} | "
        f"CPU: {term.total_cpu_seconds:.0f}초 | "
        f"경과: {term.elapsed_seconds:.0f}초\n"
        f"CPU/zone-cycle: {term.cpu_per_zone_cycle_ns:.1f} ns | "
        f"Clock/zone-cycle: {term.clock_per_zone_cycle_ns:.1f} ns"
    )
    if term.start_datetime:
        term_text += f"\n시작: {term.start_datetime} | 종료: {term.end_datetime}"
    console.print(Panel(term_text, title="종료 상태", border_style="cyan"))

    # === Findings ===
    if report.findings:
        critical_count = sum(1 for f in report.findings if f.severity == Severity.CRITICAL)
        warning_count = sum(1 for f in report.findings if f.severity == Severity.WARNING)
        info_count = sum(1 for f in report.findings if f.severity == Severity.INFO)

        summary = (
            f"[bold red]{critical_count} 심각[/bold red] | "
            f"[bold yellow]{warning_count} 경고[/bold yellow] | "
            f"[bold blue]{info_count} 정보[/bold blue]"
        )
        console.print(Panel(summary, title=f"진단 결과 (총 {len(report.findings)}건)"))

        for finding in report.findings:
            style = _severity_style(finding.severity)
            icon = _severity_icon(finding.severity)
            console.print(f"  [{style}]{icon}[/{style}] {finding.title}")
            if finding.description:
                console.print(f"    [dim]{finding.description}[/dim]")
            if finding.recommendation:
                console.print(f"    [italic]>> {finding.recommendation}[/italic]")
            console.print()
    else:
        console.print("[green]발견된 문제 없음.[/green]")

    # === Warning Summary ===
    if report.warnings:
        warn_table = Table(title="경고/오류 요약", border_style="yellow")
        warn_table.add_column("코드", justify="right", style="cyan")
        warn_table.add_column("횟수", justify="right")
        warn_table.add_column("심각도", justify="center")
        warn_table.add_column("설명")
        warn_table.add_column("인터페이스")

        for w in report.warnings[:20]:
            sev_style = _severity_style(w.severity)
            intf_str = ""
            if w.affected_interfaces:
                intf_list = w.affected_interfaces[:8]
                intf_str = ", ".join(str(i) for i in intf_list)
                if len(w.affected_interfaces) > 8:
                    intf_str += f" (+{len(w.affected_interfaces)-8})"
            warn_table.add_row(
                str(w.code),
                f"{w.count:,}",
                f"[{sev_style}]{w.severity.value}[/{sev_style}]",
                w.message[:60] if w.message else "",
                intf_str,
            )
        console.print(warn_table)

    # === Contact Definitions + Per-Interface Warnings ===
    if report.contact_definitions:
        cd_table = Table(title="접촉 인터페이스 요약", border_style="red")
        cd_table.add_column("ID", justify="right", style="cyan")
        cd_table.add_column("타입")
        cd_table.add_column("제목")
        cd_table.add_column("경고 수", justify="right")
        cd_table.add_column("Clock (s)", justify="right")
        cd_table.add_column("Clock %", justify="right")

        # Build lookup dicts
        ct_lookup = {ct.interface_id: ct for ct in report.contact_timing}
        warn_lookup = report.interface_warning_counts

        for cd in report.contact_definitions:
            type_name = _CONTACT_TYPE_RESOLVE.get(
                (cd.type_prefix, cd.type_number), f"{cd.type_code}"
            )
            warn_count = warn_lookup.get(cd.contact_id, 0)
            warn_str = f"[bold yellow]{warn_count:,}[/bold yellow]" if warn_count > 100 else (
                f"{warn_count:,}" if warn_count > 0 else ""
            )
            ct = ct_lookup.get(cd.contact_id)
            clock_str = f"{ct.clock_seconds:.4f}" if ct else ""
            pct_str = f"{ct.clock_percent:.2f}" if ct else ""

            cd_table.add_row(
                str(cd.contact_id), type_name,
                cd.title[:30], warn_str, clock_str, pct_str,
            )
        console.print(cd_table)

    # === Energy Summary ===
    energy = report.energy
    if energy.snapshots:
        e_table = Table(title="에너지 수지 요약", border_style="green")
        e_table.add_column("항목", style="cyan")
        e_table.add_column("초기값", justify="right")
        e_table.add_column("최종값", justify="right")

        initial = energy.snapshots[0]
        final = energy.snapshots[-1]

        for label, i_val, f_val in [
            ("운동 에너지", initial.kinetic, final.kinetic),
            ("내부 에너지", initial.internal, final.internal),
            ("Hourglass 에너지", initial.hourglass, final.hourglass),
            ("슬라이딩 인터페이스", initial.sliding_interface, final.sliding_interface),
            ("총 에너지", initial.total, final.total),
            ("에너지 비율", initial.energy_ratio, final.energy_ratio),
        ]:
            e_table.add_row(label, _fmt_sci(i_val), _fmt_sci(f_val))

        e_table.add_row(
            "최대 HG/내부에너지 비율",
            "",
            f"{energy.max_hourglass_ratio:.1%}",
        )
        console.print(e_table)

    # === Timestep Summary ===
    ts = report.timestep
    if ts.smallest_timesteps:
        # Table 1: Element-level detail (top 20)
        sorted_entries = sorted(ts.smallest_timesteps, key=lambda e: e.timestep)
        elem_table = Table(title="최소 타임스텝 요소 (상위 20개)", border_style="magenta")
        elem_table.add_column("#", justify="right", style="dim")
        elem_table.add_column("타입")
        elem_table.add_column("요소 ID", justify="right", style="cyan")
        elem_table.add_column("파트", justify="right")
        elem_table.add_column("dt", justify="right")

        for i, entry in enumerate(sorted_entries[:20], 1):
            elem_table.add_row(
                str(i), entry.element_type, str(entry.element_number),
                str(entry.part_number), f"{entry.timestep:.4E}",
            )
        console.print(elem_table)

        # Table 2: Part summary (condensed)
        part_info: dict[int, dict] = {}
        for entry in ts.smallest_timesteps:
            if entry.part_number not in part_info:
                part_info[entry.part_number] = {
                    "count": 0, "min_dt": entry.timestep,
                    "max_dt": entry.timestep, "elem_type": entry.element_type,
                }
            pi = part_info[entry.part_number]
            pi["count"] += 1
            if entry.timestep < pi["min_dt"]:
                pi["min_dt"] = entry.timestep
            if entry.timestep > pi["max_dt"]:
                pi["max_dt"] = entry.timestep

        ps_table = Table(title="파트별 타임스텝 요약 (100 최소)", border_style="magenta", show_header=True)
        ps_table.add_column("파트", justify="right", style="cyan")
        ps_table.add_column("개수", justify="right")
        ps_table.add_column("최소 dt", justify="right")
        ps_table.add_column("최대 dt", justify="right")
        ps_table.add_column("타입")
        for part_id, info in sorted(part_info.items(), key=lambda x: x[1]["min_dt"]):
            ps_table.add_row(
                str(part_id), str(info["count"]),
                f"{info['min_dt']:.4E}", f"{info['max_dt']:.4E}", info["elem_type"],
            )
        console.print(ps_table)

        console.print(
            f"  [dim]TSSFAC: {ts.dt_scale_factor} | "
            f"초기 dt: {_fmt_sci(ts.initial_dt)} | "
            f"최종 dt: {_fmt_sci(ts.final_dt)}[/dim]"
        )

    # === Timestep Control Timeline (from glstat) ===
    snapshots = report.energy.snapshots
    if snapshots and snapshots[0].controlling_part > 0:
        # Compress consecutive runs with same controlling element
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
                    "part": snap.controlling_part,
                    "elem": snap.controlling_element,
                    "elem_type": snap.controlling_element_type,
                    "start_cycle": snap.cycle,
                    "end_cycle": snap.cycle,
                    "start_time": snap.time,
                    "end_time": snap.time,
                    "min_dt": snap.timestep,
                    "count": 1,
                })

        if runs:
            tl_table = Table(title="타임스텝 제어 타임라인", border_style="magenta")
            tl_table.add_column("사이클", justify="right")
            tl_table.add_column("시간 구간")
            tl_table.add_column("파트", justify="right", style="cyan")
            tl_table.add_column("요소", justify="right")
            tl_table.add_column("타입")
            tl_table.add_column("최소 dt", justify="right")
            tl_table.add_column("스냅", justify="right", style="dim")

            for r in runs:
                tl_table.add_row(
                    f"{r['start_cycle']:,}-{r['end_cycle']:,}",
                    f"{r['start_time']:.4E} - {r['end_time']:.4E}",
                    str(r["part"]),
                    str(r["elem"]),
                    r["elem_type"],
                    f"{r['min_dt']:.4E}",
                    str(r["count"]),
                )
            console.print(tl_table)

    # === Performance Timing ===
    if report.performance:
        perf_table = Table(title="성능 프로파일링", border_style="blue")
        perf_table.add_column("컴포넌트", style="cyan")
        perf_table.add_column("CPU (s)", justify="right")
        perf_table.add_column("CPU %", justify="right")
        perf_table.add_column("Clock (s)", justify="right")
        perf_table.add_column("Clock %", justify="right")
        perf_table.add_column("비율", min_width=20)

        for pt in report.performance:
            bar_len = int(pt.clock_percent / 2)
            bar = "[green]" + "#" * bar_len + "[/green]"
            perf_table.add_row(
                pt.component,
                f"{pt.cpu_seconds:.2f}",
                f"{pt.cpu_percent:.1f}",
                f"{pt.clock_seconds:.2f}",
                f"{pt.clock_percent:.1f}",
                bar,
            )
        console.print(perf_table)

    # === Load Profile Summary ===
    if report.load_profile_pct:
        _render_load_profile(console, report)

    # === MPI Scaling Projections ===
    if report.scaling_projections:
        sp_table = Table(title="MPI 스케일링 예측", border_style="blue")
        sp_table.add_column("코어 수", justify="right", style="cyan")
        sp_table.add_column("예상 시간 (s)", justify="right")
        sp_table.add_column("속도향상", justify="right")
        sp_table.add_column("효율", justify="right")
        sp_table.add_column("통신 비율", justify="right")

        for sp in report.scaling_projections:
            eff_style = ""
            if sp.est_efficiency < 50:
                eff_style = "bold red"
            elif sp.est_efficiency < 70:
                eff_style = "bold yellow"
            eff_str = f"{sp.est_efficiency:.0f}%"
            if eff_style:
                eff_str = f"[{eff_style}]{eff_str}[/{eff_style}]"

            is_current = (sp.target_cores == report.header.num_procs)
            label = f"{sp.target_cores}" + (" (현재)" if is_current else "")
            sp_table.add_row(
                label,
                f"{sp.est_elapsed_seconds:.0f}",
                f"{sp.est_speedup:.1f}x",
                eff_str,
                f"{sp.est_sharing_pct:.0f}%",
            )
        console.print(sp_table)

    # === Contact Timing (Top 10) ===
    if report.contact_timing:
        ct_table = Table(title="접촉 인터페이스 타이밍 (상위 10)", border_style="red")
        ct_table.add_column("인터페이스 ID", justify="right", style="cyan")
        ct_table.add_column("제목")
        ct_table.add_column("Clock (s)", justify="right")
        ct_table.add_column("Clock %", justify="right")

        # Build title lookup from contact_definitions
        title_lookup = {cd.contact_id: cd.title for cd in report.contact_definitions}

        sorted_ct = sorted(report.contact_timing, key=lambda x: x.clock_seconds, reverse=True)
        for ct in sorted_ct[:10]:
            title = title_lookup.get(ct.interface_id, "")
            ct_table.add_row(
                str(ct.interface_id),
                title[:25],
                f"{ct.clock_seconds:.4f}",
                f"{ct.clock_percent:.2f}",
            )
        console.print(ct_table)

    # === Per-Contact Processor Timing (cont_profile) ===
    if report.cont_profile_abs:
        _render_cont_profile(console, report)

    # === MPP Balance ===
    if report.mpp_timing:
        mpp_table = Table(title="MPP 부하 균형", border_style="cyan")
        mpp_table.add_column("프로세서", justify="right", style="cyan")
        mpp_table.add_column("호스트명")
        mpp_table.add_column("CPU/평균", justify="right")
        mpp_table.add_column("CPU (s)", justify="right")

        for m in report.mpp_timing:
            ratio_style = ""
            if m.cpu_ratio > 1.05:
                ratio_style = "bold red"
            elif m.cpu_ratio < 0.95:
                ratio_style = "bold yellow"
            mpp_table.add_row(
                str(m.processor_id),
                m.hostname,
                f"[{ratio_style}]{m.cpu_ratio:.5f}[/{ratio_style}]" if ratio_style else f"{m.cpu_ratio:.5f}",
                f"{m.cpu_seconds:.2f}",
            )
        console.print(mpp_table)

    # === Memory Per Rank ===
    if report.memory_per_rank and any(m > 0 for m in report.memory_per_rank):
        mem_list = report.memory_per_rank
        min_mem = min(m for m in mem_list if m > 0)
        max_mem = max(mem_list)
        avg_mem = sum(mem_list) / len(mem_list)
        max_rank = mem_list.index(max_mem)
        # Convert d-words to MB (8 bytes per d-word)
        console.print(
            f"  [dim]메모리 (최대 d-words): 최소={min_mem:,} 최대={max_mem:,} "
            f"(~{max_mem * 8 / 1024 / 1024:.0f} MB) 평균={avg_mem:,.0f} "
            f"| 피크 랭크: #{max_rank}[/dim]"
        )

    # === Part Summary ===
    if report.parts:
        part_table = Table(title="파트 정의", border_style="dim")
        part_table.add_column("ID", justify="right", style="cyan")
        part_table.add_column("이름")
        part_table.add_column("재료 타입", justify="center")
        part_table.add_column("재료명")
        part_table.add_column("밀도", justify="right")
        part_table.add_column("탄성계수", justify="right")
        part_table.add_column("포아송비", justify="right")
        part_table.add_column("ELFORM", justify="center")

        for p in report.parts:
            part_table.add_row(
                str(p.part_id),
                p.name[:20] if p.name else "",
                str(p.material_type),
                p.material_type_name[:20],
                _fmt_sci(p.density),
                _fmt_sci(p.youngs_modulus),
                f"{p.poisson_ratio:.2f}" if p.poisson_ratio > 0 else "",
                str(p.solid_formulation) if p.solid_formulation > 0 else "",
            )
        console.print(part_table)

    # === Files Found ===
    if report.files_found:
        console.print(
            f"\n[dim]분석 파일: {', '.join(report.files_found)}[/dim]"
        )


def _render_load_profile(console: Console, report: Report):
    """Render load profile summary across processors."""
    entries = report.load_profile_pct
    if not entries:
        return

    # Component names and their attribute names
    components = [
        ("솔리드", "solids"), ("쉘", "shells"), ("접촉", "contact"),
        ("Force 공유", "force_shr"), ("Timestep 공유", "tstep_shr"),
        ("Element 공유", "elmnt_shr"), ("Switch 공유", "swtch_shr"),
        ("바이너리 DB", "e_other"), ("강체", "rigid_bdy"),
        ("기타", "others"),
    ]

    lp_table = Table(
        title=f"부하 프로파일 요약 ({len(entries)}개 프로세서)",
        border_style="blue",
    )
    lp_table.add_column("컴포넌트", style="cyan")
    lp_table.add_column("최소 %", justify="right")
    lp_table.add_column("최대 %", justify="right")
    lp_table.add_column("평균 %", justify="right")
    lp_table.add_column("편차", justify="right")

    for label, attr in components:
        values = [getattr(e, attr) for e in entries]
        if not values or max(values) == 0:
            continue
        mn = min(values)
        mx = max(values)
        mean = sum(values) / len(values)
        rng = mx - mn
        rng_style = ""
        if rng > 8:
            rng_style = "bold yellow"
        rng_str = f"{rng:.1f}"
        if rng_style:
            rng_str = f"[{rng_style}]{rng_str}[/{rng_style}]"
        lp_table.add_row(
            label, f"{mn:.1f}", f"{mx:.1f}", f"{mean:.1f}", rng_str,
        )
    console.print(lp_table)


def _render_cont_profile(console: Console, report: Report):
    """Render per-contact interface timing across processors."""
    entries = report.cont_profile_abs
    if not entries:
        return

    # Get all interface IDs
    all_ids: set[int] = set()
    for e in entries:
        all_ids.update(e.interface_timings.keys())

    if not all_ids:
        return

    title_lookup = {cd.contact_id: cd.title for cd in report.contact_definitions}

    cp_table = Table(title="접촉 프로파일 (인터페이스별 프로세서 분포)", border_style="red")
    cp_table.add_column("인터페이스", justify="right", style="cyan")
    cp_table.add_column("제목")
    cp_table.add_column("최소 (s)", justify="right")
    cp_table.add_column("최대 (s)", justify="right")
    cp_table.add_column("평균 (s)", justify="right")
    cp_table.add_column("불균형", justify="right")

    for intf_id in sorted(all_ids):
        values = [e.interface_timings.get(intf_id, 0) for e in entries]
        values = [v for v in values if v > 0]
        if not values:
            continue
        mn = min(values)
        mx = max(values)
        mean = sum(values) / len(values)
        imbal = (mx - mn) / mean * 100 if mean > 0 else 0
        imbal_style = "bold yellow" if imbal > 20 else ""
        imbal_str = f"{imbal:.0f}%"
        if imbal_style:
            imbal_str = f"[{imbal_style}]{imbal_str}[/{imbal_style}]"
        title = title_lookup.get(intf_id, "")
        cp_table.add_row(
            str(intf_id), title[:25],
            f"{mn:.2f}", f"{mx:.2f}", f"{mean:.2f}", imbal_str,
        )
    console.print(cp_table)
