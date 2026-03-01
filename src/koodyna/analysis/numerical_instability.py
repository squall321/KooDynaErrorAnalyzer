"""Detection of numerical instabilities from nodout, bndout, and glstat data."""

import math
from pathlib import Path
from koodyna.models import Finding, Severity, EnergySnapshot, SlurmJobInfo
from koodyna.parsers.nodout import NodoutParser, NodalTimeSeries
from koodyna.parsers.bndout import BndoutParser, BoundaryForceTimeSeries


def detect_shooting_nodes(
    nodout_path: Path | None,
    velocity_threshold: float = 1000.0,  # m/s - adjust for simulation type
) -> list[Finding]:
    """
    Detect nodes with abnormally high velocity (shooting nodes).

    Shooting nodes indicate numerical instability from:
    - Constraint matrix errors
    - Excessive contact penetration
    - Overly stiff penalty contact
    - Conflicting boundary conditions

    Args:
        nodout_path: Path to nodout file
        velocity_threshold: Velocity magnitude threshold (m/s)
                           Default 1000 m/s for typical structural analysis
                           Increase for high-speed impact (e.g., 10000 m/s)

    Returns:
        list of Finding objects
    """
    findings: list[Finding] = []

    if not nodout_path or not nodout_path.exists():
        return findings

    try:
        parser = NodoutParser(nodout_path)
        # Only parse limited nodes to avoid memory issues
        nodes = parser.parse(max_nodes=1000)

        shooting_nodes = []
        for node_id, time_series in nodes.items():
            max_v = time_series.max_velocity()
            if max_v > velocity_threshold:
                shooting_nodes.append((node_id, max_v))

        if shooting_nodes:
            # Sort by velocity magnitude (highest first)
            shooting_nodes.sort(key=lambda x: x[1], reverse=True)

            # Report top 5
            top_nodes = shooting_nodes[:5]
            node_desc = ', '.join([f"Node {nid} ({v:.2E} m/s)" for nid, v in top_nodes])

            if len(shooting_nodes) > 5:
                node_desc += f" ... ({len(shooting_nodes)} total)"

            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="numerical_instability",
                title=f"Shooting nodes detected ({len(shooting_nodes)} nodes)",
                description=(
                    f"{node_desc}. "
                    f"Shooting node란 비정상적으로 큰 속도(|v| > {velocity_threshold:.0f} m/s)를 "
                    f"가진 노드입니다. 명시적 시간 적분에서 가속도 a = F/m으로 속도를 "
                    f"업데이트하는데, 접촉 penalty force가 과도하거나(F↑), 질량이 너무 "
                    f"작거나(m↓), constraint 행렬에 특이점이 있으면 한 스텝에서 속도가 "
                    f"급격히 발산합니다. 이 노드들은 주변 요소를 왜곡시켜 negative volume "
                    f"에러의 직접 원인이 됩니다."
                ),
                recommendation=(
                    f"1. 해당 노드가 포함된 *CONSTRAINED_* 정의 점검 — 중복 constraint가 "
                    f"있으면 내부적으로 상반되는 힘이 발생하여 노드가 발산합니다\n"
                    f"2. Contact interface 초기 관통 제거 — 초기 관통된 노드에 penalty "
                    f"force가 순간적으로 집중되어 shooting node를 유발합니다. "
                    f"*CONTROL_CONTACT의 PENOPT로 관통 처리 설정\n"
                    f"3. Penalty stiffness 감소 — SLSFAC < 0.1로 설정하여 접촉 강성을 "
                    f"낮추거나, soft constraint(SOFT=1/2) 사용. k_contact = "
                    f"fs × K × A²/V에서 fs(SLSFAC)를 줄이면 접촉력 감소\n"
                    f"4. 중복된 constraint/contact 제거 — 같은 노드에 여러 constraint가 "
                    f"적용되면 자유도 과잉 구속으로 힘이 발산합니다"
                ),
            ))

    except Exception as e:
        # Parse error - don't fail the entire analysis
        pass

    return findings


def detect_high_frequency_oscillation(
    nodout_path: Path | None,
    oscillation_threshold: float = 10000.0,  # Hz
) -> list[Finding]:
    """
    Detect non-physical high-frequency oscillations in nodal velocity.

    High-frequency oscillations indicate:
    - Timestep too large
    - Inadequate hourglass control
    - Shear locking in elements

    Method: Count zero-crossings in velocity signal
    - Typical structural vibration: 100-1000 Hz
    - Numerical oscillation: > 10 kHz

    Args:
        nodout_path: Path to nodout file
        oscillation_threshold: Frequency threshold (Hz) for warning

    Returns:
        list of Finding objects
    """
    findings: list[Finding] = []

    if not nodout_path or not nodout_path.exists():
        return findings

    try:
        parser = NodoutParser(nodout_path)
        nodes = parser.parse(max_nodes=500)

        oscillating_nodes = []

        for node_id, time_series in nodes.items():
            if len(time_series.snapshots) < 10:
                continue  # Need sufficient samples

            # Count zero-crossings in x-velocity
            crossings = _count_zero_crossings([s.x_vel for s in time_series.snapshots])

            if len(time_series.snapshots) > 1:
                total_time = time_series.snapshots[-1].time - time_series.snapshots[0].time
                if total_time > 0:
                    # Zero-crossing rate (crossings per second)
                    zcr = crossings / total_time

                    if zcr > oscillation_threshold:
                        oscillating_nodes.append((node_id, zcr))

        if oscillating_nodes:
            oscillating_nodes.sort(key=lambda x: x[1], reverse=True)
            top_nodes = oscillating_nodes[:5]
            node_desc = ', '.join([f"Node {nid} ({freq:.0f} Hz)" for nid, freq in top_nodes])

            if len(oscillating_nodes) > 5:
                node_desc += f" ... ({len(oscillating_nodes)} total)"

            findings.append(Finding(
                severity=Severity.WARNING,
                category="numerical_instability",
                title=f"High-frequency oscillation detected ({len(oscillating_nodes)} nodes)",
                description=(
                    f"{node_desc}. "
                    f"Zero-crossing rate(ZCR)으로 측정한 진동 주파수가 {oscillation_threshold/1000:.0f} kHz를 "
                    f"초과합니다. 일반적인 구조 진동 주파수는 100~1000 Hz이며, 10 kHz 이상은 "
                    f"비물리적인 수치 진동입니다. 이는 reduced integration 요소(1-point Gauss)의 "
                    f"hourglass mode(zero-energy mode)가 제어되지 않거나, Courant 안정 조건 "
                    f"(dt < L/c)에 가까워 수치적 분산(numerical dispersion)이 발생하는 것입니다. "
                    f"Hourglass mode는 요소 강성 행렬의 rank deficiency로 인해 에너지 없이 "
                    f"변형되는 모드이며, 물리적으로 무의미한 고주파 진동을 생성합니다."
                ),
                recommendation=(
                    f"1. Hourglass control 강화 — IHQ=4(Flanagan-Belytschko stiffness)는 "
                    f"viscous+stiffness 혼합으로 효과적. IHQ=8(Puso)은 전단 잠김 방지에 유리\n"
                    f"2. Fully-integrated element 사용 — shell: ELFORM=16(fully-integrated), "
                    f"solid: ELFORM=2(8-point). Hourglass mode가 원천적으로 제거되지만 "
                    f"계산 비용이 2~5배 증가\n"
                    f"3. Timestep 감소 — TSSFAC를 0.9/0.67에서 0.5로 줄여 Courant 조건에 "
                    f"여유를 확보. dt = TSSFAC × L_char / c\n"
                    f"4. 해당 영역 메시 세분화 — 요소 크기가 작아지면 고주파 모드의 "
                    f"파장이 메시로 해상 가능해져 진동이 감소합니다"
                ),
            ))

    except Exception:
        pass

    return findings


