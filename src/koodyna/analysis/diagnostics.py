"""Overall diagnostic engine that aggregates all analysis findings."""

from koodyna.models import (
    TerminationInfo, TerminationStatus, Finding, Severity,
    DecompMetrics, MassProperty, InterfaceSurfaceTimestep,
    WarningEntry, EnergySnapshot, PerformanceTiming,
    TimestepEntry, PartDefinition,
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
                f"활성 서프스 {len(active)}개 중 제어 인터페이스가 확인됨. "
                f"Penalty 기반 접촉에서 접촉 강성(contact stiffness)은 "
                f"k = (fs × K × A²) / V로 계산되며, "
                f"이 강성이 높을수록 접촉 안정성 dt가 작아집니다. "
                f"접촉 dt가 요소 dt보다 작으면 접촉이 전체 시뮬레이션의 timestep을 지배합니다."
            ),
            recommendation=(
                "1. Penalty scale factor(SLSFAC) 감소 → 접촉 강성 ↓ → 접촉 dt ↑\n"
                "2. Soft constraint (SOFT=1 또는 2) 사용 → 질량 기반으로 접촉 강성 자동 조절\n"
                "3. 해당 인터페이스의 접촉 두께(SHLTHK) 설정 확인\n"
                "4. 접촉면 메시 크기가 과도하게 작지 않은지 확인"
            ),
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
    """Diagnose MPP decomposition load imbalance.

    MPP(Massively Parallel Processing)에서 도메인 분할(domain decomposition)은
    메시를 프로세서 수만큼 분할합니다. 이상적으로 각 프로세서의 계산량이 균등해야
    하며, 불균형이 크면 가장 느린 프로세서가 전체 속도를 결정합니다(Amdahl's Law).

    Imbalance = (max_cost - min_cost) / max_cost
    - > 50% → CRITICAL (심각한 불균형, 일부 프로세서만 과부하)
    - > 30% → WARNING (병렬 효율 저하, 스케일링 비효율적)
    """
    findings: list[Finding] = []
    if decomp_metrics.min_cost <= 0 or decomp_metrics.max_cost <= 0:
        return findings

    # Calculate imbalance percentage: (max - min) / max
    imbalance = (decomp_metrics.max_cost - decomp_metrics.min_cost) / decomp_metrics.max_cost

    if imbalance > 0.50:
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="decomposition",
            title=f"MPP 부하 불균형 심각 ({imbalance:.1%})",
            description=(
                f"프로세서 간 부하 차이가 {imbalance:.1%}입니다 "
                f"(Min={decomp_metrics.min_cost:.6f}, Max={decomp_metrics.max_cost:.6f}). "
                f"MPP에서 각 프로세서는 배정된 도메인의 요소를 계산하고, "
                f"매 사이클 동기화(MPI barrier)를 수행합니다. "
                f"불균형이 50%를 초과하면 가장 빠른 프로세서가 "
                f"가장 느린 프로세서를 기다리는 시간이 전체의 절반 이상이 됩니다."
            ),
            recommendation=(
                "1. Decomposition 방법 변경: RCB(기본) → METIS 또는 GREEDY\n"
                "   (*CONTROL_MPP_DECOMPOSITION_METHOD 키워드)\n"
                "2. METIS는 그래프 기반 파티셔닝으로 접촉 포함 부하를 균등 분배\n"
                "3. 프로세서 수를 줄이면 도메인당 요소 수 증가 → 불균형 완화\n"
                "4. 모델 내 극단적 크기 차이가 있는 파트 확인"
            ),
        ))
    elif imbalance > 0.30:
        findings.append(Finding(
            severity=Severity.WARNING,
            category="decomposition",
            title=f"MPP 부하 불균형 ({imbalance:.1%})",
            description=(
                f"프로세서 간 부하 차이가 {imbalance:.1%}입니다 "
                f"(Min={decomp_metrics.min_cost:.6f}, Max={decomp_metrics.max_cost:.6f}). "
                f"병렬 효율이 {1.0 - imbalance:.0%} 수준으로 저하되어, "
                f"프로세서 추가 대비 성능 향상이 제한적입니다."
            ),
            recommendation=(
                "1. Decomposition 방법 변경 (RCB → METIS)\n"
                "   METIS는 그래프 파티셔닝으로 접촉/경계 통신을 최소화\n"
                "2. 프로세서 수 최적화 (요소 수 대비 프로세서가 과다한지 확인)\n"
                f"3. Standard deviation: {decomp_metrics.std_deviation:.6f}"
            ),
        ))

    return findings


