"""LS-DYNA error and warning code database with recommendations."""

from dataclasses import dataclass
from koodyna.models import Severity


@dataclass
class ErrorInfo:
    code: int
    severity: Severity
    title: str
    description: str
    recommendation: str


ERROR_DATABASE: dict[int, ErrorInfo] = {
    # ===== Contact / Interface Warnings (50xxx) =====
    50135: ErrorInfo(
        code=50135,
        severity=Severity.WARNING,
        title="Tracked node not constrained (tied interface)",
        description=(
            "A slave node in a TIED contact interface could not be found "
            "on any master segment. This node will be unconstrained and "
            "may separate from the tied interface."
        ),
        recommendation=(
            "Check mesh compatibility between tied parts. Ensure slave nodes "
            "are within projection distance of master segments. Consider using "
            "SBOPT=3 and DEPTH=5 options in *CONTACT. Refine mesh near interface."
        ),
    ),
    50136: ErrorInfo(
        code=50136,
        severity=Severity.WARNING,
        title="Tracked node too far from segment",
        description=(
            "A slave node in a TIED contact is too far from the nearest "
            "master segment to be constrained. The distance exceeds the "
            "search tolerance."
        ),
        recommendation=(
            "Increase the tied contact search distance (SFACT) or improve mesh "
            "alignment between master and slave surfaces. Check for geometric "
            "gaps between tied parts."
        ),
    ),
    50120: ErrorInfo(
        code=50120,
        severity=Severity.WARNING,
        title="Contact segment normals inconsistent",
        description="Contact segment normals are inconsistent or reversed.",
        recommendation=(
            "Check segment normal orientation. Use *CONTACT_..._ID with "
            "proper SSTYP/MSTYP settings. Verify segment connectivity."
        ),
    ),

    # ===== Contact Penetration Warnings (20xxx) =====
    20248: ErrorInfo(
        code=20248,
        severity=Severity.WARNING,
        title="Initial penetration in contact",
        description=(
            "Nodes are initially penetrating through contact surfaces. "
            "This can cause artificial energy injection at the start."
        ),
        recommendation=(
            "Fix initial penetrations in the mesh using *CONTROL_CONTACT with "
            "PENOPT. Use IGNORE=1 to track but not resolve, or IGNORE=2. "
            "Check mesh alignment at contact surfaces."
        ),
    ),
    20200: ErrorInfo(
        code=20200,
        severity=Severity.WARNING,
        title="Contact interface has no segments",
        description="A contact interface has no segments defined.",
        recommendation=(
            "Verify the contact definition. Ensure segment sets reference "
            "correct part/set IDs."
        ),
    ),

    # ===== Negative Volume Errors (30xxx/40xxx) =====
    30010: ErrorInfo(
        code=30010,
        severity=Severity.CRITICAL,
        title="Negative volume (error termination)",
        description=(
            "An element has developed negative volume, causing error termination. "
            "The element is severely distorted beyond physical limits."
        ),
        recommendation=(
            "Add erosion criteria (*MAT_ADD_EROSION) to remove severely "
            "distorted elements. Use ERODE=1 in *CONTROL_TIMESTEP with "
            "appropriate TSMIN. Improve mesh quality in the problem region. "
            "Check boundary conditions and loading for excessive deformation."
        ),
    ),
    40003: ErrorInfo(
        code=40003,
        severity=Severity.CRITICAL,
        title="Negative volume in element",
        description=(
            "An element has developed a negative volume during computation. "
            "This indicates severe mesh distortion and potential instability."
        ),
        recommendation=(
            "Check element quality near the reported element. Add erosion "
            "criteria or reduce timestep scale factor. Improve mesh quality."
        ),
    ),
    40004: ErrorInfo(
        code=40004,
        severity=Severity.CRITICAL,
        title="Negative volume in shell element",
        description="A shell element has developed negative area/volume.",
        recommendation=(
            "Check for excessive shell deformation. Add element erosion "
            "or reduce shell TSMIN. Verify shell thickness is reasonable."
        ),
    ),

    # ===== NaN / Numerical Errors (30xxx) =====
    30200: ErrorInfo(
        code=30200,
        severity=Severity.CRITICAL,
        title="NaN velocity detected",
        description=(
            "A NaN (Not a Number) velocity was detected, indicating "
            "numerical divergence. The simulation has become unstable."
        ),
        recommendation=(
            "Check for zero-volume elements, excessive mass scaling, or "
            "contact instabilities. Reduce timestep scale factor (TSSFAC). "
            "Verify all material properties are physically reasonable."
        ),
    ),
    30100: ErrorInfo(
        code=30100,
        severity=Severity.CRITICAL,
        title="NaN in stress calculation",
        description="NaN detected in stress computation, indicating divergence.",
        recommendation=(
            "Check material properties. Ensure density, modulus, and "
            "yield stress are non-zero and physically reasonable. "
            "Reduce TSSFAC if needed."
        ),
    ),

    # ===== Memory Errors (10xxx) =====
    10103: ErrorInfo(
        code=10103,
        severity=Severity.CRITICAL,
        title="Out of memory",
        description="LS-DYNA ran out of allocated memory during execution.",
        recommendation=(
            "Increase memory allocation with memory= and memory2= keywords. "
            "On the command line: memory=NWORDS memory2=NWORDS. "
            "Check for excessive contact segment generation. Consider "
            "running with more MPI ranks to distribute memory."
        ),
    ),
    10100: ErrorInfo(
        code=10100,
        severity=Severity.CRITICAL,
        title="Insufficient memory for decomposition",
        description="Not enough memory for MPP decomposition.",
        recommendation=(
            "Increase memory allocation. Try memory=200m memory2=200m "
            "or higher on the command line."
        ),
    ),

    # ===== Element Quality Warnings =====
    40100: ErrorInfo(
        code=40100,
        severity=Severity.WARNING,
        title="Degenerate element detected",
        description="An element has very poor aspect ratio or is degenerate.",
        recommendation=(
            "Improve mesh quality. Remesh elements with poor aspect ratios. "
            "Use *CONTROL_CHECK for pre-run mesh quality verification."
        ),
    ),

    # ===== Timestep Warnings =====
    30001: ErrorInfo(
        code=30001,
        severity=Severity.WARNING,
        title="Element timestep below minimum",
        description=(
            "An element's timestep has fallen below the TSMIN threshold. "
            "The element may be eroded or the run terminated."
        ),
        recommendation=(
            "Review TSMIN and ERODE settings in *CONTROL_TIMESTEP. "
            "If erosion is active, check if too many elements are being removed."
        ),
    ),

    # ===== Material Warnings =====
    41200: ErrorInfo(
        code=41200,
        severity=Severity.WARNING,
        title="Material failure criterion met",
        description="A material failure criterion has been activated.",
        recommendation=(
            "Check failure strain/stress values in material definition. "
            "Verify the failure model is appropriate for the loading."
        ),
    ),

    # ===== Rigid Body Warnings =====
    60100: ErrorInfo(
        code=60100,
        severity=Severity.WARNING,
        title="Rigid body mass too small",
        description="A rigid body has very small mass, which can cause instability.",
        recommendation=(
            "Check rigid body material density and geometry. "
            "Ensure the rigid body mass is reasonable for the simulation."
        ),
    ),

    # ===== Adaptive/Remeshing =====
    70100: ErrorInfo(
        code=70100,
        severity=Severity.WARNING,
        title="Adaptive remeshing issue",
        description="An issue was encountered during adaptive remeshing.",
        recommendation=(
            "Check adaptive remeshing parameters. Verify the mesh quality "
            "criteria and refinement levels."
        ),
    ),

    # ===== SPH Warnings =====
    80100: ErrorInfo(
        code=80100,
        severity=Severity.WARNING,
        title="SPH particle issue",
        description="An issue with SPH particle computation.",
        recommendation="Check SPH parameters and particle distribution.",
    ),

    # ===== License / System =====
    90001: ErrorInfo(
        code=90001,
        severity=Severity.CRITICAL,
        title="License error",
        description="LS-DYNA license could not be acquired or has expired.",
        recommendation=(
            "Check LSTC_LICENSE_SERVER environment variable and license file. "
            "Contact your license administrator."
        ),
    ),
}


def lookup_error(code: int) -> ErrorInfo:
    """Look up a warning/error code. Returns generic info if code is unknown."""
    if code in ERROR_DATABASE:
        return ERROR_DATABASE[code]

    # Determine severity from code range
    if code < 20000:
        severity = Severity.CRITICAL
    elif code < 40000:
        severity = Severity.WARNING
    elif code < 50000:
        severity = Severity.WARNING
    elif code < 60000:
        severity = Severity.WARNING
    else:
        severity = Severity.INFO

    return ErrorInfo(
        code=code,
        severity=severity,
        title=f"Code {code}",
        description=f"Warning/Error code {code} (not in built-in database).",
        recommendation=(
            "Consult LS-DYNA documentation or LSTC support resources "
            f"for details on code {code}."
        ),
    )
