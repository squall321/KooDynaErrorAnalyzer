"""Detection of numerical instabilities from nodout and bndout data."""

from pathlib import Path
from koodyna.models import Finding, Severity
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
