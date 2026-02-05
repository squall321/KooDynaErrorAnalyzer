"""Energy balance analysis for LS-DYNA simulation results."""

from koodyna.models import EnergySnapshot, EnergyAnalysis, Finding, Severity

# Thresholds
HOURGLASS_RATIO_WARN = 0.10     # 10% of internal energy
HOURGLASS_RATIO_CRIT = 0.50     # 50% of internal energy
SLIDING_RATIO_WARN = 0.05       # 5% of total energy
ENERGY_RATIO_WARN = 0.05        # 5% deviation from 1.0
ENERGY_RATIO_CRIT = 0.10        # 10% deviation from 1.0
ENERGY_GROWTH_WARN = 0.05       # 5% increase over initial


def analyze_energy(snapshots: list[EnergySnapshot]) -> EnergyAnalysis:
    """Analyze energy balance from a sequence of energy snapshots."""
    if not snapshots:
        return EnergyAnalysis()

    findings: list[Finding] = []

    initial = snapshots[0]
    final = snapshots[-1]
    initial_total = initial.total if initial.total != 0 else 1.0

    # Compute max hourglass ratio
    max_hg_ratio = 0.0
    max_hg_time = 0.0
    for s in snapshots:
        if s.internal > 0:
            ratio = s.hourglass / s.internal
            if ratio > max_hg_ratio:
                max_hg_ratio = ratio
                max_hg_time = s.time

    if max_hg_ratio > HOURGLASS_RATIO_CRIT:
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="energy",
            title="Hourglass energy critically high",
            description=(
                f"Max hourglass/internal energy ratio: {max_hg_ratio:.1%} "
                f"at t={max_hg_time:.4E}. This indicates severe zero-energy "
                f"mode deformation."
            ),
            recommendation=(
                "Increase hourglass control stiffness (IHQ/QH in *CONTROL_HOURGLASS). "
                "Consider switching to fully integrated elements (ELFORM=2 for solids, "
                "ELFORM=16 for shells). Check for single-point-constrained elements."
            ),
        ))
    elif max_hg_ratio > HOURGLASS_RATIO_WARN:
        findings.append(Finding(
            severity=Severity.WARNING,
            category="energy",
            title="Hourglass energy exceeds 10% of internal energy",
            description=(
                f"Max hourglass/internal energy ratio: {max_hg_ratio:.1%} "
                f"at t={max_hg_time:.4E}. Hourglass energy should generally "
                f"be below 10% of internal energy."
            ),
            recommendation=(
                "Review hourglass control settings. Consider using type 5 "
                "(Flanagan-Belytschko) for solids or increasing QH coefficient. "
                "Switching to fully integrated elements eliminates hourglassing."
            ),
        ))

    # Compute max sliding interface ratio
    max_slide_ratio = 0.0
    for s in snapshots:
        if s.total > 0:
            ratio = abs(s.sliding_interface) / abs(s.total)
            if ratio > max_slide_ratio:
                max_slide_ratio = ratio

    if max_slide_ratio > SLIDING_RATIO_WARN:
        findings.append(Finding(
            severity=Severity.WARNING,
            category="energy",
            title="High sliding interface energy",
            description=(
                f"Max sliding interface / total energy ratio: {max_slide_ratio:.1%}. "
                f"This may indicate contact instability or excessive penetration."
            ),
            recommendation=(
                "Check contact definitions for excessive penetration. "
                "Consider increasing penalty stiffness (SLSFAC in *CONTROL_CONTACT) "
                "or using soft constraint (SOFT=1)."
            ),
        ))

    # Energy ratio analysis
    min_ratio = min(s.energy_ratio for s in snapshots)
    max_ratio = max(s.energy_ratio for s in snapshots)

    if abs(max_ratio - 1.0) > ENERGY_RATIO_CRIT or abs(min_ratio - 1.0) > ENERGY_RATIO_CRIT:
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="energy",
            title="Energy balance severely violated",
            description=(
                f"Energy ratio range: [{min_ratio:.6f}, {max_ratio:.6f}]. "
                f"Deviation > {ENERGY_RATIO_CRIT:.0%} from 1.0 indicates "
                f"numerical instability or energy source/sink."
            ),
            recommendation=(
                "Check for contact energy growth, mass scaling effects, "
                "or improperly defined loads. Enable energy output "
                "(*CONTROL_ENERGY) to identify the source."
            ),
        ))
    elif abs(max_ratio - 1.0) > ENERGY_RATIO_WARN or abs(min_ratio - 1.0) > ENERGY_RATIO_WARN:
        findings.append(Finding(
            severity=Severity.WARNING,
            category="energy",
            title="Energy balance deviation detected",
            description=(
                f"Energy ratio range: [{min_ratio:.6f}, {max_ratio:.6f}]. "
                f"Some deviation from 1.0 detected."
            ),
            recommendation=(
                "Monitor energy components. Small deviations can be normal "
                "for contact-dominated simulations. Check contact energy and "
                "damping contributions."
            ),
        ))

    # Energy growth detection
    if len(snapshots) > 2:
        final_total = snapshots[-1].total
        if initial_total > 0 and (final_total - initial_total) / initial_total > ENERGY_GROWTH_WARN:
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="energy",
                title="Total energy is increasing (divergence)",
                description=(
                    f"Total energy grew from {initial_total:.4E} to "
                    f"{final_total:.4E} ({(final_total/initial_total - 1)*100:.1f}% increase). "
                    f"This strongly suggests numerical instability."
                ),
                recommendation=(
                    "Reduce timestep scale factor (TSSFAC). Check for "
                    "improperly defined initial penetrations in contacts. "
                    "Verify material properties and boundary conditions."
                ),
            ))

    return EnergyAnalysis(
        snapshots=snapshots,
        initial_total_energy=initial.total,
        final_total_energy=final.total,
        max_hourglass_ratio=max_hg_ratio,
        max_sliding_ratio=max_slide_ratio,
        energy_ratio_range=(min_ratio, max_ratio),
        findings=findings,
    )
