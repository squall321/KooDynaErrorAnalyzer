"""Overall diagnostic engine that aggregates all analysis findings."""

from koodyna.models import (
    TerminationInfo, TerminationStatus, Finding, Severity,
    DecompMetrics, MassProperty, InterfaceSurfaceTimestep,
    WarningEntry, EnergySnapshot, PerformanceTiming,
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
    """
    Inertia ratio check disabled.

    Rationale: Part-level inertia ratios reflect design geometry (thin walls,
    beams, PCBs), not mesh quality issues. For deformable parts, inertia tensors
    are post-processing metrics and don't affect simulation stability. Only rigid
    bodies with extreme ratios (>1000) might show numerical issues in rotational
    dynamics, which is rare in typical drop/impact simulations.
    """
    findings: list[Finding] = []
    # Diagnostic disabled - inertia ratio is not a reliability indicator for deformable parts
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


def _diagnose_timestep_collapse(
    min_dt: float,
    warnings: list[WarningEntry],
    termination: TerminationInfo,
) -> list[Finding]:
    """Detect timestep collapse - simulation becoming impractical due to tiny timestep."""
    findings: list[Finding] = []

    # Check for extreme timestep reduction
    if min_dt < 1e-11 and min_dt > 0:
        # Count negative volume warnings
        neg_vol_warnings = [w for w in warnings if w.code == 40509]
        neg_vol_count = sum(w.count for w in neg_vol_warnings)

        severity = Severity.CRITICAL if neg_vol_count > 50 else Severity.WARNING
        findings.append(Finding(
            severity=severity,
            category="timestep",
            title=f"Timestep collapse detected (dt = {min_dt:.3E})",
            description=(
                f"최소 timestep이 {min_dt:.3E}로 감소했습니다. "
                f"이는 시뮬레이션을 실질적으로 불가능하게 만듭니다. "
                + (f"Negative volume warning(40509)이 {neg_vol_count}회 발생했습니다."
                   if neg_vol_count > 0 else "")
            ),
            recommendation=(
                "요소 붕괴(element collapse) 또는 과도한 변형이 원인입니다. "
                "해당 요소의 메시 품질을 개선하거나 *MAT_ADD_EROSION으로 "
                "파손 요소를 제거하세요. dt < 1e-11은 실용적이지 않습니다."
            ),
        ))

    return findings


def _diagnose_energy_instability(
    energy_snapshots: list[EnergySnapshot],
) -> list[Finding]:
    """Detect energy instability patterns that indicate impending failure."""
    findings: list[Finding] = []

    if not energy_snapshots:
        return findings

    final = energy_snapshots[-1]
    initial_total = energy_snapshots[0].total if energy_snapshots[0].total != 0 else 1.0

    # Check energy ratio explosion
    if final.energy_ratio > 4.0:
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="energy",
            title=f"에너지 비율 폭주 (ratio = {final.energy_ratio:.2f})",
            description=(
                f"에너지 비율이 {final.energy_ratio:.2f}로 상승했습니다. "
                f"이는 NaN이나 제약조건 행렬 오류(Error 30358)의 전조입니다."
            ),
            recommendation=(
                "제약조건(*CONSTRAINED_*)과 접촉 정의를 점검하세요. "
                "'shooting nodes' (비정상적으로 멀리 이동하는 노드)를 확인하세요."
            ),
        ))
    elif final.energy_ratio > 3.0:
        findings.append(Finding(
            severity=Severity.WARNING,
            category="energy",
            title=f"에너지 비율 상승 (ratio = {final.energy_ratio:.2f})",
            description=(
                f"에너지 비율이 {final.energy_ratio:.2f}입니다. "
                f"정상 범위(0.95~1.05)를 크게 벗어났습니다."
            ),
            recommendation="접촉 정의와 경계조건을 검토하세요.",
        ))

    # Check for negative internal energy
    if final.internal < 0:
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="energy",
            title=f"음수 내부 에너지 (IE = {final.internal:.3E})",
            description=(
                "내부 에너지가 음수입니다. 이는 물리적으로 불가능하며 "
                "수치적 불안정성을 의미합니다."
            ),
            recommendation=(
                "제약조건과 접촉 설정을 점검하세요. "
                "과도한 관통(penetration)이나 잘못된 경계조건이 원인일 수 있습니다."
            ),
        ))

    return findings


