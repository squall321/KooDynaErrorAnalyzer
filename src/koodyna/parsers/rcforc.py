"""Parser for LS-DYNA rcforc (Resultant Contact Forces) file.

Extracts per-interface contact force/moment time series for SURFA and SURFB
(or slave/master) surfaces.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RcforcSnapshot:
    """One time-step snapshot of contact forces for one surface."""
    time: float = 0.0
    fx: float = 0.0
    fy: float = 0.0
    fz: float = 0.0
    mass: float = 0.0
    mx: float = 0.0
    my: float = 0.0
    mz: float = 0.0


@dataclass
class RcforcInterface:
    """Contact force data for one interface."""
    interface_id: int = 0
    title: str = ""
    surfa_forces: list[RcforcSnapshot] = field(default_factory=list)
    surfb_forces: list[RcforcSnapshot] = field(default_factory=list)
    is_single_surface: bool = False


# Pattern: SURFA/SURFB/slave/master line
# e.g. "  SURFA          92 time 1.23E-04  x  1.0E+03  y  2.0E+03  z  3.0E+03 mass  0.0E+00  mx  0.0E+00  my  0.0E+00  mz  0.0E+00"
RE_FORCE_LINE = re.compile(
    r'\s*(SURFA|SURFB|slave|master)\s+(\d+)\s+time\s+([^\s]+)'
    r'\s+x\s+([^\s]+)\s+y\s+([^\s]+)\s+z\s+([^\s]+)'
    r'\s+mass\s+([^\s]+)'
    r'\s+mx\s+([^\s]+)\s+my\s+([^\s]+)\s+mz\s+([^\s]+)',
    re.IGNORECASE,
)

RE_LEGEND_ENTRY = re.compile(r'\s*(\d+)\s+(.+)')
RE_SINGLE_SURFACE = re.compile(r'interface number,\s*(\d+),\s*is single surface')


def _safe_float(s: str) -> float:
    try:
        return float(s)
    except (ValueError, OverflowError):
        return 0.0


class RcforcParser:
    """Parse rcforc file and extract contact force time series."""

    def __init__(self, filepath: Path):
        self.filepath = filepath

    def parse(self) -> dict[int, RcforcInterface]:
        """Parse rcforc file.

        Returns:
            dict mapping interface_id → RcforcInterface
        """
        interfaces: dict[int, RcforcInterface] = {}
        legend: dict[int, str] = {}
        single_surface_ids: set[int] = set()

        in_legend = False

        with open(self.filepath, "r", errors="replace") as f:
            for line in f:
                # Legend parsing
                if "{BEGIN LEGEND}" in line:
                    in_legend = True
                    continue
                if "{END LEGEND}" in line:
                    in_legend = False
                    continue
                if in_legend:
                    if "Entity #" in line or "Title" in line:
                        continue
                    m = RE_LEGEND_ENTRY.match(line)
                    if m:
                        eid = int(m.group(1))
                        title = m.group(2).strip()
                        legend[eid] = title
                    continue

                # Single surface notification
                m_ss = RE_SINGLE_SURFACE.search(line)
                if m_ss:
                    single_surface_ids.add(int(m_ss.group(1)))
                    continue

                # Force data line
                m = RE_FORCE_LINE.match(line)
                if not m:
                    continue

                surf_type = m.group(1).upper()  # SURFA/SURFB/SLAVE/MASTER
                iid = int(m.group(2))
                time = _safe_float(m.group(3))
                fx = _safe_float(m.group(4))
                fy = _safe_float(m.group(5))
                fz = _safe_float(m.group(6))
                mass = _safe_float(m.group(7))
                mx = _safe_float(m.group(8))
                my = _safe_float(m.group(9))
                mz = _safe_float(m.group(10))

                snap = RcforcSnapshot(
                    time=time, fx=fx, fy=fy, fz=fz,
                    mass=mass, mx=mx, my=my, mz=mz,
                )

                if iid not in interfaces:
                    interfaces[iid] = RcforcInterface(
                        interface_id=iid,
                        title=legend.get(iid, ""),
                        is_single_surface=(iid in single_surface_ids),
                    )

                iface = interfaces[iid]
                if surf_type in ("SURFA", "SLAVE"):
                    iface.surfa_forces.append(snap)
                else:
                    iface.surfb_forces.append(snap)

        return interfaces
