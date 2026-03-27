"""Pure SVG chart generator for LS-DYNA energy/force time series.

No external dependencies — generates self-contained SVG strings
that embed directly into HTML reports.
"""

import math
from dataclasses import dataclass


@dataclass
class Series:
    """One data series for a line chart."""
    name: str
    values: list[tuple[float, float]]  # [(x, y), ...]
    color: str = "#4fc3f7"
    dash: str = ""  # e.g. "6,3" for dashed


def _nice_ticks(vmin: float, vmax: float, n: int = 5) -> list[float]:
    """Generate human-friendly tick values."""
    if not math.isfinite(vmin) or not math.isfinite(vmax):
        return [0.0]
    if vmax <= vmin:
        return [vmin]
    raw = (vmax - vmin) / max(n - 1, 1)
    if raw == 0 or not math.isfinite(raw):
        return [vmin]
    mag = 10 ** math.floor(math.log10(abs(raw)))
    norm = raw / mag
    if norm <= 1.5:
        step = 1.0 * mag
    elif norm <= 3.5:
        step = 2.0 * mag
    elif norm <= 7.5:
        step = 5.0 * mag
    else:
        step = 10.0 * mag
    start = math.floor(vmin / step) * step
    ticks = []
    v = start
    while v <= vmax + step * 0.01:
        ticks.append(v)
        v += step
    return ticks


def _fmt_tick(v: float) -> str:
    """Format tick label smartly."""
    if v == 0:
        return "0"
    av = abs(v)
    if av >= 1e6 or av < 1e-2:
        return f"{v:.2E}"
    if av >= 100:
        return f"{v:.0f}"
    if av >= 1:
        return f"{v:.1f}"
    return f"{v:.3f}"


def _fmt_time(v: float) -> str:
    """Format time axis label."""
    if v == 0:
        return "0"
    av = abs(v)
    if av >= 1e-1:
        return f"{v:.2f}"
    if av >= 1e-3:
        return f"{v:.4f}"
    return f"{v:.2E}"


