"""Parser for LS-DYNA bndout (boundary force/energy) ASCII output file."""

import re
from pathlib import Path
from dataclasses import dataclass, field
from math import sqrt


@dataclass
class BoundaryForceSnapshot:
    """Boundary forces at a single time step."""
    time: float = 0.0
    node_id: int = 0
    x_force: float = 0.0
    y_force: float = 0.0
    z_force: float = 0.0
    energy: float = 0.0
    x_moment: float = 0.0
    y_moment: float = 0.0
    z_moment: float = 0.0
    x_total: float = 0.0
    y_total: float = 0.0
    z_total: float = 0.0
    e_total: float = 0.0

    def force_magnitude(self) -> float:
        """Calculate force resultant magnitude."""
        return sqrt(self.x_force**2 + self.y_force**2 + self.z_force**2)

    def moment_magnitude(self) -> float:
        """Calculate moment resultant magnitude."""
        return sqrt(self.x_moment**2 + self.y_moment**2 + self.z_moment**2)


@dataclass
class BoundaryForceTimeSeries:
    """Time series data for boundary forces at a single node."""
    node_id: int = 0
    snapshots: list[BoundaryForceSnapshot] = field(default_factory=list)

    def max_force(self) -> float:
        """Get maximum force magnitude in time series."""
        if not self.snapshots:
            return 0.0
        return max(s.force_magnitude() for s in self.snapshots)

    def mean_force(self) -> float:
        """Get mean force magnitude."""
        if not self.snapshots:
            return 0.0
        return sum(s.force_magnitude() for s in self.snapshots) / len(self.snapshots)

    def force_history(self) -> list[tuple[float, float]]:
        """Get (time, force_magnitude) pairs."""
        return [(s.time, s.force_magnitude()) for s in self.snapshots]


class BndoutParser:
    """Parser for bndout file."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self.nodes: dict[int, BoundaryForceTimeSeries] = {}

    def parse(self) -> dict[int, BoundaryForceTimeSeries]:
        """
        Parse bndout file and return boundary force time series data.

        Returns:
            dict: {node_id: BoundaryForceTimeSeries}
        """
        if not self.file_path.exists():
            return self.nodes

        with open(self.file_path, 'r', encoding='utf-8', errors='replace') as f:
            current_time = 0.0

            for line in f:
                # Parse time header
                # "n o d a l   f o r c e/e n e r g y    o u t p u t  t=   0.00000E+00"
                if 'n o d a l   f o r c e' in line.lower() and ' t=' in line:
                    time_match = re.search(r't\s*=\s*([0-9.E+\-]+)', line)
                    if time_match:
                        current_time = float(time_match.group(1))
                    continue

                # Parse force line
                # "nd#    4513  xforce=   0.0000E+00   yforce=   0.0000E+00  zforce=  -1.0000E-02   energy=   2.1673E-08 xmoment=   0.0000E+00 ymoment=   0.0000E+00 zmoment=   0.0000E+00"
                if line.strip().startswith('nd#'):
                    snapshot = self._parse_force_line(line, current_time)
                    if snapshot:
                        node_id = snapshot.node_id
                        if node_id not in self.nodes:
                            self.nodes[node_id] = BoundaryForceTimeSeries(node_id=node_id)
                        self.nodes[node_id].snapshots.append(snapshot)
                    continue

                # Parse total line (optional, contains xtotal, ytotal, ztotal, etotal)
                # We can skip this for now as it's mostly redundant

        return self.nodes

    def _parse_force_line(self, line: str, time: float) -> BoundaryForceSnapshot | None:
        """Parse a force data line."""
        try:
            # Extract node ID
            node_match = re.search(r'nd#\s+(\d+)', line)
            if not node_match:
                return None
            node_id = int(node_match.group(1))

            # Extract force components
            xforce_match = re.search(r'xforce\s*=\s*([0-9.E+\-]+)', line)
            yforce_match = re.search(r'yforce\s*=\s*([0-9.E+\-]+)', line)
            zforce_match = re.search(r'zforce\s*=\s*([0-9.E+\-]+)', line)
            energy_match = re.search(r'energy\s*=\s*([0-9.E+\-]+)', line)
            xmoment_match = re.search(r'xmoment\s*=\s*([0-9.E+\-]+)', line)
            ymoment_match = re.search(r'ymoment\s*=\s*([0-9.E+\-]+)', line)
            zmoment_match = re.search(r'zmoment\s*=\s*([0-9.E+\-]+)', line)

            snapshot = BoundaryForceSnapshot(
                time=time,
                node_id=node_id,
                x_force=float(xforce_match.group(1)) if xforce_match else 0.0,
                y_force=float(yforce_match.group(1)) if yforce_match else 0.0,
                z_force=float(zforce_match.group(1)) if zforce_match else 0.0,
                energy=float(energy_match.group(1)) if energy_match else 0.0,
                x_moment=float(xmoment_match.group(1)) if xmoment_match else 0.0,
                y_moment=float(ymoment_match.group(1)) if ymoment_match else 0.0,
                z_moment=float(zmoment_match.group(1)) if zmoment_match else 0.0,
            )

            return snapshot

        except (ValueError, AttributeError):
            return None