def _diagnose_warning_patterns(
    warnings: list[WarningEntry],
    termination: TerminationInfo,
) -> list[Finding]:
    """Detect problematic warning patterns based on frequency and type."""
    findings: list[Finding] = []

    if termination.total_cycles == 0:
        return findings

    # Check for high-frequency warnings (> 50% of cycles)
    for w in warnings:
        if w.count == 0:
            continue
        ratio = w.count / termination.total_cycles

        if ratio > 0.5:
            # Warning appears in > 50% of cycles - systemic issue
            if w.code == 40509:  # Negative volume
                findings.append(Finding(
                    severity=Severity.CRITICAL,
                    category="warnings",
                    title=f"Warning {w.code}: 전체 사이클의 {ratio:.0%} 발생",
                    description=(
                        f"Negative volume warning이 {w.count}회 발생 "
                        f"(전체 사이클 {termination.total_cycles}의 {ratio:.0%}). "
                        f"이는 근본적인 요소 품질 문제를 나타냅니다."
                    ),
                    recommendation=(
                        "해당 요소의 메시를 개선하거나 erosion 기준을 추가하세요. "
                        "매 사이클 반복되는 경고는 모델 재작성이 필요할 수 있습니다."
                    ),
                ))
            elif w.code in [40538, 40540]:  # Contact issues
                findings.append(Finding(
                    severity=Severity.WARNING,
                    category="warnings",
                    title=f"Warning {w.code}: 접촉 정의 문제 (사이클의 {ratio:.0%})",
                    description=(
                        f"접촉 관련 warning이 {w.count}회 발생. "
                        f"Tied interface 정의에 문제가 있습니다."
                    ),
                    recommendation=(
                        f"인터페이스 {', '.join(map(str, w.affected_interfaces[:5]))} "
                        f"등의 접촉 정의를 재검토하세요."
                    ),
                ))

    # Check for specific critical errors embedded as warnings
    neg_vol_total = sum(w.count for w in warnings if w.code == 40509)
    if neg_vol_total > 100:
        findings.append(Finding(
            severity=Severity.WARNING,
            category="warnings",
            title=f"Negative volume 누적 {neg_vol_total}회",
            description=(
                f"Negative volume이 {neg_vol_total}회 발생했습니다. "
                f"요소 붕괴가 진행 중입니다."
            ),
            recommendation="메시 품질을 개선하거나 erosion을 활성화하세요.",
        ))

    return findings


def _diagnose_performance_bottlenecks(
    performance: list[PerformanceTiming],
) -> list[Finding]:
    """Detect performance bottlenecks, especially MPP parallel efficiency issues.

    Focus on:
    - Excessive Force gather time (rigid body MPP communication overhead)
    - High Mass Scaling time (excessive mass scaling events)
    """
    findings: list[Finding] = []
    if not performance:
        return findings

    # Create a dict for easy lookup
    perf_map = {p.component: p for p in performance}

    # Check Force gather (MPP rigid body communication)
    force_gather = perf_map.get("Force gather")
    if force_gather:
        # Force gather > 5% → WARNING (parallel overhead)
        # Force gather > 10% → CRITICAL (severe parallel inefficiency)
        if force_gather.cpu_percent > 10.0:
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="performance",
                title=f"Force gather 시간 과다 ({force_gather.cpu_percent:.1f}%)",
                description=(
                    f"Force gather가 전체 CPU의 {force_gather.cpu_percent:.1f}%를 소비합니다 "
                    f"({force_gather.cpu_seconds:.2f}초). "
                    f"이는 MPP 병렬 계산에서 rigid body 통신 오버헤드가 과도함을 나타냅니다. "
                    f"병렬 효율이 크게 저하되고 있습니다."
                ),
                recommendation=(
                    f"1. Rigid body 개수 감소 (불필요한 rigid body를 deformable로 변경)\n"
                    f"2. MPP 프로세서 수 조정 (프로세서가 너무 많으면 통신 비용 증가)\n"
                    f"3. RCFORC 출력 빈도 감소 (rigid body force 출력이 gather 유발)\n"
                    f"4. Rigid body merge 검토 (작은 파트들을 병합)"
                ),
            ))
        elif force_gather.cpu_percent > 5.0:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="performance",
                title=f"Force gather 시간 주의 ({force_gather.cpu_percent:.1f}%)",
                description=(
                    f"Force gather가 전체 CPU의 {force_gather.cpu_percent:.1f}%를 소비합니다. "
                    f"MPP 병렬 계산에서 rigid body 통신 오버헤드가 있습니다."
                ),
                recommendation=(
                    f"Rigid body 개수 또는 MPP 프로세서 수를 검토하세요. "
                    f"프로세서 수를 줄이면 통신 비용이 감소할 수 있습니다."
                ),
            ))

    # Check Mass Scaling (excessive mass scaling events)
    mass_scaling = perf_map.get("Mass Scaling")
    if mass_scaling and mass_scaling.cpu_percent > 5.0:
        findings.append(Finding(
            severity=Severity.WARNING,
            category="performance",
            title=f"Mass Scaling 시간 과다 ({mass_scaling.cpu_percent:.1f}%)",
            description=(
                f"Mass Scaling이 전체 CPU의 {mass_scaling.cpu_percent:.1f}%를 소비합니다. "
                f"Mass scaling 이벤트가 빈번하게 발생하고 있습니다."
            ),
            recommendation=(
                f"1. Mass scaling 설정 재검토 (*CONTROL_TIMESTEP, DT2MS)\n"
                f"2. 메시 품질 개선 (과도하게 작은 요소 제거)\n"
                f"3. 접촉 설정 확인 (과도한 penalty로 인한 dt 감소)"
            ),
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
    warnings: list[WarningEntry] | None = None,
    energy_snapshots: list[EnergySnapshot] | None = None,
    performance: list[PerformanceTiming] | None = None,
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

    # Advanced diagnostics based on test case analysis
    all_findings.extend(_diagnose_timestep_collapse(
        min_dt, warnings or [], termination,
    ))
    all_findings.extend(_diagnose_energy_instability(
        energy_snapshots or [],
    ))
    all_findings.extend(_diagnose_warning_patterns(
        warnings or [], termination,
    ))
    all_findings.extend(_diagnose_performance_bottlenecks(
        performance or [],
    ))

    # Sort by severity: CRITICAL > WARNING > INFO
    severity_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}
    all_findings.sort(key=lambda f: severity_order.get(f.severity, 3))

    return all_findings
