"""Overall diagnostic engine that aggregates all analysis findings."""

from koodyna.models import (
    TerminationInfo, TerminationStatus, Finding, Severity,
    DecompMetrics, MassProperty, InterfaceSurfaceTimestep,
)


def _diagnose_contact_dt(
    contact_dt_limit: float,
    min_dt: float,
    interface_surface_timesteps: list[InterfaceSurfaceTimestep],
) -> list[Finding]:
    findings: list[Finding] = []
    if contact_dt_limit <= 0:
        return findings

    # 접촉 안정성 dt 상한 경고
    active = [s for s in interface_surface_timesteps if s.is_active]
    # 가장 작은 서프스 타임스텝
    if active:
        bottleneck = min(active, key=lambda s: s.surface_timestep)
        findings.append(Finding(
            severity=Severity.WARNING,
            category="contact",
            title=f"접촉 안정성 dt 상한: {contact_dt_limit:.3E}",
            description=(
                f"LS-DYNA 권장: dt ≤ {contact_dt_limit:.3E}. "
                f"가장 작은 서프스 dt = {bottleneck.surface_timestep:.3E} "
                f"(인터페이스 {bottleneck.interface_id}, {bottleneck.surface}, 파트 {bottleneck.part_id}). "
                f"활성 서프스 {len(active)}개 중 제어 인터페이스가 확인됨."
            ),
            recommendation="Penalty scaling 또는 해당 인터페이스의 접촉 설정을 확인하세요.",
        ))
    return findings


def _diagnose_mass_properties(mass_properties: list[MassProperty]) -> list[Finding]:
    findings: list[Finding] = []
    for mp in mass_properties:
        i_vals = [mp.i11, mp.i22, mp.i33]
        i_min = min(i_vals)
        i_max = max(i_vals)
        if i_min <= 0:
            continue
        ratio = i_max / i_min
        if ratio > 100:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="mass",
                title=f"파트 {mp.part_id}: 주관성모멘트 비율 {ratio:.0f}x (I_max/I_min > 100)",
                description=(
                    f"I11={mp.i11:.3E}, I22={mp.i22:.3E}, I33={mp.i33:.3E}. "
                    f"극단적인 관성 비율은 강체 회전 불안정성을 유발할 수 있습니다."
                ),
                recommendation="해당 파트의 기하학적 형상과 재료 설정을 검토하세요.",
            ))
    return findings


def _diagnose_decomp(decomp_metrics: DecompMetrics) -> list[Finding]:
    findings: list[Finding] = []
    if decomp_metrics.min_cost <= 0:
        return findings
    ratio = decomp_metrics.max_cost / decomp_metrics.min_cost
    if ratio > 1.05:
        findings.append(Finding(
            severity=Severity.WARNING,
            category="decomposition",
            title=f"Decomposition 부하 불균형: max/min 비율 {ratio:.3f}",
            description=(
                f"Min cost={decomp_metrics.min_cost:.6f}, "
                f"Max cost={decomp_metrics.max_cost:.6f}, "
                f"StdDev={decomp_metrics.std_deviation:.6f}. "
                f"코어 수 증가 시 스케일링 효율이 저하될 수 있습니다."
            ),
            recommendation="RCB 대신 METIS decomposition을 시도하거나, 모델 구조를 검토하세요.",
        ))
    return findings


def run_diagnostics(
    termination: TerminationInfo,
    energy_findings: list[Finding],
    timestep_findings: list[Finding],
    warning_findings: list[Finding],
    contact_findings: list[Finding],
    performance_findings: list[Finding],
    contact_dt_limit: float = 0.0,
    min_dt: float = 0.0,
    interface_surface_timesteps: list[InterfaceSurfaceTimestep] | None = None,
    mass_properties: list[MassProperty] | None = None,
    decomp_metrics: DecompMetrics | None = None,
) -> list[Finding]:
    """Aggregate and prioritize all findings from analysis modules."""
    all_findings: list[Finding] = []

    # Termination status check
    if termination.status == TerminationStatus.ERROR:
        msg = ""
        if termination.error_code:
            msg = f" Error code: {termination.error_code}."
        if termination.error_message:
            msg += f" {termination.error_message}"
        all_findings.append(Finding(
            severity=Severity.CRITICAL,
            category="termination",
            title="Simulation terminated with ERROR",
            description=(
                f"The simulation terminated abnormally.{msg} "
                f"Reached time: {termination.actual_time:.4E}, "
                f"target: {termination.target_time:.4E}."
            ),
            recommendation=(
                "Check the error code in the d3hsp/mes files for details. "
                "Common causes: negative volume, NaN velocity, memory exhaustion."
            ),
        ))
    elif termination.status == TerminationStatus.INCOMPLETE:
        all_findings.append(Finding(
            severity=Severity.CRITICAL,
            category="termination",
            title="Simulation output appears incomplete",
            description=(
                "No normal or error termination marker was found. "
                "The output files may be truncated, suggesting the simulation "
                "was killed externally or crashed without a clean termination."
            ),
            recommendation=(
                "Check system logs for OOM kills or walltime limits. "
                "Verify the run completed by checking the last lines of mes0000. "
                "Look for core dumps or signal files."
            ),
        ))
    else:
        # Normal termination
        if termination.actual_time > 0 and termination.target_time > 0:
            completion = termination.actual_time / termination.target_time
            if completion < 0.99:
                all_findings.append(Finding(
                    severity=Severity.WARNING,
                    category="termination",
                    title="Simulation did not reach target time",
                    description=(
                        f"Reached {termination.actual_time:.4E} of "
                        f"target {termination.target_time:.4E} "
                        f"({completion:.1%} complete)."
                    ),
                    recommendation="Check termination conditions.",
                ))

    # Collect all findings
    all_findings.extend(energy_findings)
    all_findings.extend(timestep_findings)
    all_findings.extend(warning_findings)
    all_findings.extend(contact_findings)
    all_findings.extend(performance_findings)

    # New diagnostics
    all_findings.extend(_diagnose_contact_dt(
        contact_dt_limit, min_dt, interface_surface_timesteps or [],
    ))
    all_findings.extend(_diagnose_mass_properties(mass_properties or []))
    all_findings.extend(_diagnose_decomp(decomp_metrics or DecompMetrics()))

    # Sort by severity: CRITICAL > WARNING > INFO
    severity_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}
    all_findings.sort(key=lambda f: severity_order.get(f.severity, 3))

    return all_findings
