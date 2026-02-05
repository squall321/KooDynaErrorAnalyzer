"""Timestep analysis for LS-DYNA simulation results."""

from collections import Counter

from koodyna.models import (
    EnergySnapshot, TimestepEntry, TimestepAnalysis, Finding, Severity,
)

DT_DROP_WARN = 0.50      # dt dropped to 50% of initial
DT_DROP_CRIT = 0.10      # dt dropped to 10% of initial


def analyze_timestep(
    smallest_timesteps: list[TimestepEntry],
    energy_snapshots: list[EnergySnapshot],
    dt_scale_factor: float = 0.0,
    dt2ms: float = 0.0,
    tsmin: float = 0.0,
) -> TimestepAnalysis:
    """Analyze timestep behavior and identify controlling parts."""
    findings: list[Finding] = []

    # Parts controlling smallest timesteps
    part_counts: dict[int, int] = {}
    for entry in smallest_timesteps:
        part_counts[entry.part_number] = part_counts.get(entry.part_number, 0) + 1

    # Parts controlling timestep over simulation (from energy snapshots)
    controlling_counts: dict[int, int] = {}
    for snap in energy_snapshots:
        if snap.controlling_part > 0:
            p = snap.controlling_part
            controlling_counts[p] = controlling_counts.get(p, 0) + 1

    # Timestep stability
    initial_dt = energy_snapshots[0].timestep if energy_snapshots else 0.0
    final_dt = energy_snapshots[-1].timestep if energy_snapshots else 0.0
    min_dt = min((s.timestep for s in energy_snapshots), default=0.0)

    if initial_dt > 0 and min_dt > 0:
        ratio = min_dt / initial_dt
        if ratio < DT_DROP_CRIT:
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="timestep",
                title="Severe timestep drop detected",
                description=(
                    f"Timestep dropped to {ratio:.1%} of initial value "
                    f"(from {initial_dt:.4E} to {min_dt:.4E}). "
                    f"This indicates severe element distortion."
                ),
                recommendation=(
                    "Check the controlling elements for excessive deformation. "
                    "Consider adding erosion criteria (*MAT_ADD_EROSION) or "
                    "improving mesh quality in the problem region."
                ),
            ))
        elif ratio < DT_DROP_WARN:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="timestep",
                title="Significant timestep drop detected",
                description=(
                    f"Timestep dropped to {ratio:.1%} of initial value "
                    f"(from {initial_dt:.4E} to {min_dt:.4E})."
                ),
                recommendation=(
                    "Monitor the controlling part for potential instability. "
                    "Check element quality near the smallest timestep elements."
                ),
            ))

    # Single part dominating timestep control
    if part_counts:
        total_entries = sum(part_counts.values())
        dominant_part, dominant_count = max(part_counts.items(), key=lambda x: x[1])
        if dominant_count / total_entries > 0.8:
            findings.append(Finding(
                severity=Severity.INFO,
                category="timestep",
                title=f"Part {dominant_part} dominates timestep control",
                description=(
                    f"Part {dominant_part} controls {dominant_count}/{total_entries} "
                    f"of the 100 smallest timesteps ({dominant_count/total_entries:.0%}). "
                    f"Smallest dt: {smallest_timesteps[0].timestep:.4E}."
                ),
                recommendation=(
                    f"Review mesh quality in Part {dominant_part}. "
                    "Coarsening very small elements or applying mass scaling "
                    "(DT2MS in *CONTROL_TIMESTEP) could improve performance."
                ),
            ))

    # Mass scaling detection
    if dt2ms != 0.0:
        findings.append(Finding(
            severity=Severity.INFO,
            category="timestep",
            title="Mass scaling is active",
            description=(
                f"DT2MS = {dt2ms:.4E}. Mass is being added to maintain "
                f"the target timestep size."
            ),
            recommendation=(
                "Verify that added mass is acceptable (<5% of total mass). "
                "Check *DATABASE_GLSTAT for mass increase percentage."
            ),
        ))

    return TimestepAnalysis(
        smallest_timesteps=smallest_timesteps,
        controlling_parts=controlling_counts if controlling_counts else part_counts,
        initial_dt=initial_dt,
        final_dt=final_dt,
        min_dt=min_dt,
        dt_scale_factor=dt_scale_factor,
        dt2ms=dt2ms,
        tsmin=tsmin,
        findings=findings,
    )