def make_line_chart(
    series_list: list[Series],
    title: str = "",
    x_label: str = "Time",
    y_label: str = "",
    width: int = 800,
    height: int = 320,
    chart_id: str = "chart",
) -> str:
    """Generate an SVG line chart string.

    Returns a complete <svg> element as a string.
    """
    if not series_list or all(len(s.values) == 0 for s in series_list):
        return ""

    # Margins
    ml, mr, mt, mb = 80, 20, 35, 50
    legend_h = 25
    pw = width - ml - mr
    ph = height - mt - mb - legend_h

    # Filter out non-finite values
    for s in series_list:
        s.values = [(x, y) for x, y in s.values if math.isfinite(x) and math.isfinite(y)]
    series_list = [s for s in series_list if s.values]
    if not series_list:
        return ""

    # Data bounds
    all_x = [x for s in series_list for x, _ in s.values]
    all_y = [y for s in series_list for _, y in s.values]
    xmin, xmax = min(all_x), max(all_x)
    ymin, ymax = min(all_y), max(all_y)

    # Expand range slightly
    if ymin == ymax:
        ymin -= 1
        ymax += 1
    yr = ymax - ymin
    ymin -= yr * 0.05
    ymax += yr * 0.05
    if xmin == xmax:
        xmax = xmin + 1

    # Ticks
    x_ticks = _nice_ticks(xmin, xmax, 6)
    y_ticks = _nice_ticks(ymin, ymax, 6)

    def sx(v: float) -> float:
        return ml + (v - xmin) / (xmax - xmin) * pw

    def sy(v: float) -> float:
        return mt + ph - (v - ymin) / (ymax - ymin) * ph

    parts: list[str] = []
    _w = parts.append

    _w(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
       f'width="{width}" height="{height}" id="{chart_id}" '
       f'style="background:#1a1b26;border-radius:6px;margin:8px 0;">')

    # Grid lines
    for yt in y_ticks:
        y = sy(yt)
        if mt <= y <= mt + ph:
            _w(f'<line x1="{ml}" y1="{y:.1f}" x2="{ml+pw}" y2="{y:.1f}" '
               f'stroke="#2a2b3d" stroke-width="1"/>')
    for xt in x_ticks:
        x = sx(xt)
        if ml <= x <= ml + pw:
            _w(f'<line x1="{x:.1f}" y1="{mt}" x2="{x:.1f}" y2="{mt+ph}" '
               f'stroke="#2a2b3d" stroke-width="1"/>')

    # Axes
    _w(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="#565f89" stroke-width="1"/>')
    _w(f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="#565f89" stroke-width="1"/>')

    # Y-axis ticks & labels
    for yt in y_ticks:
        y = sy(yt)
        if mt <= y <= mt + ph:
            _w(f'<text x="{ml-6}" y="{y+3:.1f}" text-anchor="end" '
               f'fill="#787c99" font-size="10" font-family="monospace">{_fmt_tick(yt)}</text>')

    # X-axis ticks & labels
    for xt in x_ticks:
        x = sx(xt)
        if ml <= x <= ml + pw:
            _w(f'<text x="{x:.1f}" y="{mt+ph+16}" text-anchor="middle" '
               f'fill="#787c99" font-size="10" font-family="monospace">{_fmt_time(xt)}</text>')

    # Axis labels
    if x_label:
        _w(f'<text x="{ml+pw/2}" y="{mt+ph+38}" text-anchor="middle" '
           f'fill="#9aa5ce" font-size="11" font-family="sans-serif">{x_label}</text>')
    if y_label:
        _w(f'<text x="14" y="{mt+ph/2}" text-anchor="middle" '
           f'fill="#9aa5ce" font-size="11" font-family="sans-serif" '
           f'transform="rotate(-90,14,{mt+ph/2})">{y_label}</text>')

    # Title
    if title:
        _w(f'<text x="{ml+pw/2}" y="{mt-12}" text-anchor="middle" '
           f'fill="#c0caf5" font-size="13" font-weight="bold" font-family="sans-serif">{title}</text>')

    # Clip area
    _w(f'<clipPath id="clip-{chart_id}"><rect x="{ml}" y="{mt}" width="{pw}" height="{ph}"/></clipPath>')

    # Data lines
    for s in series_list:
        if len(s.values) < 2:
            continue
        # Downsample if too many points (SVG becomes huge)
        pts = s.values
        if len(pts) > 500:
            step = len(pts) // 500
            pts = pts[::step]
            if pts[-1] != s.values[-1]:
                pts.append(s.values[-1])

        points = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in pts)
        dash_attr = f' stroke-dasharray="{s.dash}"' if s.dash else ""
        _w(f'<polyline points="{points}" fill="none" stroke="{s.color}" '
           f'stroke-width="1.5" clip-path="url(#clip-{chart_id})"{dash_attr}/>')

    # Legend
    lx = ml + 10
    ly = mt + ph + legend_h + 18
    for i, s in enumerate(series_list):
        x_off = lx + i * (pw // len(series_list))
        dash_attr = f' stroke-dasharray="{s.dash}"' if s.dash else ""
        _w(f'<line x1="{x_off}" y1="{ly-4}" x2="{x_off+20}" y2="{ly-4}" '
           f'stroke="{s.color}" stroke-width="2"{dash_attr}/>')
        _w(f'<text x="{x_off+24}" y="{ly}" fill="#a9b1d6" font-size="10" '
           f'font-family="sans-serif">{s.name}</text>')

    _w('</svg>')
    return "\n".join(parts)


def make_energy_charts(snapshots) -> str:
    """Generate energy time-series charts from EnergySnapshot list.

    Returns HTML string containing multiple SVG charts.
    """
    if not snapshots or len(snapshots) < 2:
        return ""

    parts: list[str] = []

    # Chart 1: Major energy components (KE, IE, HG, Total)
    ke = [(s.time, s.kinetic) for s in snapshots]
    ie = [(s.time, s.internal) for s in snapshots]
    hg = [(s.time, s.hourglass) for s in snapshots]
    total = [(s.time, s.total) for s in snapshots]

    chart1 = make_line_chart(
        [
            Series("Total Energy", total, "#c0caf5"),
            Series("Internal Energy", ie, "#9ece6a"),
            Series("Kinetic Energy", ke, "#f7768e"),
            Series("Hourglass Energy", hg, "#ff9e64", dash="4,2"),
        ],
        title="Energy Components",
        x_label="Time (s)",
        y_label="Energy",
        chart_id="energy-components",
    )
    if chart1:
        parts.append(chart1)

    # Chart 2: Contact sliding + External work
    slide = [(s.time, s.sliding_interface) for s in snapshots]
    ext = [(s.time, s.external_work) for s in snapshots]

    has_slide = any(abs(y) > 1e-30 for _, y in slide)
    has_ext = any(abs(y) > 1e-30 for _, y in ext)
    if has_slide or has_ext:
        series2 = []
        if has_ext:
            series2.append(Series("External Work", ext, "#bb9af7"))
        if has_slide:
            series2.append(Series("Sliding Interface", slide, "#e0af68"))

        chart2 = make_line_chart(
            series2,
            title="External Work & Contact Energy",
            x_label="Time (s)",
            y_label="Energy",
            chart_id="energy-ext-slide",
        )
        if chart2:
            parts.append(chart2)

    # Chart 3: Energy ratio
    ratio = [(s.time, s.energy_ratio) for s in snapshots if not s.has_nan]
    if len(ratio) >= 2:
        chart3 = make_line_chart(
            [Series("Energy Ratio (Total/Initial)", ratio, "#7dcfff")],
            title="Energy Ratio",
            x_label="Time (s)",
            y_label="Ratio",
            chart_id="energy-ratio",
        )
        if chart3:
            parts.append(chart3)

    # Chart 4: Timestep
    dt = [(s.time, s.timestep) for s in snapshots if s.timestep > 0]
    if len(dt) >= 2:
        chart4 = make_line_chart(
            [Series("Timestep (dt)", dt, "#73daca")],
            title="Timestep History",
            x_label="Time (s)",
            y_label="dt (s)",
            chart_id="timestep-history",
        )
        if chart4:
            parts.append(chart4)

    return "\n".join(parts)


def make_rcforc_charts(interfaces: dict, max_charts: int = 10) -> str:
    """Generate contact force time-series charts from rcforc data.

    Args:
        interfaces: dict[int, RcforcInterface] — interface_id → data
        max_charts: max number of interface charts to render

    Returns HTML string containing SVG charts.
    """
    if not interfaces:
        return ""

    parts: list[str] = []

    # Summary chart: resultant force magnitude for top interfaces
    # Sort by max force magnitude
    ranked = []
    for iid, iface in interfaces.items():
        if not iface.surfa_forces:
            continue
        max_mag = 0.0
        for snap in iface.surfa_forces:
            mag = (snap.fx**2 + snap.fy**2 + snap.fz**2) ** 0.5
            if mag > max_mag:
                max_mag = mag
        ranked.append((iid, iface, max_mag))
    ranked.sort(key=lambda x: x[2], reverse=True)

    if not ranked:
        return ""

    # Overall chart: top N interfaces resultant force
    top = ranked[:max_charts]
    colors = [
        "#f7768e", "#ff9e64", "#e0af68", "#9ece6a", "#73daca",
        "#7dcfff", "#7aa2f7", "#bb9af7", "#c0caf5", "#a9b1d6",
    ]

    summary_series = []
    for i, (iid, iface, _) in enumerate(top):
        vals = []
        for snap in iface.surfa_forces:
            mag = (snap.fx**2 + snap.fy**2 + snap.fz**2) ** 0.5
            vals.append((snap.time, mag))
        title = iface.title.strip() if iface.title else f"Interface {iid}"
        if len(title) > 25:
            title = title[:22] + "..."
        summary_series.append(Series(
            f"#{iid} {title}", vals, colors[i % len(colors)]
        ))

    chart_summary = make_line_chart(
        summary_series,
        title=f"Contact Resultant Force (Top {len(top)} Interfaces)",
        x_label="Time (s)",
        y_label="Force Magnitude",
        width=800,
        height=350,
        chart_id="rcforc-summary",
    )
    if chart_summary:
        parts.append(chart_summary)

    # Per-interface detail charts (top 5 only)
    for i, (iid, iface, _) in enumerate(top[:5]):
        fx_a = [(s.time, s.fx) for s in iface.surfa_forces]
        fy_a = [(s.time, s.fy) for s in iface.surfa_forces]
        fz_a = [(s.time, s.fz) for s in iface.surfa_forces]

        title = iface.title.strip() if iface.title else f"Interface {iid}"
        chart_detail = make_line_chart(
            [
                Series("Fx", fx_a, "#f7768e"),
                Series("Fy", fy_a, "#9ece6a"),
                Series("Fz", fz_a, "#7aa2f7"),
            ],
            title=f"Interface #{iid}: {title} (SURFA Forces)",
            x_label="Time (s)",
            y_label="Force",
            width=800,
            height=280,
            chart_id=f"rcforc-detail-{iid}",
        )
        if chart_detail:
            parts.append(chart_detail)

    return "\n".join(parts)