def _diagnose_timestep_collapse(
    min_dt: float,
    warnings: list[WarningEntry],
    termination: TerminationInfo,
) -> list[Finding]:
    """Detect timestep collapse - simulation becoming impractical due to tiny timestep.

    양해적 시간 적분(explicit time integration)에서 안정 timestep은
    dt = L_char / c (L_char: 요소 특성 길이, c: 음속)로 결정됩니다.
    요소가 심하게 변형되면 L_char → 0이 되어 dt가 극소값으로 감소합니다.
    dt < 1e-11이면 목표 시간 도달에 필요한 사이클 수가 비실용적입니다.
    """
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
                f"양해적 시간 적분에서 dt = L/c (L: 요소 특성길이, c: 재료 음속)로 결정되며, "
                f"요소가 심하게 찌그러지면 L → 0이 되어 dt가 붕괴합니다. "
                f"dt < 1e-11은 목표 시간 도달에 수십억 사이클이 필요하여 실용적이지 않습니다. "
                + (f"Negative volume warning(40509)이 {neg_vol_count}회 발생하여 "
                   f"요소 반전(element inversion)이 확인됩니다."
                   if neg_vol_count > 0 else "")
            ),
            recommendation=(
                "1. *MAT_ADD_EROSION으로 파손/반전 요소 자동 제거 (MXEPS, MNEPS 설정)\n"
                "2. *CONTROL_TIMESTEP에서 ERODE=1, TSMIN 설정으로 최소 dt 이하 요소 삭제\n"
                "3. 해당 영역 메시를 재생성하여 초기 요소 품질 개선\n"
                "4. 경계조건/하중이 과도한 변형을 유발하는지 확인"
            ),
        ))

    return findings


