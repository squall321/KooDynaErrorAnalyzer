"""Parser for LS-DYNA nodout (nodal time history) ASCII output file."""

import re
from pathlib import Path
from dataclasses import dataclass, field
from math import sqrt


@dataclass
class NodalSnapshot:
    """Nodal data at a single time step."""
    time: float = 0.0
    timestep: int = 0
    node_id: int = 0
    x_disp: float = 0.0
    y_disp: float = 0.0
    z_disp: float = 0.0
    x_vel: float = 0.0
    y_vel: float = 0.0
    z_vel: float = 0.0
    x_accel: float = 0.0
    y_accel: float = 0.0
    z_accel: float = 0.0
    x_coord: float = 0.0
    y_coord: float = 0.0
    z_coord: float = 0.0

    def velocity_magnitude(self) -> float:
        """Calculate velocity magnitude."""
        return sqrt(self.x_vel**2 + self.y_vel**2 + self.z_vel**2)

    def acceleration_magnitude(self) -> float:
        """Calculate acceleration magnitude."""
        return sqrt(self.x_accel**2 + self.y_accel**2 + self.z_accel**2)


@dataclass
class NodalTimeSeries:
    """Time series data for a single node."""
    node_id: int = 0
    snapshots: list[NodalSnapshot] = field(default_factory=list)

    def max_velocity(self) -> float:
        """Get maximum velocity magnitude in time series."""
        if not self.snapshots:
            return 0.0
        return max(s.velocity_magnitude() for s in self.snapshots)

    def velocity_history(self) -> list[tuple[float, float]]:
        """Get (time, velocity_magnitude) pairs."""
        return [(s.time, s.velocity_magnitude()) for s in self.snapshots]


class NodoutParser:
    """Parser for nodout file."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self.nodes: dict[int, NodalTimeSeries] = {}
        self.legend: dict[int, str] = {}

    def parse(self, max_nodes: int | None = None) -> dict[int, NodalTimeSeries]:
        """
        Parse nodout file and return nodal time series data.

        Args:
            max_nodes: Maximum number of nodes to parse (None = all).
                      Use this to limit memory usage for large files.

        Returns:
            dict: {node_id: NodalTimeSeries}
        """
        if not self.file_path.exists():
            return self.nodes

        with open(self.file_path, 'r', encoding='utf-8', errors='replace') as f:
            in_legend = False
            current_time = 0.0
            current_timestep = 0
            nodes_parsed = 0

            for line in f:
                stripped = line.strip()

                # Parse legend
                if "{BEGIN LEGEND}" in line:
                    in_legend = True
                    continue
                elif "{END LEGEND}" in line:
                    in_legend = False
                    continue

                if in_legend:
                    # Entity #        Title
                    #     4141
                    match = re.match(r'\s*(\d+)\s*(.*)', stripped)
                    if match:
                        node_id = int(match.group(1))
                        title = match.group(2).strip()
                        self.legend[node_id] = title if title else ""
                    continue

                # Parse time header
                # "n o d a l   p r i n t   o u t   f o r   t i m e  s t e p       1                              ( at time 0.0000000E+00 )"
                if 'n o d a l   p r i n t   o u t' in line.lower():
                    # Extract timestep number
                    ts_match = re.search(r't i m e\s+s t e p\s+(\d+)', line)
                    if ts_match:
                        current_timestep = int(ts_match.group(1))

                    # Extract time value
                    time_match = re.search(r'\(\s*at time\s+([0-9.E+\-]+)\s*\)', line)
                    if time_match:
                        current_time = float(time_match.group(1))
                    continue

                # Skip header line
                if 'nodal point' in line.lower() and 'x-disp' in line.lower():
                    continue

                # Parse data line
                # Format: node_id x_disp y_disp z_disp x_vel y_vel z_vel x_accel y_accel z_accel x_coord y_coord z_coord
                parts = line.split()
                if len(parts) >= 13:
                    try:
                        node_id = int(parts[0])

                        # Check max_nodes limit
                        if max_nodes is not None and nodes_parsed >= max_nodes:
                            continue

                        snapshot = NodalSnapshot(
                            time=current_time,
                            timestep=current_timestep,
                            node_id=node_id,
                            x_disp=float(parts[1]),
                            y_disp=float(parts[2]),
                            z_disp=float(parts[3]),
                            x_vel=float(parts[4]),
                            y_vel=float(parts[5]),
                            z_vel=float(parts[6]),
                            x_accel=float(parts[7]),
                            y_accel=float(parts[8]),
                            z_accel=float(parts[9]),
                            x_coord=float(parts[10]),
                            y_coord=float(parts[11]),
                            z_coord=float(parts[12]),
                        )

                        if node_id not in self.nodes:
                            self.nodes[node_id] = NodalTimeSeries(node_id=node_id)
                            nodes_parsed += 1

                        self.nodes[node_id].snapshots.append(snapshot)

                    except (ValueError, IndexError):
                        # Skip malformed lines
                        pass

        return self.nodes
