"""Performance profiling analysis for LS-DYNA simulation results."""

import math

from koodyna.models import (
    PerformanceTiming, MPPProcessorTiming, LoadProfileEntry,
    ScalingProjection, Finding, Severity,
)

MPP_IMBALANCE_WARN = 0.15   # 15% CPU imbalance
SHARING_OVERHEAD_WARN = 0.25  # 25% overhead in sharing


def analyze_performance(
    timing: list[PerformanceTiming],
    mpp_timing: list[MPPProcessorTiming],
    load_profile_pct: list[LoadProfileEntry],
) -> list[Finding]:
    """Analyze simulation performance and identify bottlenecks."""
    findings: list[Finding] = []

    # Identify bottleneck components (> 25% of clock time)
    for pt in timing:
        if pt.clock_percent > 25:
            findings.append(Finding(
                severity=Severity.INFO,
                category="performance",
                title=f"{pt.component} is the primary cost ({pt.clock_percent:.1f}%)",
                description=(
                    f"{pt.component}: {pt.clock_seconds:.1f}s "
                    f"({pt.clock_percent:.1f}% of clock time). "
                    f"CPU: {pt.cpu_seconds:.1f}s ({pt.cpu_percent:.1f}%)."
                ),
                recommendation="",
            ))

    # Sharing overhead analysis
    sharing_total = sum(
        pt.clock_percent for pt in timing
        if "sharing" in pt.component.lower() or "shr" in pt.component.lower()
    )
    if sharing_total > SHARING_OVERHEAD_WARN * 100:
        findings.append(Finding(
            severity=Severity.WARNING,
            category="performance",
            title=f"High MPI sharing overhead ({sharing_total:.1f}%)",
            description=(
                f"Total sharing overhead is {sharing_total:.1f}% of clock time. "
                f"This suggests excessive inter-process communication."
            ),
            recommendation=(
                "Consider reducing the number of MPI processes or using "
                "a better decomposition. High sharing overhead often occurs "
                "when too many ranks are used for the model size."
            ),
        ))

    # MPP load balance
    if mpp_timing:
        ratios = [m.cpu_ratio for m in mpp_timing]
        min_ratio = min(ratios)
        max_ratio = max(ratios)
        imbalance = max_ratio - min_ratio

        if imbalance > MPP_IMBALANCE_WARN:
            slowest = max(mpp_timing, key=lambda x: x.cpu_ratio)
            fastest = min(mpp_timing, key=lambda x: x.cpu_ratio)
            findings.append(Finding(
                severity=Severity.WARNING,
                category="performance",
                title=f"MPP load imbalance: {imbalance:.1%}",
                description=(
                    f"CPU ratio range: [{min_ratio:.4f}, {max_ratio:.4f}]. "
                    f"Slowest: proc #{slowest.processor_id} ({slowest.hostname}), "
                    f"Fastest: proc #{fastest.processor_id} ({fastest.hostname})."
                ),
                recommendation=(
                    "Review domain decomposition. Consider using "
                    "*CONTROL_MPP_DECOMPOSITION with RCBLOG for better balance."
                ),
            ))
        else:
            findings.append(Finding(
                severity=Severity.INFO,
                category="performance",
                title=f"MPP load balance: good (imbalance {imbalance:.1%})",
                description=(
                    f"CPU ratio range: [{min_ratio:.4f}, {max_ratio:.4f}] "
                    f"across {len(mpp_timing)} processors."
                ),
                recommendation="",
            ))

    # Load profile variation across processors
    if load_profile_pct:
        contact_pcts = [lp.contact for lp in load_profile_pct]
        if contact_pcts:
            min_c = min(contact_pcts)
            max_c = max(contact_pcts)
            if max_c - min_c > 10:
                findings.append(Finding(
                    severity=Severity.INFO,
                    category="performance",
                    title="Contact load varies across processors",
                    description=(
                        f"Contact cost varies from {min_c:.1f}% to {max_c:.1f}% "
                        f"across processors. Uneven contact distribution."
                    ),
                    recommendation=(
                        "Consider using contact groupable options or "
                        "adjusting decomposition to balance contact work."
                    ),
                ))

    return findings


# Component classification for scaling projection
_PARALLEL_KEYWORDS = ["element", "contact", "rigid"]
_COMM_KEYWORDS = ["sharing", "shr", "share"]
_SERIAL_KEYWORDS = ["keyword", "initialization", "decomposition", "init solver",
                     "binary database", "ascii database", "sense switch",
                     "group force", "time step size"]


def project_scaling(
    timing: list[PerformanceTiming],
    current_cores: int,
    elapsed_seconds: float,
) -> list[ScalingProjection]:
    """Project performance scaling to different core counts."""
    if not timing or current_cores < 1 or elapsed_seconds <= 0:
        return []

    # Classify timing components
    parallel_sec = 0.0
    comm_sec = 0.0
    serial_sec = 0.0

    for pt in timing:
        name = pt.component.lower()
        if any(k in name for k in _COMM_KEYWORDS):
            comm_sec += pt.clock_seconds
        elif any(k in name for k in _PARALLEL_KEYWORDS):
            parallel_sec += pt.clock_seconds
        elif any(k in name for k in _SERIAL_KEYWORDS):
            serial_sec += pt.clock_seconds
        else:
            # Unknown components split between parallel and serial
            parallel_sec += pt.clock_seconds * 0.5
            serial_sec += pt.clock_seconds * 0.5

    projections: list[ScalingProjection] = []
    targets = [current_cores]
    for n in [32, 64, 128, 256]:
        if n > current_cores:
            targets.append(n)

    for target in targets:
        ratio = target / current_cores
        # Parallel: scales inversely with cores
        p = parallel_sec / ratio
        # Communication: scales as sqrt(ratio) for 3D decomposition
        c = comm_sec * math.sqrt(ratio)
        # Serial: constant
        s = serial_sec
        est_elapsed = p + c + s

        sharing_pct = (c / est_elapsed * 100) if est_elapsed > 0 else 0
        speedup = elapsed_seconds / est_elapsed if est_elapsed > 0 else 0
        efficiency = (speedup / ratio * 100) if ratio > 0 else 0

        projections.append(ScalingProjection(
            target_cores=target,
            est_elapsed_seconds=est_elapsed,
            est_speedup=speedup,
            est_efficiency=efficiency,
            est_sharing_pct=sharing_pct,
        ))

    return projections