def verify_constraint_compliance(
    nodout_path: Path | None,
    tolerance: float = 1e-6,  # Relative to model size
) -> list[Finding]:
    """
    Verify that constrained nodes have zero displacement.

    Note: This requires knowledge of which nodes are constrained,
    which we don't have from d3hsp. For now, we detect nodes with
    suspiciously small but non-zero displacement (possible constraint violation).

    Args:
        nodout_path: Path to nodout file
        tolerance: Displacement tolerance (absolute)

    Returns:
        list of Finding objects
    """
    findings: list[Finding] = []

    if not nodout_path or not nodout_path.exists():
        return findings

    # TODO: Implement when we can parse constraint definitions from d3hsp or k file
    # For now, skip this diagnostic

    return findings


def detect_excessive_reaction_force(
    bndout_path: Path | None,
    spike_ratio: float = 100.0,  # Peak / mean threshold
) -> list[Finding]:
    """
    Detect abnormally high reaction forces at boundary nodes.

    Excessive reaction forces indicate:
    - Overly stiff penalty contact
    - Initial penetration in contact definitions
    - Conflicting or over-constrained boundary conditions

    Method: Detect force spikes (peak >> mean)
    - spike_ratio: If max_force > spike_ratio × mean_force → warning

    Args:
        bndout_path: Path to bndout file
        spike_ratio: Ratio of peak to mean force for warning

    Returns:
        list of Finding objects
    """
    findings: list[Finding] = []

    if not bndout_path or not bndout_path.exists():
        return findings

    try:
        parser = BndoutParser(bndout_path)
        nodes = parser.parse()

        spike_nodes = []
        oscillating_nodes = []

        for node_id, time_series in nodes.items():
            if len(time_series.snapshots) < 5:
                continue  # Need sufficient samples

            max_f = time_series.max_force()
            mean_f = time_series.mean_force()

            # Detect force spike
            if mean_f > 1e-9:  # Avoid division by zero
                ratio = max_f / mean_f
                if ratio > spike_ratio:
                    spike_nodes.append((node_id, max_f, mean_f, ratio))

            # Detect oscillating force
            force_values = [s.force_magnitude() for s in time_series.snapshots]
            if _has_high_frequency_oscillation(force_values):
                oscillating_nodes.append(node_id)

        if spike_nodes:
            spike_nodes.sort(key=lambda x: x[3], reverse=True)  # Sort by ratio
            top_nodes = spike_nodes[:5]
            node_desc = ', '.join([
                f"Node {nid} (max={max_f:.2E} N, avg={mean_f:.2E} N, ratio={ratio:.0f}x)"
                for nid, max_f, mean_f, ratio in top_nodes
            ])

            if len(spike_nodes) > 5:
                node_desc += f" ... ({len(spike_nodes)} total)"

            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="numerical_instability",
                title=f"Reaction force spike detected ({len(spike_nodes)} nodes)",
                description=(
                    f"{node_desc}. "
                    f"경계 노드의 반력(reaction force)이 평균 대비 {spike_ratio:.0f}배 이상 "
                    f"급증했습니다. 명시적 시간 적분에서 반력 R = K × u + C × v로 계산되는데, "
                    f"penalty contact에서 관통 깊이 g가 순간적으로 커지면 "
                    f"F_contact = k_penalty × g로 반력이 급등합니다. "
                    f"또한 *BOUNDARY_SPC의 constraint force가 과도하면 접촉면의 "
                    f"구속 노드에 비현실적인 힘이 집중됩니다. "
                    f"이러한 force spike는 인접 요소에 충격파를 전달하여 "
                    f"연쇄적인 요소 왜곡을 유발합니다."
                ),
                recommendation=(
                    f"1. Contact penalty stiffness 감소 — SLSFAC < 0.1 또는 "
                    f"SOFT=1(segment-based)로 전환하여 관통 시 접촉력을 완화. "
                    f"Segment-based contact는 k = min(k_slave, k_master)로 "
                    f"양측 강성을 고려하여 불균형 방지\n"
                    f"2. 초기 관통(initial penetration) 제거 — *CONTACT_..._에서 "
                    f"IGNORE=1로 초기 관통을 감지하고 출력, IGNORE=2로 관통을 "
                    f"자동 해소. *CONTROL_CONTACT의 PENOPT=4 권장\n"
                    f"3. Soft constraint 사용 — *CONSTRAINED_..._PENALTY로 경계조건을 "
                    f"penalty 기반으로 변환하면 급격한 force spike 방지\n"
                    f"4. 경계조건 중복 확인 — 같은 노드에 SPC + contact + "
                    f"*CONSTRAINED_*가 동시에 적용되면 과잉구속으로 "
                    f"비정상적 반력이 발생합니다"
                ),
            ))

        if oscillating_nodes:
            node_desc = ', '.join([f"Node {nid}" for nid in oscillating_nodes[:10]])
            if len(oscillating_nodes) > 10:
                node_desc += f" ... ({len(oscillating_nodes)} total)"

            findings.append(Finding(
                severity=Severity.WARNING,
                category="numerical_instability",
                title=f"Oscillating reaction force ({len(oscillating_nodes)} nodes)",
                description=(
                    f"{node_desc}의 반력이 진동합니다. "
                    f"반력 진동은 경계 노드에서 힘의 균형이 매 스텝마다 부호가 바뀌는 "
                    f"현상입니다. 명시적 적분에서 damping이 부족하면 접촉/구속 반력이 "
                    f"overshooting → correction → overshooting을 반복합니다. "
                    f"Courant 안정 조건(dt < L/c)에 가까울수록 에너지 분산이 "
                    f"심해져 수치적 진동이 증폭됩니다. "
                    f"quasi-static 해석에서는 관성력이 작아야 하지만, "
                    f"반력 진동은 동적 효과가 결과에 영향을 줌을 의미합니다."
                ),
                recommendation=(
                    f"1. Global damping 추가 — *DAMPING_GLOBAL로 시스템 전체에 "
                    f"점성 감쇠를 추가하여 진동 감소. 준정적 해석에서 특히 효과적\n"
                    f"2. Timestep 감소 — TSSFAC를 줄여 Courant 조건에 충분한 여유를 "
                    f"확보. dt가 안정 한계에 가까우면 수치 분산이 진동을 유발\n"
                    f"3. Contact damping 증가 — *CONTACT의 VDC(viscous damping "
                    f"coefficient) 파라미터로 접촉면에서의 진동을 감쇠. "
                    f"VDC=20~40이 일반적"
                ),
            ))

    except Exception:
        pass

    return findings