def _diagnose_energy_instability(
    energy_snapshots: list[EnergySnapshot],
) -> list[Finding]:
    """Detect energy instability patterns that indicate impending failure.

    양해적 유한요소법에서 에너지 보존(energy balance)은 수치 안정성의 핵심 지표입니다.
    총 에너지 = KE + IE + HG + Slide + Damping + External Work
    에너지 비율(Energy Ratio) = 현재 총에너지 / 초기 총에너지
    이상적 값: 1.0 (완벽한 에너지 보존)
    허용 범위: 0.95 ~ 1.05 (5% 이내)
    """
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
                f"에너지 비율(E_total/E_initial)은 이상적으로 1.0이어야 하며, "
                f"1.05를 초과하면 에너지가 인위적으로 생성되고 있음을 의미합니다. "
                f"4.0 이상은 NaN 발산이나 제약조건 행렬 특이성(Error 30358)의 전조이며, "
                f"곧 시뮬레이션이 발산할 가능성이 높습니다."
            ),
            recommendation=(
                "1. *CONSTRAINED_* 정의 점검 (과도하게 구속된 노드 → 에너지 주입)\n"
                "2. Contact interface에서 초기 관통(initial penetration) 제거\n"
                "3. Penalty stiffness 감소 (SLSFAC) → 접촉 에너지 주입 감소\n"
                "4. 'shooting nodes' 확인 (비정상 고속 노드 → 에너지 폭주 원인)"
            ),
        ))
    elif final.energy_ratio > 3.0:
        findings.append(Finding(
            severity=Severity.WARNING,
            category="energy",
            title=f"에너지 비율 상승 (ratio = {final.energy_ratio:.2f})",
            description=(
                f"에너지 비율이 {final.energy_ratio:.2f}입니다. "
                f"정상 범위(0.95~1.05)를 크게 벗어났습니다. "
                f"접촉 관통, 과도한 hourglass 에너지, 또는 제약조건 충돌로 인해 "
                f"비물리적 에너지가 시스템에 주입되고 있습니다."
            ),
            recommendation=(
                "1. 접촉 정의와 경계조건을 검토하세요\n"
                "2. Hourglass 에너지 비율 확인 (HG/IE)\n"
                "3. Sliding interface 에너지 확인 (과도한 접촉 에너지)"
            ),
        ))

    # Check for negative internal energy
    if final.internal < 0:
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="energy",
            title=f"음수 내부 에너지 (IE = {final.internal:.3E})",
            description=(
                f"내부 에너지(Internal Energy)가 {final.internal:.3E}로 음수입니다. "
                f"내부 에너지는 요소의 변형 에너지(strain energy)의 합으로, "
                f"물리적으로 항상 0 이상이어야 합니다. "
                f"음수 IE는 요소의 응력-변형률 관계가 비물리적이거나, "
                f"제약조건이 요소에서 에너지를 추출하고 있음을 의미합니다. "
                f"시뮬레이션 결과를 신뢰할 수 없습니다."
            ),
            recommendation=(
                "1. 재료 모델의 응력-변형률 곡선 확인 (softening이 과도한지)\n"
                "2. 제약조건(*CONSTRAINED_*)과 접촉 설정 점검\n"
                "3. 과도한 관통(penetration)으로 인한 penalty 에너지 확인\n"
                "4. 잘못된 경계조건이 에너지를 추출하는지 확인"
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
                        f"요소의 Jacobian 행렬식이 음수가 되었으며(J < 0), "
                        f"이는 요소 노드 순서가 반전되어 체적이 음수임을 의미합니다. "
                        f"매 사이클 반복되는 것은 해당 요소가 복구 불가능한 상태입니다."
                    ),
                    recommendation=(
                        "1. 해당 요소 영역의 메시를 재생성 (왜곡 요소 제거)\n"
                        "2. *MAT_ADD_EROSION으로 파손 요소 자동 삭제\n"
                        "3. *CONTROL_TIMESTEP에서 ERODE=1 활성화\n"
                        "4. 매 사이클 반복되면 모델 재작성 필요"
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
                f"요소의 Jacobian(J)이 음수가 되어 체적이 반전되었습니다. "
                f"이는 과도한 변형, 불량 메시, 또는 부적절한 재료 모델이 원인입니다. "
                f"계속 누적되면 timestep 붕괴나 에너지 발산으로 이어집니다."
            ),
            recommendation=(
                "1. 메시 품질 개선 (Jacobian ratio > 0.3, aspect ratio < 5)\n"
                "2. *MAT_ADD_EROSION (MXEPS: 최대 유효 변형률 기준 삭제)\n"
                "3. Erosion 활성화: *CONTROL_TIMESTEP, ERODE=1, TSMIN 설정"
            ),
        ))

    # Check for tied contact warnings (50135, 50136)
    warning_50135 = next((w for w in warnings if w.code == 50135), None)
    warning_50136 = next((w for w in warnings if w.code == 50136), None)

    if warning_50135 and warning_50135.count > 1000:
        interface_desc = f"인터페이스 {', '.join(map(str, warning_50135.affected_interfaces[:10]))}"
        if len(warning_50135.affected_interfaces) > 10:
            interface_desc += f" 등 {len(warning_50135.affected_interfaces)}개"

        findings.append(Finding(
            severity=Severity.WARNING,
            category="warnings",
            title=f"Tied contact 노드 누락 (Warning 50135: {warning_50135.count}회)",
            description=(
                f"Tied contact에서 slave 노드가 master segment를 찾지 못했습니다 "
                f"({warning_50135.count}회 발생). "
                f"{interface_desc}에서 메시 불일치가 있습니다. "
                f"Tied contact는 slave 노드를 가장 가까운 master segment에 투영(projection)하여 "
                f"구속합니다. 투영 실패 시 해당 노드는 구속되지 않아 "
                f"tied 인터페이스에서 분리(debonding)가 발생합니다."
            ),
            recommendation=(
                "1. Master 메시가 slave 메시보다 조밀하거나 같은 크기인지 확인\n"
                "2. *CONTACT에서 SBOPT=3 (투영 알고리즘 개선), DEPTH=5 (다중 검색)\n"
                "3. Tied 인터페이스 근처 메시 세분화 (불일치 해소)\n"
                "4. 메시 호환성이 어려우면 merge nodes로 직접 결합 고려"
            ),
        ))

    if warning_50136 and warning_50136.count > 100:
        interface_desc = f"인터페이스 {', '.join(map(str, warning_50136.affected_interfaces[:10]))}"
        if len(warning_50136.affected_interfaces) > 10:
            interface_desc += f" 등 {len(warning_50136.affected_interfaces)}개"

        findings.append(Finding(
            severity=Severity.WARNING,
            category="warnings",
            title=f"Tied contact 노드 거리 초과 (Warning 50136: {warning_50136.count}회)",
            description=(
                f"Slave 노드가 master segment로부터 너무 멀리 떨어져 있습니다 "
                f"({warning_50136.count}회 발생). "
                f"{interface_desc}에서 기하학적 간격이 있습니다. "
                f"Tied contact 검색 거리는 기본적으로 slave 요소 크기의 일정 비율이며, "
                f"이 거리를 초과하는 노드는 구속 대상에서 제외됩니다. "
                f"결합되어야 할 표면 사이에 물리적 간격(gap)이 존재합니다."
            ),
            recommendation=(
                "1. SFACT 파라미터 증가 → 검색 거리 확대 (기본값의 2~5배)\n"
                "2. CAD에서 파트 간 기하학적 간격 제거 (표면 정렬)\n"
                "3. 메시 생성 시 인터페이스 표면이 정확히 일치하도록 설정\n"
                "4. 초기 간섭(interference) 확인 및 제거"
            ),
        ))

    return findings


