"""Warning and error classification for LS-DYNA results."""

from koodyna.models import WarningEntry, Finding, Severity
from koodyna.knowledge.error_db import lookup_error


def analyze_warnings(
    warning_counts: dict[int, int],
    warning_messages: dict[int, str],
    warning_interfaces: dict[int, set[int]],
    error_counts: dict[int, int],
    error_messages: dict[int, str],
) -> tuple[list[WarningEntry], list[Finding]]:
    """Classify and analyze all warnings and errors."""
    entries: list[WarningEntry] = []
    findings: list[Finding] = []

    # Process errors first (higher severity)
    for code, count in sorted(error_counts.items()):
        info = lookup_error(code)
        entry = WarningEntry(
            code=code,
            count=count,
            message=error_messages.get(code, info.description),
            severity=Severity.CRITICAL,
            recommendation=info.recommendation,
        )
        entries.append(entry)

        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="error",
            title=f"Error {code}: {info.title}",
            description=f"{count} occurrence(s). {info.description}",
            recommendation=info.recommendation,
        ))

    # Process warnings
    for code, count in sorted(warning_counts.items(), key=lambda x: -x[1]):
        info = lookup_error(code)
        interfaces = sorted(warning_interfaces.get(code, set()))

        entry = WarningEntry(
            code=code,
            count=count,
            message=warning_messages.get(code, info.description),
            severity=info.severity,
            recommendation=info.recommendation,
            affected_interfaces=interfaces,
        )
        entries.append(entry)

    # Generate findings for significant warning groups
    total_warnings = sum(warning_counts.values())
    if total_warnings > 0:
        # Group by severity
        codes_by_severity: dict[Severity, list[tuple[int, int]]] = {}
        for code, count in warning_counts.items():
            info = lookup_error(code)
            sev = info.severity
            if sev not in codes_by_severity:
                codes_by_severity[sev] = []
            codes_by_severity[sev].append((code, count))

        # Report critical warnings
        for code, count in codes_by_severity.get(Severity.CRITICAL, []):
            info = lookup_error(code)
            interfaces = sorted(warning_interfaces.get(code, set()))
            intf_str = (
                f" Affected interfaces: {interfaces[:10]}"
                + ("..." if len(interfaces) > 10 else "")
                if interfaces else ""
            )
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="warning",
                title=f"Warning {code}: {info.title} ({count:,}x)",
                description=f"{info.description}{intf_str}",
                recommendation=info.recommendation,
            ))

        # Report non-critical warnings as summary
        warn_codes = codes_by_severity.get(Severity.WARNING, [])
        if warn_codes:
            code_summary = ", ".join(
                f"{code}({count:,}x)" for code, count in warn_codes[:5]
            )
            total_warn = sum(c for _, c in warn_codes)
            findings.append(Finding(
                severity=Severity.WARNING,
                category="warning",
                title=f"{total_warn:,} warnings detected ({len(warn_codes)} codes)",
                description=f"Warning codes: {code_summary}",
                recommendation=(
                    "Review individual warning codes for details. "
                    "Common tied contact warnings can often be resolved by "
                    "improving mesh compatibility between contact surfaces."
                ),
            ))

    return entries, findings