def _count_zero_crossings(signal: list[float]) -> int:
    """Count number of times signal crosses zero."""
    if len(signal) < 2:
        return 0

    crossings = 0
    for i in range(len(signal) - 1):
        if signal[i] * signal[i+1] < 0:  # Sign change
            crossings += 1

    return crossings


def _has_high_frequency_oscillation(signal: list[float]) -> bool:
    """Check if signal has high-frequency oscillation (simple heuristic)."""
    if len(signal) < 10:
        return False

    # Count direction changes (not zero-crossings)
    changes = 0
    for i in range(1, len(signal) - 1):
        # Check if signal changes direction (local min/max)
        if (signal[i] > signal[i-1] and signal[i] > signal[i+1]) or \
           (signal[i] < signal[i-1] and signal[i] < signal[i+1]):
            changes += 1

    # If more than 40% of points are local extrema → oscillating
    return changes / len(signal) > 0.4


# ========== glstat-based diagnostics ==========


def detect_hourglass_dominance(
    energy_snapshots: list[EnergySnapshot],
) -> list[Finding]:
    """
    Detect excessive hourglass energy (zero-energy mode).

    Hourglass energy > 10% of internal energy → WARNING
    Hourglass energy > 20% of internal energy → CRITICAL

    Hourglass modes are zero-energy deformation modes that don't contribute
    to stiffness but allow element distortion. Excessive hourglass energy
    indicates mesh instability and non-physical deformation.

    Args:
        energy_snapshots: Energy history from glstat

    Returns:
        list of Finding objects
    """
    findings: list[Finding] = []

    if not energy_snapshots or len(energy_snapshots) < 5:
        return findings

    final = energy_snapshots[-1]

    # Skip if internal energy is negligible
    if final.internal < 1e-9:
        return findings

    hg_ratio = final.hourglass / final.internal

    if hg_ratio > 0.20:
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="numerical_instability",
            title=f"Hourglass energy dominance ({hg_ratio:.1%})",
            description=(
                f"Hourglass 에너지가 내부 에너지의 {hg_ratio:.1%}를 차지합니다 "
                f"(HG={final.hourglass:.3E}, IE={final.internal:.3E}). "
                f"Hourglass mode는 reduced integration 요소(shell 1-point, solid 1-point)에서 "
                f"발생하는 zero-energy deformation mode입니다. 2×2 Gauss 적분 대신 "
                f"1-point 적분을 사용하면 강성 행렬의 rank가 부족해져(rank deficiency), "
                f"에너지 없이 변형되는 모드가 존재합니다. 예: 4노드 shell에서 hourglass "
                f"mode는 중앙은 고정되고 모서리가 교대로 상하 변형하는 패턴입니다. "
                f"HG/IE > 20%이면 해석 결과의 신뢰성이 없습니다. 변형 에너지의 상당 "
                f"부분이 비물리적 변형에 소비되어 응력/변형률 결과가 왜곡됩니다."
            ),
            recommendation=(
                f"1. Hourglass control type 변경 — IHQ=4(Flanagan-Belytschko "
                f"stiffness form)는 비점성 강성 기반으로 정적 해석에 적합. IHQ=8(Puso)은 "
                f"physical stabilization으로 전단 잠김(shear locking) 없이 hourglass 제어\n"
                f"2. Fully-integrated element 사용 — shell: ELFORM=16(4-point fully "
                f"integrated), solid: ELFORM=2(8-point selective reduced). Hourglass mode가 "
                f"원천 제거되나 계산 비용 2~5배 증가. 고변형 영역에만 선택적 적용 권장\n"
                f"3. QH/QM 계수 조정 — *HOURGLASS 키워드에서 QH(hourglass coefficient)를 "
                f"0.03~0.15 범위로 증가. 너무 크면(>0.15) 인공적 강성이 결과에 영향\n"
                f"4. 메시 세분화 — 고변형 영역의 요소를 2~3배 세분화하면 hourglass mode의 "
                f"파장이 짧아져 에너지 비율이 감소합니다"
            ),
        ))
    elif hg_ratio > 0.10:
        findings.append(Finding(
            severity=Severity.WARNING,
            category="numerical_instability",
            title=f"Elevated hourglass energy ({hg_ratio:.1%})",
            description=(
                f"Hourglass 에너지가 내부 에너지의 {hg_ratio:.1%}입니다 "
                f"(HG={final.hourglass:.3E}, IE={final.internal:.3E}). "
                f"일반적으로 HG/IE < 10%가 권장되며, 현재 값은 경계 수준입니다. "
                f"Reduced integration 요소의 zero-energy mode가 에너지를 소비하고 "
                f"있으나, 아직 결과에 심각한 영향을 주는 수준은 아닙니다. "
                f"그러나 시뮬레이션이 진행될수록 비율이 증가할 수 있습니다."
            ),
            recommendation=(
                f"1. Hourglass control 강화 — IHQ 값을 1→4 또는 4→8로 변경. "
                f"Stiffness-based(IHQ=4)가 viscous(IHQ=1)보다 정적 문제에 효과적\n"
                f"2. 변형이 큰 영역의 메시 확인 — 요소 종횡비(aspect ratio) > 5인 "
                f"요소가 hourglass mode에 취약합니다. 정방형에 가까운 메시 권장"
            ),
        ))

    return findings


