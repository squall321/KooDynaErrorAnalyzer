"""Overall diagnostic engine that aggregates all analysis findings."""

from koodyna.models import (
    TerminationInfo, TerminationStatus, Finding, Severity,
)


def run_diagnostics(
    termination: TerminationInfo,
    energy_findings: list[Finding],
    timestep_findings: list[Finding],
    warning_findings: list[Finding],
    contact_findings: list[Finding],
    performance_findings: list[Finding],
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

    # Sort by severity: CRITICAL > WARNING > INFO
    severity_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}
    all_findings.sort(key=lambda f: severity_order.get(f.severity, 3))

    return all_findings
