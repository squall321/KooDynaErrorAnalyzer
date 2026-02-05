"""Contact analysis for LS-DYNA simulation results."""

from koodyna.models import ContactTiming, Finding, Severity

CONTACT_TIME_WARN = 0.40   # 40% of total clock time
CONTACT_TIME_INFO = 0.20   # 20% of total clock time

CONTACT_TYPE_NAMES = {
    1: "Sliding Only",
    2: "Tied",
    3: "Surface to Surface",
    4: "Single Surface",
    5: "Nodes to Surface",
    6: "Nodes Tied to Surface",
    7: "Shell Edge Tied to Shell",
    8: "Spotweld Nodes to Surface",
    9: "Tie-Break",
    10: "One-Way Surface to Surface",
    13: "Automatic Single Surface",
    14: "Eroding Surface to Surface",
    15: "Eroding Single Surface",
    25: "Automatic Surface to Surface (Offset)",
    26: "Automatic Single Surface (Offset)",
}


def analyze_contacts(
    contact_timing: list[ContactTiming],
    contact_types: dict[int, int],
    total_clock_seconds: float = 0.0,
) -> list[Finding]:
    """Analyze contact timing and generate findings."""
    findings: list[Finding] = []

    if not contact_timing:
        return findings

    total_contact_clock = sum(ct.clock_seconds for ct in contact_timing)
    total_contact_pct = sum(ct.clock_percent for ct in contact_timing)

    if total_clock_seconds > 0:
        contact_ratio = total_contact_clock / total_clock_seconds
    else:
        contact_ratio = total_contact_pct / 100.0 if total_contact_pct > 0 else 0

    if contact_ratio > CONTACT_TIME_WARN:
        findings.append(Finding(
            severity=Severity.WARNING,
            category="contact",
            title=f"Contact dominates computation time ({contact_ratio:.0%})",
            description=(
                f"Contact algorithm uses {total_contact_clock:.1f}s "
                f"({contact_ratio:.1%} of total clock time). "
                f"This is above the {CONTACT_TIME_WARN:.0%} threshold."
            ),
            recommendation=(
                "Consider using MPP groupable contacts where possible. "
                "Reduce contact search frequency (NSBCS in *CONTROL_CONTACT). "
                "Check if some contacts can be removed or simplified."
            ),
        ))
    elif contact_ratio > CONTACT_TIME_INFO:
        findings.append(Finding(
            severity=Severity.INFO,
            category="contact",
            title=f"Contact uses {contact_ratio:.0%} of total time",
            description=(
                f"Contact algorithm: {total_contact_clock:.1f}s "
                f"({contact_ratio:.1%} of total). "
                f"This is typical for contact-dominated simulations."
            ),
            recommendation=(
                "Review individual contact timings. Dominant contacts "
                "may benefit from optimization (bucket sort, segment-based)."
            ),
        ))

    # Identify dominant contact interfaces
    sorted_contacts = sorted(contact_timing, key=lambda x: x.clock_seconds, reverse=True)
    if sorted_contacts and total_contact_clock > 0:
        top = sorted_contacts[0]
        top_ratio = top.clock_seconds / total_contact_clock
        if top_ratio > 0.5:
            ctype = contact_types.get(top.interface_id, 0)
            ctype_name = CONTACT_TYPE_NAMES.get(ctype, f"Type {ctype}")
            findings.append(Finding(
                severity=Severity.INFO,
                category="contact",
                title=f"Interface {top.interface_id} dominates contact cost",
                description=(
                    f"Interface {top.interface_id} ({ctype_name}) uses "
                    f"{top.clock_seconds:.2f}s ({top_ratio:.0%} of contact time). "
                    f"Total contact interfaces: {len(contact_timing)}."
                ),
                recommendation=(
                    f"Review Interface {top.interface_id} for optimization. "
                    "Consider bucket sort options or reducing segment count."
                ),
            ))

    return findings