def detect_excessive_mass_addition(
    energy_snapshots: list[EnergySnapshot],
) -> list[Finding]:
    """
    Detect excessive mass scaling (added mass).

    Mass scaling adds artificial mass to maintain target timestep.
    Excessive mass addition distorts dynamics and invalidates results.

    Added mass > 5% of original mass → WARNING
    Added mass > 10% of original mass → CRITICAL

    Args:
        energy_snapshots: Energy history from glstat

    Returns:
        list of Finding objects
    """
    findings: list[Finding] = []

    if not energy_snapshots or len(energy_snapshots) < 5:
        return findings

    # Mass is proportional to kinetic energy at same velocity
    # But we don't have mass directly in EnergySnapshot
    # Alternative: Check if timestep is suspiciously constant (DT2MS active)
    # For now, we'll note this requires additional data from d3hsp

    # TODO: This needs total_mass field added to EnergySnapshot
    # or access to d3hsp mass scaling info

    return findings


def detect_kinetic_energy_explosion(
    energy_snapshots: list[EnergySnapshot],
) -> list[Finding]:
    """
    Detect kinetic energy explosion (velocity divergence).

    Sudden KE increase indicates velocity instability:
    - KE increases 100× in short time → velocity divergence
    - KE >> IE in quasi-static problem → unphysical motion

    Args:
        energy_snapshots: Energy history from glstat

    Returns:
        list of Finding objects
    """
    findings: list[Finding] = []

    if not energy_snapshots or len(energy_snapshots) < 10:
        return findings

    # Check for sudden KE spike (within 10% of time span)
    window_size = max(10, len(energy_snapshots) // 10)

    for i in range(window_size, len(energy_snapshots)):
        recent_window = energy_snapshots[i-window_size:i+1]
        min_ke = min(s.kinetic for s in recent_window)
        max_ke = max(s.kinetic for s in recent_window)

        if min_ke > 1e-9 and max_ke / min_ke > 100:
            time_span = recent_window[-1].time - recent_window[0].time
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="numerical_instability",
                title=f"Kinetic energy explosion (100x in {time_span:.3E}s)",
                description=(
                    f"운동 에너지가 {time_span:.3E}초 동안 {max_ke/min_ke:.0f}배 증가했습니다 "
                    f"(KE: {min_ke:.3E} → {max_ke:.3E}). "
                    f"운동 에너지 KE = Σ(½mv²)가 급격히 증가한다는 것은 일부 노드의 "
                    f"속도가 발산(velocity divergence)했다는 의미입니다. "
                    f"명시적 적분에서 v(t+dt) = v(t) + (F/m)×dt로 업데이트하는데, "
                    f"F가 비정상적으로 크면(contact spike, constraint conflict) 한 스텝에서 "
                    f"속도가 급증하고, 이 노드가 인접 요소를 왜곡시켜 추가적인 "
                    f"penalty force를 생성하는 양성 피드백 루프가 형성됩니다. "
                    f"100배 이상의 KE 증가는 시뮬레이션이 발산 단계에 진입했음을 "
                    f"나타내며, 이후 NaN 또는 negative volume 에러로 이어집니다."
                ),
                recommendation=(
                    f"1. 발산 시점(t={recent_window[0].time:.3E}s) 전후의 변형 확인 — "
                    f"애니메이션에서 비정상적으로 빠르게 움직이는 노드/파트 식별\n"
                    f"2. Constraint 정의 점검 — *CONSTRAINED_EXTRA_NODES, "
                    f"*CONSTRAINED_RIGID_BODIES 등에서 과잉 구속 확인. 같은 노드에 "
                    f"여러 구속이 적용되면 내부적으로 상반되는 힘이 생성\n"
                    f"3. 접촉 초기 관통 제거 — 관통된 노드에 과도한 penalty force가 "
                    f"집중되어 속도 발산의 주요 원인. *CONTROL_CONTACT의 PENOPT 설정\n"
                    f"4. Penalty stiffness 감소 — SLSFAC < 0.1로 설정하여 "
                    f"접촉력 크기를 완화. SOFT=1(segment-based) 사용 권장"
                ),
            ))
            break  # Report only first occurrence

    # Check KE/IE ratio for quasi-static problems
    final = energy_snapshots[-1]
    if final.internal > 1e-9:
        ke_ie_ratio = final.kinetic / final.internal

        # In quasi-static: KE << IE (typically KE < 0.1 × IE)
        # In dynamic: KE ≈ IE is normal
        # If KE >> IE: likely unphysical motion or instability
        if ke_ie_ratio > 10.0:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="numerical_instability",
                title=f"Kinetic energy dominates (KE/IE = {ke_ie_ratio:.1f})",
                description=(
                    f"운동 에너지가 내부 에너지의 {ke_ie_ratio:.1f}배입니다 "
                    f"(KE={final.kinetic:.3E}, IE={final.internal:.3E}). "
                    f"준정적(quasi-static) 해석에서는 관성 효과가 무시될 수 있어야 하므로 "
                    f"KE/IE < 0.1 (10% 미만)이 권장됩니다. 현재 KE/IE = {ke_ie_ratio:.1f}은 "
                    f"동적 효과가 결과를 지배하고 있음을 의미합니다. "
                    f"이는 하중 속도가 너무 빠르거나(loading rate), 구속 부족으로 "
                    f"rigid body mode가 발생했기 때문일 수 있습니다. "
                    f"충격 해석(crash, impact)에서는 KE ≈ IE가 정상입니다."
                ),
                recommendation=(
                    f"1. 시뮬레이션 유형 확인 — 동적(crash/impact)이면 KE > IE는 정상. "
                    f"준정적(forming, squeeze)이면 아래 조치 필요\n"
                    f"2. 하중 속도(loading rate) 감소 — 준정적 해석에서 *BOUNDARY_PRESCRIBED"
                    f"_MOTION의 속도를 줄이거나 하중 시간을 늘려 관성 효과 최소화\n"
                    f"3. Rigid body mode 확인 — 구속이 부족하면(under-constrained) "
                    f"자유 운동이 발생하여 KE가 증가합니다. 6개 자유도를 "
                    f"충분히 구속했는지 확인"
                ),
            ))

    return findings