def _diagnose_performance_bottlenecks(
    performance: list[PerformanceTiming],
) -> list[Finding]:
    """Detect performance bottlenecks, especially MPP parallel efficiency issues.

    LS-DYNA explicit solver의 주요 계산 단계:
    1. Element processing: 요소별 내력(internal force) 계산 (응력×B행렬)
    2. Contact algorithm: 접촉 탐색(bucket sort) + 관통 검출 + penalty force
    3. Force gather: MPP에서 rigid body force를 모든 프로세서에 수집/분배
    4. Mass Scaling: DT2MS 활성 시 질량 추가 계산
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
                    f"MPP에서 rigid body는 여러 프로세서에 걸쳐 분포할 수 있으며, "
                    f"매 사이클 모든 프로세서의 rigid body force를 수집(gather)하고 "
                    f"합산하여 재분배해야 합니다. 이 MPI 통신은 프로세서 수에 비례하며, "
                    f"rigid body 수가 많을수록 통신량이 증가합니다."
                ),
                recommendation=(
                    "1. 불필요한 rigid body를 deformable body로 변경\n"
                    "2. MPP 프로세서 수 감소 (프로세서당 통신 비용 감소)\n"
                    "3. RCFORC 출력 빈도 감소 (*DATABASE_RCFORC의 DT 증가)\n"
                    "4. 작은 rigid body들을 *CONSTRAINED_RIGID_BODIES로 병합"
                ),
            ))
        elif force_gather.cpu_percent > 5.0:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="performance",
                title=f"Force gather 시간 주의 ({force_gather.cpu_percent:.1f}%)",
                description=(
                    f"Force gather가 전체 CPU의 {force_gather.cpu_percent:.1f}%를 소비합니다. "
                    f"MPP 병렬 계산에서 rigid body 간 MPI 통신(gather/scatter) 오버헤드입니다. "
                    f"프로세서 수가 많을수록, rigid body 수가 많을수록 비용이 증가합니다."
                ),
                recommendation=(
                    "1. Rigid body 개수 또는 MPP 프로세서 수를 검토하세요\n"
                    "2. 프로세서 수를 줄이면 통신 비용이 감소할 수 있습니다"
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
                f"Mass scaling은 dt < DT2MS인 요소에 인위적 질량을 추가하여 "
                f"timestep을 목표값(DT2MS)으로 유지합니다. "
                f"추가 질량 = m_added = m_original × ((dt_target/dt_element)² - 1). "
                f"Mass scaling 계산이 빈번하다는 것은 많은 요소가 목표 dt보다 "
                f"작은 timestep을 가지고 있음을 의미합니다."
            ),
            recommendation=(
                "1. DT2MS 값 재검토 (너무 크면 과도한 질량 추가)\n"
                "2. 작은 요소 제거/병합으로 메시 품질 개선\n"
                "3. 접촉 설정에서 과도한 penalty로 인한 dt 감소 확인\n"
                "4. 추가된 질량이 원래 질량의 5% 이내인지 glstat에서 확인"
            ),
        ))

    # Check Contact algorithm (excessive contact time)
    contact = perf_map.get("Contact algorithm")
    if contact:
        # Contact > 40% → WARNING (contact-dominated)
        # Contact > 50% → CRITICAL (severe contact bottleneck)
        if contact.cpu_percent > 50.0:
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="performance",
                title=f"접촉 계산 시간 과다 ({contact.cpu_percent:.1f}%)",
                description=(
                    f"Contact algorithm이 전체 CPU의 {contact.cpu_percent:.1f}%를 소비합니다 "
                    f"({contact.cpu_seconds:.2f}초). "
                    f"접촉 계산은 (1) bucket sort로 후보 쌍 탐색 O(N), "
                    f"(2) 관통 검출(penetration check), "
                    f"(3) penalty force 계산으로 구성됩니다. "
                    f"Single Surface 접촉은 모든 요소 쌍을 탐색하므로 비용이 높고, "
                    f"세그먼트 수가 많을수록 계산량이 급증합니다."
                ),
                recommendation=(
                    "1. 불필요한 접촉 인터페이스 제거 (접촉하지 않는 파트 쌍)\n"
                    "2. Single Surface를 구체적인 Surface-to-Surface로 분리\n"
                    "3. BSORT 파라미터 조정 (bucket sort 빈도, 기본=10사이클마다)\n"
                    "4. SOFT=2 (segment-based) 사용 시 더 효율적일 수 있음\n"
                    "5. Contact thickness(SHLTHK) 과다 설정 확인 → 검색 범위 증가"
                ),
            ))
        elif contact.cpu_percent > 40.0:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="performance",
                title=f"접촉 계산 시간 높음 ({contact.cpu_percent:.1f}%)",
                description=(
                    f"Contact algorithm이 전체 CPU의 {contact.cpu_percent:.1f}%를 소비합니다. "
                    f"접촉이 지배적인 시뮬레이션(다물체 충돌, 성형 등)에서는 "
                    f"30~40%가 일반적이나, 최적화 여지가 있습니다."
                ),
                recommendation=(
                    "1. 접촉 인터페이스 범위 축소 (불필요한 파트 제외)\n"
                    "2. Bucket sort 빈도 최적화 (*CONTACT의 BSORT)\n"
                    "3. Contact type 최적화 (AUTOMATIC_SINGLE_SURFACE → S2S 분리)"
                ),
            ))

    return findings


def _diagnose_problematic_parts(
    smallest_timesteps: list[TimestepEntry],
    parts: list[PartDefinition],
) -> list[Finding]:
    """Diagnose parts that dominate timestep control.

    양해적 시간 적분에서 전역 timestep은 모든 요소 중 가장 작은 dt로 결정됩니다:
    dt_global = TSSFAC × min(dt_element) (TSSFAC: 안전 계수, 기본 0.9)
    dt_element = L_char / c (L_char: 요소 특성 길이, c: 재료 음속)

    특정 파트가 dt를 지배하면 그 파트의 메시 품질이 전체 계산 속도를 결정합니다.
    dt가 절반이면 사이클 수가 2배 → 계산 시간 2배.
    """
    findings: list[Finding] = []

    if not smallest_timesteps or not parts:
        return findings

    # Count timesteps per part
    part_ts_count: dict[int, int] = {}
    for ts in smallest_timesteps:
        part_id = ts.part_number
        part_ts_count[part_id] = part_ts_count.get(part_id, 0) + 1

    # Find part name mapping
    part_names = {p.part_id: p.name for p in parts}

    # Find dominant parts (>50% of smallest timesteps)
    total_ts = len(smallest_timesteps)
    for part_id, count in sorted(part_ts_count.items(), key=lambda x: x[1], reverse=True):
        ratio = count / total_ts
        if ratio > 0.50:
            part_name = part_names.get(part_id, f"Part {part_id}")
            min_dt = min(ts.timestep for ts in smallest_timesteps if ts.part_number == part_id)

            findings.append(Finding(
                severity=Severity.WARNING,
                category="part_analysis",
                title=f"파트 {part_id} ({part_name})가 timestep 지배 ({ratio:.0%})",
                description=(
                    f"파트 {part_id} ({part_name})가 가장 작은 timestep의 {ratio:.0%}를 차지합니다 "
                    f"({count}/{total_ts}개). 최소 dt={min_dt:.3E}. "
                    f"양해적 적분에서 dt = L/c이므로, 이 파트의 가장 작은 요소가 "
                    f"전체 시뮬레이션의 계산 속도를 결정합니다. "
                    f"다른 파트 요소들은 더 큰 dt를 가질 수 있지만, "
                    f"이 파트에 의해 전역적으로 제한됩니다."
                ),
                recommendation=(
                    f"1. 파트 {part_id}의 메시에서 가장 작은 요소 확인 및 재생성\n"
                    f"2. 과도하게 세밀한(over-refined) 메시 영역이 있는지 확인\n"
                    f"3. 재료 물성 확인: E↑ → c↑ → dt↓ (과도한 탄성계수가 dt를 줄임)\n"
                    f"4. Mass scaling 적용: *CONTROL_TIMESTEP에서 DT2MS 설정\n"
                    f"   (주의: 추가 질량이 원래 질량의 5% 미만이어야 결과 신뢰)"
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
    smallest_timesteps: list[TimestepEntry] | None = None,
    parts: list[PartDefinition] | None = None,
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
            title="해석 에러 종료",
            description=(
                f"시뮬레이션이 비정상 종료되었습니다.{msg} "
                f"도달 시간: {termination.actual_time:.4E}, "
                f"목표 시간: {termination.target_time:.4E}. "
                f"LS-DYNA는 복구 불가능한 수치적 오류(negative volume, NaN, "
                f"메모리 부족 등)를 감지하면 즉시 종료합니다."
            ),
            recommendation=(
                "1. d3hsp/mes 파일에서 에러 코드와 위치(요소/노드 번호) 확인\n"
                "2. 가장 흔한 원인: negative volume(요소 반전), NaN velocity(발산)\n"
                "3. 해당 위치의 메시/경계조건/접촉 설정 검토\n"
                "4. *MAT_ADD_EROSION으로 파손 요소 자동 제거 고려"
            ),
        ))
    elif termination.status == TerminationStatus.INCOMPLETE:
        all_findings.append(Finding(
            severity=Severity.CRITICAL,
            category="termination",
            title="해석 미완료 (출력 불완전)",
            description=(
                "정상 종료 또는 에러 종료 표시가 발견되지 않았습니다. "
                "출력 파일이 불완전하며, 시뮬레이션이 외부에서 강제 종료되었거나 "
                "클린 종료 없이 크래시된 것으로 보입니다. "
                "일반적 원인: HPC walltime 초과, OOM(Out Of Memory) kill, "
                "라이선스 만료, 파일시스템 오류."
            ),
            recommendation=(
                "1. 시스템 로그에서 OOM kill 또는 walltime 초과 확인\n"
                "2. mes0000 파일의 마지막 줄에서 진행 상태 확인\n"
                "3. 코어 덤프(core dump) 또는 signal 파일 확인\n"
                "4. HPC의 경우 walltime 증가 또는 restart 파일 활용"
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
                    title="목표 시간 미도달",
                    description=(
                        f"도달 시간 {termination.actual_time:.4E} / "
                        f"목표 시간 {termination.target_time:.4E} "
                        f"({completion:.1%} 완료). "
                        f"*CONTROL_TERMINATION의 ENDTIM보다 일찍 종료되었습니다."
                    ),
                    recommendation=(
                        "1. *CONTROL_TERMINATION의 ENDTIM 및 DTMIN 설정 확인\n"
                        "2. Sense switch(sw1/sw2) 파일로 인한 조기 종료 여부 확인"
                    ),
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
    all_findings.extend(_diagnose_problematic_parts(
        smallest_timesteps or [],
        parts or [],
    ))

    # Sort by severity: CRITICAL > WARNING > INFO
    severity_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}
    all_findings.sort(key=lambda f: severity_order.get(f.severity, 3))

    return all_findings
