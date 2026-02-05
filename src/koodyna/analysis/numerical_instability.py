"""Detection of numerical instabilities from nodout, bndout, and glstat data."""

from pathlib import Path
from koodyna.models import Finding, Severity, EnergySnapshot
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
                    f"비정상적으로 큰 속도는 수치적 불안정성을 나타냅니다. "
                    f"일반적으로 constraint 오류, 과도한 접촉 관통, 또는 "
                    f"너무 강한 penalty stiffness가 원인입니다."
                ),
                recommendation=(
                    f"1. 해당 노드가 포함된 *CONSTRAINED_* 정의 점검\n"
                    f"2. Contact interface 설정 확인 (초기 관통 제거)\n"
                    f"3. Penalty stiffness 감소 (SLSFAC < 0.1)\n"
                    f"4. 중복된 constraint 제거"
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
                    f"고주파 진동은 timestep이 너무 크거나 hourglass control이 "
                    f"부적절함을 나타냅니다. 일반 구조 진동(100-1000 Hz)을 "
                    f"크게 초과하는 비물리적 진동입니다."
                ),
                recommendation=(
                    f"1. Timestep 감소 (TSSFAC를 0.67에서 0.5로 줄이기)\n"
                    f"2. Hourglass control 강화 (IHQ=4 또는 8 사용)\n"
                    f"3. Fully-integrated element 시도 (ELFORM=2)\n"
                    f"4. 해당 영역 메시 품질 확인"
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
                    f"반력이 평균의 {spike_ratio:.0f}배 이상으로 급증했습니다. "
                    f"이는 penalty contact의 과도한 stiffness 또는 "
                    f"초기 관통(initial penetration)을 나타냅니다."
                ),
                recommendation=(
                    f"1. Contact penalty factor 감소 (SLSFAC < 0.1)\n"
                    f"2. 초기 관통 제거 (*CONTACT_...에서 간섭 확인)\n"
                    f"3. Soft constraint 사용 고려 (*CONSTRAINED_..._PENALTY)\n"
                    f"4. 경계조건 중복 확인"
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
                    f"Timestep이 너무 크거나 damping이 부족합니다."
                ),
                recommendation=(
                    f"1. Global damping 추가 (*DAMPING_GLOBAL)\n"
                    f"2. Timestep 감소 (TSSFAC 줄이기)\n"
                    f"3. Contact damping 증가 (*CONTACT의 VDC 파라미터)"
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
                f"Hourglass mode(zero-energy mode)가 지배적이며, "
                f"요소 변형이 비물리적입니다."
            ),
            recommendation=(
                f"1. Hourglass control 강화 (IHQ=4 또는 8)\n"
                f"2. Fully-integrated element 사용 (ELFORM=2 for shells, ELFORM=1 for solids)\n"
                f"3. 메시 세분화 (특히 고변형 영역)\n"
                f"4. QH/QM 설정 확인 (*HOURGLASS 키워드)"
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
                f"Hourglass control이 부족할 수 있습니다."
            ),
            recommendation=(
                f"1. Hourglass control 강화 (IHQ 값 증가)\n"
                f"2. 변형이 큰 영역의 메시 확인"
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
                    f"전역적 속도 발산(velocity divergence)을 나타냅니다."
                ),
                recommendation=(
                    f"1. Constraint 정의 점검 (*CONSTRAINED_*)\n"
                    f"2. 초기 관통 제거 (contact interfaces)\n"
                    f"3. Penalty stiffness 감소\n"
                    f"4. 경계조건 충돌 확인"
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
                    f"준정적 문제라면 비정상적으로 큰 운동입니다."
                ),
                recommendation=(
                    f"1. 시뮬레이션 유형 확인 (동적 vs 준정적)\n"
                    f"2. 준정적이라면: 경계조건과 하중 속도 검토\n"
                    f"3. Rigid body mode 의심 (under-constrained)"
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
                    f"과도한 마찰 또는 비정상적 접촉 거동을 나타냅니다."
                ),
                recommendation=(
                    f"1. 마찰계수(FS) 확인 (과도하게 높지 않은지)\n"
                    f"2. Contact penalty 설정 검토\n"
                    f"3. 초기 관통 제거\n"
                    f"4. Contact type 재검토 (sliding vs tied)"
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
                        f"Contact sliding 에너지가 {time_span:.3E}초 동안 급증했습니다 "
                        f"({min_slide:.3E} → {max_slide:.3E}). "
                        f"과도한 관통 또는 penalty contact 문제를 나타냅니다."
                    ),
                    recommendation=(
                        f"1. Contact 관통 확인 (initial penetration)\n"
                        f"2. Penalty factor 감소 (SLSFAC)\n"
                        f"3. Contact stiffness 재조정"
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
                    f"수치 불안정성의 전조 증상일 수 있습니다."
                ),
                recommendation=(
                    f"1. 시간 {energy_snapshots[i].time:.3E}s 전후의 변형 확인 (애니메이션)\n"
                    f"2. 관련 파트의 메시 품질 확인\n"
                    f"3. Contact 관통 여부 확인\n"
                    f"4. Timestep collapse 방지 조치 필요"
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
                        f"시뮬레이션이 안정성 경계에서 작동하고 있을 수 있습니다."
                    ),
                    recommendation=(
                        f"1. 변형이 큰 영역의 메시 개선\n"
                        f"2. Contact 설정 재검토\n"
                        f"3. Mass scaling 검토 (DT2MS 설정)"
                    ),
                ))

    return findings