def detect_contact_energy_anomaly(
    energy_snapshots: list[EnergySnapshot],
) -> list[Finding]:
    """
    Detect abnormal contact energy patterns.

    Contact sliding energy > 30% of internal energy → WARNING
    Contact energy sudden spike → penetration issue

    Args:
        energy_snapshots: Energy history from glstat

    Returns:
        list of Finding objects
    """
    findings: list[Finding] = []

    if not energy_snapshots or len(energy_snapshots) < 5:
        return findings

    final = energy_snapshots[-1]

    # Check excessive sliding energy
    if final.internal > 1e-9:
        slide_ratio = final.sliding_interface / final.internal

        if slide_ratio > 0.30:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="numerical_instability",
                title=f"Excessive contact sliding energy ({slide_ratio:.1%})",
                description=(
                    f"Contact sliding 에너지가 내부 에너지의 {slide_ratio:.1%}입니다 "
                    f"(Slide={final.sliding_interface:.3E}, IE={final.internal:.3E}). "
                    f"접촉 슬라이딩 에너지는 E_slide = Σ(F_friction × δ_slide)로 계산되며, "
                    f"접촉면에서 마찰력에 의해 소산되는 에너지입니다. "
                    f"Slide/IE > 30%이면 에너지 균형에서 접촉 거동이 과도한 비중을 차지하며, "
                    f"이는 마찰 계수가 비현실적으로 높거나, penalty contact에서 비정상적 "
                    f"슬라이딩이 발생하거나, 과도한 관통 후 반발로 인한 것입니다. "
                    f"접촉 에너지는 내부 에너지(변형 에너지)로 전환되어야 하는 에너지가 "
                    f"마찰 소산으로 손실되는 것이므로, 구조물의 변형 응답이 과소평가됩니다."
                ),
                recommendation=(
                    f"1. 마찰 계수(FS) 확인 — *CONTACT의 FS(정마찰), FD(동마찰)가 "
                    f"재료 쌍에 적합한지 검증. 일반적으로 금속-금속: 0.1~0.3, "
                    f"고무-금속: 0.5~0.8\n"
                    f"2. Contact penalty 설정 검토 — penalty stiffness가 너무 높으면 "
                    f"관통-반발 사이클에서 과도한 에너지가 접촉면에 집중. "
                    f"SLSFAC < 0.1 또는 SOFT=1 사용\n"
                    f"3. 초기 관통 제거 — 관통된 노드가 penalty force에 의해 튕겨나가면서 "
                    f"마찰 에너지가 비정상적으로 증가합니다\n"
                    f"4. Contact type 재검토 — sliding contact 대신 tied contact가 "
                    f"적합한 인터페이스는 *CONTACT_TIED_...로 변경"
                ),
            ))

    # Check for contact energy spike
    if len(energy_snapshots) > 10:
        window_size = max(10, len(energy_snapshots) // 10)
        for i in range(window_size, len(energy_snapshots)):
            recent = energy_snapshots[i-window_size:i+1]
            min_slide = min(s.sliding_interface for s in recent)
            max_slide = max(s.sliding_interface for s in recent)

            if min_slide > 1e-9 and max_slide / min_slide > 50:
                time_span = recent[-1].time - recent[0].time
                findings.append(Finding(
                    severity=Severity.CRITICAL,
                    category="numerical_instability",
                    title=f"Contact energy spike (50x in {time_span:.3E}s)",
                    description=(
                        f"Contact sliding 에너지가 {time_span:.3E}초 동안 "
                        f"{max_slide/min_slide:.0f}배 급증했습니다 "
                        f"({min_slide:.3E} → {max_slide:.3E}). "
                        f"접촉 에너지의 급격한 증가는 다수의 노드가 동시에 접촉면을 "
                        f"심하게 관통한 후 penalty force에 의해 반발되는 과정에서 "
                        f"발생합니다. Penalty method에서 접촉력 F = k × g (g=관통깊이)이므로, "
                        f"관통이 깊어지면 힘이 급격히 증가하고, 이 힘에 의한 슬라이딩이 "
                        f"에너지를 급증시킵니다. 이는 곧 요소 왜곡과 timestep 감소로 이어져 "
                        f"시뮬레이션 불안정의 전조 증상입니다."
                    ),
                    recommendation=(
                        f"1. 시간 {recent[0].time:.3E}s 전후의 접촉 관통 확인 — "
                        f"후처리기에서 접촉 관통 깊이(penetration depth) 시각화\n"
                        f"2. Penalty factor 감소 — SLSFAC 값을 줄여 관통 시 "
                        f"반발력을 완화하고, SOFT=1(segment-based) 사용으로 "
                        f"양면 강성을 고려한 균형 잡힌 접촉력 적용\n"
                        f"3. Contact stiffness 재조정 — *CONTACT의 SFS/SFM "
                        f"(slave/master scale factor)로 접촉면별 강성 조절"
                    ),
                ))
                break

    return findings


def detect_timestep_volatility(
    energy_snapshots: list[EnergySnapshot],
) -> list[Finding]:
    """
    Detect sudden timestep changes (volatility).

    Sudden timestep changes indicate numerical instability precursors:
    - dt drops 10× within short period → instability starting
    - Frequent dt fluctuations → marginal stability

    Args:
        energy_snapshots: Energy history from glstat

    Returns:
        list of Finding objects
    """
    findings: list[Finding] = []

    if not energy_snapshots or len(energy_snapshots) < 20:
        return findings

    # Check for sudden dt drop (compare consecutive windows)
    window_size = max(5, len(energy_snapshots) // 20)

    for i in range(window_size, len(energy_snapshots) - window_size):
        prev_window = energy_snapshots[i-window_size:i]
        next_window = energy_snapshots[i:i+window_size]

        prev_dt = [s.timestep for s in prev_window if s.timestep > 0]
        next_dt = [s.timestep for s in next_window if s.timestep > 0]

        if not prev_dt or not next_dt:
            continue

        avg_prev = sum(prev_dt) / len(prev_dt)
        avg_next = sum(next_dt) / len(next_dt)

        if avg_prev > 0 and avg_next > 0 and avg_prev / avg_next >= 10:
            time_span = energy_snapshots[i+window_size-1].time - energy_snapshots[i-window_size].time
            findings.append(Finding(
                severity=Severity.WARNING,
                category="numerical_instability",
                title=f"Timestep sudden drop (10x in {time_span:.3E}s)",
                description=(
                    f"Timestep이 {time_span:.3E}초 동안 {avg_prev/avg_next:.1f}배 감소했습니다 "
                    f"(dt: {avg_prev:.3E} → {avg_next:.3E}). "
                    f"명시적 시간 적분에서 안정 timestep은 dt = TSSFAC × L_char / c로 "
                    f"결정됩니다(L_char=요소 특성 길이, c=음속). dt의 급격한 감소는 "
                    f"특정 요소의 L_char이 급격히 줄어들었음을 의미하며, 이는 "
                    f"심한 요소 왜곡(squeezing, shearing)이 발생했다는 것입니다. "
                    f"Timestep이 10배 이상 감소하면 계산 비용이 10배 증가할 뿐 아니라, "
                    f"요소 왜곡이 더 심해져 연쇄적 timestep 감소(timestep collapse)의 "
                    f"전조 증상입니다. 조치 없이 진행하면 negative volume 에러로 "
                    f"시뮬레이션이 종료될 가능성이 높습니다."
                ),
                recommendation=(
                    f"1. 시간 {energy_snapshots[i].time:.3E}s 전후의 변형 확인 — "
                    f"후처리기에서 요소 품질(aspect ratio, Jacobian) 시각화하여 "
                    f"왜곡되는 요소 식별\n"
                    f"2. 요소 침식(erosion) 설정 — *MAT_ADD_EROSION으로 과도하게 "
                    f"왜곡된 요소를 자동 삭제. MXEPS(최대 유효 소성 변형률)를 "
                    f"재료에 맞게 설정 (예: 강재 0.3~0.5, 알루미늄 0.15~0.3)\n"
                    f"3. *CONTROL_TIMESTEP의 ERODE=1 — dt < TSMIN인 요소를 "
                    f"자동 삭제하여 timestep collapse 방지\n"
                    f"4. 관련 파트의 메시 품질 개선 — 초기 요소 종횡비(aspect ratio) "
                    f"< 3, warpage < 15도, Jacobian > 0.5 확인"
                ),
            ))
            break  # Report only first occurrence

    # Check for frequent fluctuations (oscillating dt)
    if len(energy_snapshots) > 50:
        dt_values = [s.timestep for s in energy_snapshots if s.timestep > 0]
        if len(dt_values) > 20:
            # Count direction changes in dt
            changes = 0
            for i in range(1, len(dt_values) - 1):
                if (dt_values[i] > dt_values[i-1] and dt_values[i] > dt_values[i+1]) or \
                   (dt_values[i] < dt_values[i-1] and dt_values[i] < dt_values[i+1]):
                    changes += 1

            # If more than 30% of points are local extrema → oscillating
            if changes / len(dt_values) > 0.3:
                mean_dt = sum(dt_values) / len(dt_values)
                findings.append(Finding(
                    severity=Severity.INFO,
                    category="numerical_instability",
                    title=f"Timestep oscillation detected",
                    description=(
                        f"Timestep이 빈번하게 변동합니다 (평균={mean_dt:.3E}). "
                        f"dt 진동은 시뮬레이션이 안정성 경계(stability boundary)에서 "
                        f"작동하고 있음을 나타냅니다. dt = TSSFAC × L/c에서 요소가 "
                        f"변형 → 복원을 반복하면 L_char이 진동하여 dt도 진동합니다. "
                        f"이는 접촉면에서 관통/반발 사이클, 또는 탄성 반발이 "
                        f"반복되는 영역에서 흔히 발생합니다. "
                        f"dt 진동 자체는 즉각적인 위험은 아니지만, mass scaling "
                        f"(DT2MS)이 활성화되어 있으면 진동하는 요소에 "
                        f"과도한 질량이 추가될 수 있습니다."
                    ),
                    recommendation=(
                        f"1. 변형이 큰 영역의 메시 개선 — 요소 종횡비를 개선하여 "
                        f"변형 시에도 L_char의 변동을 최소화\n"
                        f"2. Contact 설정 재검토 — 관통/반발 사이클이 원인이면 "
                        f"contact damping(VDC) 추가하여 진동 감쇠\n"
                        f"3. Mass scaling 검토 — DT2MS 설정 시 dt 진동 영역의 "
                        f"요소에 과도한 질량이 추가되지 않는지 확인. "
                        f"m_added = m × ((dt_target/dt_element)² - 1)"
                    ),
                ))

    return findings


# ========== NaN / Negative energy diagnostics ==========


def detect_nan_in_energy(
    energy_snapshots: list[EnergySnapshot],
) -> list[Finding]:
    """
    Detect NaN values in glstat energy data.

    NaN in energy fields means the simulation has diverged irreversibly.
    Once NaN appears, all subsequent calculations produce NaN (NaN propagation).

    Args:
        energy_snapshots: Energy history from glstat

    Returns:
        list of Finding objects
    """
    findings: list[Finding] = []

    if not energy_snapshots:
        return findings

    # Find the first snapshot with NaN
    first_nan_idx = None
    for i, snap in enumerate(energy_snapshots):
        if snap.has_nan:
            first_nan_idx = i
            break

    if first_nan_idx is None:
        return findings

    first_nan = energy_snapshots[first_nan_idx]
    total_snapshots = len(energy_snapshots)
    nan_count = sum(1 for s in energy_snapshots if s.has_nan)

    # Get pre-NaN snapshot for context
    pre_nan_desc = ""
    if first_nan_idx > 0:
        prev = energy_snapshots[first_nan_idx - 1]
        pre_nan_desc = (
            f"NaN 발생 직전(cycle {prev.cycle}): "
            f"KE={prev.kinetic:.3E}, IE={prev.internal:.3E}, "
            f"energy_ratio={prev.energy_ratio:.4f}, dt={prev.timestep:.3E}. "
        )

    findings.append(Finding(
        severity=Severity.CRITICAL,
        category="numerical_instability",
        title=f"NaN detected in energy (cycle {first_nan.cycle})",
        description=(
            f"Cycle {first_nan.cycle} (t={first_nan.time:.3E}s)에서 에너지 값이 NaN이 되었습니다. "
            f"이후 {nan_count}개 스냅샷(전체 {total_snapshots}개 중)이 NaN입니다. "
            f"{pre_nan_desc}"
            f"NaN(Not a Number)은 IEEE 754 부동소수점 연산에서 0/0, ∞-∞, √(-x) 등 "
            f"정의되지 않는 연산의 결과입니다. LS-DYNA에서 NaN 발생은 주로: "
            f"(1) negative volume 요소에서 det(J) < 0으로 음속 c = √(K/ρ)가 "
            f"허수가 되거나, (2) 노드 좌표가 ±∞로 발산한 후 후속 연산에서 발생합니다. "
            f"NaN은 전파성이 있어(NaN + x = NaN, NaN × x = NaN), 한 번 발생하면 "
            f"모든 후속 에너지 계산이 NaN으로 오염되어 시뮬레이션이 의미를 잃습니다. "
            f"LS-DYNA R16+에서는 *CONTROL_CHECK_NAN으로 NaN 발생 시 자동 종료 가능합니다."
        ),
        recommendation=(
            f"1. NaN 발생 직전 시점(cycle {first_nan.cycle - 1 if first_nan_idx > 0 else 0}) "
            f"의 변형 확인 — 후처리기에서 과도하게 왜곡된 요소/발산하는 노드 식별\n"
            f"2. *CONTROL_CHECK_NAN 추가 — NaN 발생 시 자동 종료하여 "
            f"원인 시점을 정확히 파악 가능 (R16 이상)\n"
            f"3. Negative volume 방지 — *CONTROL_TIMESTEP의 ERODE=1로 "
            f"과도 왜곡 요소 자동 삭제, 또는 *MAT_ADD_EROSION으로 "
            f"변형률 기준 erosion 설정\n"
            f"4. 접촉 설정 재검토 — penalty stiffness 감소(SLSFAC < 0.1), "
            f"초기 관통 제거, SOFT=1(segment-based) 사용\n"
            f"5. Single precision 사용 시 double precision 전환 고려 — "
            f"SP에서는 부동소수점 overflow가 더 빨리 발생 (max ~3.4E38 vs DP ~1.8E308)"
        ),
    ))

    return findings


def detect_negative_energy_components(
    energy_snapshots: list[EnergySnapshot],
) -> list[Finding]:
    """
    Detect negative energy components that should be non-negative.

    Negative sliding interface energy is physically impossible and indicates
    severe contact instability. Negative internal energy indicates
    non-physical material behavior.

    Args:
        energy_snapshots: Energy history from glstat

    Returns:
        list of Finding objects
    """
    findings: list[Finding] = []

    if not energy_snapshots:
        return findings

    # Check for negative sliding interface energy
    worst_slide = None
    worst_slide_snap = None
    for snap in energy_snapshots:
        if snap.has_nan:
            continue
        if snap.sliding_interface < -1e-6:
            if worst_slide is None or snap.sliding_interface < worst_slide:
                worst_slide = snap.sliding_interface
                worst_slide_snap = snap

    if worst_slide_snap is not None:
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="numerical_instability",
            title=f"Negative sliding interface energy ({worst_slide:.3E})",
            description=(
                f"Cycle {worst_slide_snap.cycle} (t={worst_slide_snap.time:.3E}s)에서 "
                f"sliding interface energy = {worst_slide:.3E}입니다. "
                f"접촉 슬라이딩 에너지 E_slide = Σ(F_contact × δ_slide)는 "
                f"마찰에 의한 에너지 소산이므로 항상 양수(≥0)여야 합니다. "
                f"음의 접촉 에너지는 penalty contact에서 비정상적인 에너지 생성을 "
                f"의미하며, 접촉면에서 인공적으로 에너지가 시스템에 주입되고 있습니다. "
                f"이는 주로 penalty stiffness가 과도하여 관통-반발 사이클에서 "
                f"접촉력이 오버슈팅하거나, tied contact에서 풀린 노드가 "
                f"비정상적인 penalty force를 받을 때 발생합니다. "
                f"음의 접촉 에너지는 energy ratio를 1.0 이상으로 증가시켜 "
                f"에너지 비보존을 유발하며, 시뮬레이션 결과의 신뢰성을 손상시킵니다."
            ),
            recommendation=(
                f"1. Penalty stiffness 감소 — SLSFAC를 0.05~0.1로 설정하여 "
                f"접촉력의 오버슈팅 방지. k_contact = fs × K × A²/V에서 "
                f"fs(SLSFAC)를 줄이면 관통 시 반발력이 완화됨\n"
                f"2. SOFT=1 (segment-based contact) 사용 — 양측 표면의 "
                f"강성을 고려하여 균형 잡힌 접촉력 적용. SOFT=2(pinball)도 고려\n"
                f"3. Contact type 변경 — AUTOMATIC_SURFACE_TO_SURFACE 대신 "
                f"MORTAR contact 사용 검토. Mortar은 에너지 보존이 우수\n"
                f"4. 초기 관통 제거 — 초기 관통이 있으면 첫 스텝에서 과도한 "
                f"penalty force → 반발 → 음의 에너지 생성 사이클 유발\n"
                f"5. Contact damping(VDC) 추가 — VDC=20~40으로 접촉면 "
                f"진동을 감쇠하여 에너지 생성 방지"
            ),
        ))

    # Check for negative internal energy
    worst_ie = None
    worst_ie_snap = None
    for snap in energy_snapshots:
        if snap.has_nan:
            continue
        if snap.internal < -1e-6:
            if worst_ie is None or snap.internal < worst_ie:
                worst_ie = snap.internal
                worst_ie_snap = snap

    if worst_ie_snap is not None:
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="numerical_instability",
            title=f"Negative internal energy ({worst_ie:.3E})",
            description=(
                f"Cycle {worst_ie_snap.cycle} (t={worst_ie_snap.time:.3E}s)에서 "
                f"internal energy = {worst_ie:.3E}입니다. "
                f"내부 에너지(internal energy)는 변형 에너지 W = Σ∫σ:dε × V로 "
                f"계산되며, 이는 물리적으로 항상 양수(≥0)여야 합니다. "
                f"음의 내부 에너지는 재료 모델이 비물리적 응력-변형률 관계를 "
                f"생성하거나, 요소 왜곡이 심하여 적분점에서의 계산이 "
                f"올바르지 않음을 나타냅니다. 이는 곧 시뮬레이션 발산으로 이어집니다."
            ),
            recommendation=(
                f"1. 재료 모델 입력 검증 — 탄성 계수(E), 포아송 비(ν), "
                f"항복 응력(σ_y) 등이 단위 체계에 맞는지 확인\n"
                f"2. 요소 erosion 설정 — *MAT_ADD_EROSION으로 과도 변형 시 "
                f"요소 삭제. 음의 IE를 생성하는 요소를 제거\n"
                f"3. 요소 formulation 변경 — 고변형 영역에 fully-integrated "
                f"요소(ELFORM=2/16) 사용하여 정확한 적분"
            ),
        ))

    return findings


def diagnose_slurm_failures(
    slurm_info: SlurmJobInfo | None,
) -> list[Finding]:
    """
    Generate diagnostic findings from Slurm job errors.

    Covers: segmentation faults, MPI errors, exit codes.

    Args:
        slurm_info: Parsed Slurm job error information

    Returns:
        list of Finding objects
    """
    findings: list[Finding] = []

    if slurm_info is None:
        return findings

    # Segmentation fault
    if slurm_info.has_segfault:
        stack_info = ""
        if slurm_info.stack_trace:
            stack_info = f" Stack trace ({len(slurm_info.stack_trace)} frames): {slurm_info.stack_trace[0]}"

        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="slurm_failure",
            title=f"Segmentation fault (Signal {slurm_info.signal})",
            description=(
                f"LS-DYNA 프로세스가 Segmentation fault (Signal 11)로 비정상 종료되었습니다. "
                f"Slurm job {slurm_info.job_id}, 노드: {slurm_info.node_name or 'unknown'}. "
                f"{stack_info} "
                f"Segmentation fault는 프로세스가 할당되지 않은 메모리 영역에 접근할 때 "
                f"OS가 보내는 SIGSEGV(Signal 11) 신호입니다. LS-DYNA에서 이는 주로: "
                f"(1) 메모리 부족으로 배열 경계를 초과한 접근, "
                f"(2) 극심한 요소 왜곡으로 내부 데이터 구조가 손상, "
                f"(3) NaN 전파로 인덱싱 연산이 비정상적 메모리 주소 참조, "
                f"(4) MPI 도메인 분해에서 프로세서 간 데이터 불일치 등으로 발생합니다. "
                f"d3hsp 파일이 불완전하게 종료된 경우(termination message 없음), "
                f"이 segfault가 종료 원인입니다."
            ),
            recommendation=(
                f"1. 메모리 증가 — LS-DYNA 입력에서 memory=4000m 등으로 메모리 할당 증가. "
                f"메모리 부족이 가장 흔한 segfault 원인\n"
                f"2. d3hsp 분석 — d3hsp 파일의 마지막 경고/에러 메시지 확인. "
                f"segfault 직전에 negative volume, NaN 등의 경고가 있었을 수 있음\n"
                f"3. 요소 erosion 설정 — 요소 왜곡에 의한 메모리 손상 방지를 위해 "
                f"*MAT_ADD_EROSION 또는 *CONTROL_TIMESTEP ERODE=1 설정\n"
                f"4. 접촉 설정 완화 — penalty stiffness 감소, SOFT=1 사용, "
                f"초기 관통 제거로 극심한 왜곡 방지\n"
                f"5. Double precision 사용 — SP(single precision)에서 DP로 전환하면 "
                f"부동소수점 overflow에 의한 비정상 메모리 접근 방지"
            ),
        ))

    # MPI errors
    if slurm_info.has_mpi_error:
        mpi_msgs = [m for m in slurm_info.error_messages
                     if 'MPI' in m or 'mpi' in m.lower()]
        msg_desc = '; '.join(mpi_msgs[:3]) if mpi_msgs else "MPI error"

        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="slurm_failure",
            title=f"MPI communication error",
            description=(
                f"MPI 통신 오류가 발생했습니다: {msg_desc}. "
                f"Slurm job {slurm_info.job_id}, 노드: {slurm_info.node_name or 'unknown'}. "
                f"MPI(Message Passing Interface) 오류는 MPP(Massively Parallel Processing) "
                f"실행에서 프로세서 간 통신이 실패한 것입니다. "
                f"MPI_ERR_TRUNCATE는 수신 버퍼보다 큰 메시지가 도착했을 때 발생하며, "
                f"이는 도메인 분해 경계에서 데이터 크기 불일치를 의미합니다. "
                f"MPI_Allreduce에서 발생하면 전체 프로세서의 글로벌 합산(에너지, 질량 등) "
                f"연산이 실패한 것으로, 한 프로세서에서 비정상적으로 큰 값이나 NaN이 "
                f"발생하여 통신 데이터 크기가 예상과 달라진 것이 원인입니다."
            ),
            recommendation=(
                f"1. 프로세서 수 줄이기 — MPP에서 프로세서 수가 많으면 "
                f"도메인 경계면이 증가하여 통신 부하와 오류 확률 증가. "
                f"예: -np 4 → -np 2로 줄여서 테스트\n"
                f"2. 메모리 증가 — memory= 파라미터를 2배로 증가시켜 "
                f"MPI 버퍼 부족 방지\n"
                f"3. 도메인 분해 재검토 — *CONTROL_MPP_DECOMPOSITION 또는 "
                f"MPP 도메인 분해 설정에서 프로세서별 부하 균형 확인\n"
                f"4. 입력 파일에서 수치 불안정 원인 제거 — MPI 오류는 "
                f"종종 한 프로세서에서 발생한 수치 발산(NaN, overflow)이 "
                f"통신 오류로 나타난 것. 위의 접촉/요소 설정 권장사항 적용"
            ),
        ))

    # MPI_ABORT
    if slurm_info.has_mpi_abort and not slurm_info.has_mpi_error:
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="slurm_failure",
            title="MPI_ABORT — process terminated",
            description=(
                f"MPI_ABORT가 호출되어 모든 MPI 프로세스가 종료되었습니다. "
                f"Slurm job {slurm_info.job_id}. "
                f"MPI_ABORT는 한 프로세스에서 복구 불가능한 오류가 발생하여 "
                f"전체 병렬 실행을 강제 종료시킨 것입니다. 이는 주로 LS-DYNA 내부 "
                f"에러 처리에서 호출되며, d3hsp 파일의 에러 메시지에서 "
                f"구체적인 원인을 확인할 수 있습니다."
            ),
            recommendation=(
                f"1. d3hsp 파일의 에러/경고 메시지 확인 — MPI_ABORT 전에 발생한 "
                f"LS-DYNA 에러가 실제 원인\n"
                f"2. SMP(공유 메모리 병렬) 모드로 테스트 — MPI 관련 문제를 "
                f"배제하기 위해 단일 프로세서 또는 SMP로 실행 테스트"
            ),
        ))

    # Non-zero exit code (without segfault/MPI — pure LS-DYNA error termination)
    if slurm_info.exit_code > 0 and not slurm_info.has_segfault and not slurm_info.has_mpi_error:
        findings.append(Finding(
            severity=Severity.CRITICAL if slurm_info.exit_code == 3 else Severity.WARNING,
            category="slurm_failure",
            title=f"LS-DYNA exit code {slurm_info.exit_code}",
            description=(
                f"LS-DYNA가 exit code {slurm_info.exit_code}로 종료되었습니다. "
                f"Slurm job {slurm_info.job_id}. "
                f"Exit code 3은 LS-DYNA의 표준 에러 종료(error termination)로, "
                f"d3hsp 파일에 기록된 에러 메시지에 의해 시뮬레이션이 중단된 것입니다. "
                f"일반적인 원인: negative volume(Error 40509), NaN detected(Error 40456), "
                f"constraint matrix singular(Error 30358) 등. "
                f"d3hsp의 termination 섹션과 에러/경고 카운트를 통해 "
                f"정확한 원인을 파악할 수 있습니다."
            ),
            recommendation=(
                f"1. d3hsp 파일의 'E r r o r' 메시지 확인 — 에러 코드별 대응\n"
                f"2. 이 도구의 다른 진단 결과 참조 — 에너지 불안정, timestep 붕괴, "
                f"경고 패턴 등이 종료 원인을 설명합니다"
            ),
        ))

    return findings
