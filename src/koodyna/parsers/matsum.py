"""Parser for LS-DYNA matsum (material summary) ASCII output file."""

import re
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class MaterialSnapshot:
    """Material energy/momentum at a single time."""
    time: float = 0.0
    material_id: int = 0
    internal_energy: float = 0.0
    kinetic_energy: float = 0.0
    eroded_ie: float = 0.0
    eroded_ke: float = 0.0
    x_momentum: float = 0.0
    y_momentum: float = 0.0
    z_momentum: float = 0.0
    x_rbv: float = 0.0  # rigid body velocity
    y_rbv: float = 0.0
    z_rbv: float = 0.0
    hourglass_energy: float = 0.0
    eroded_he: float = 0.0


@dataclass
class MaterialTimeSeries:
    """Time series data for a single material."""
    material_id: int = 0
    material_name: str = ""
    snapshots: list[MaterialSnapshot] = field(default_factory=list)


class MatsumParser:
    """Parser for matsum file."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self.materials: dict[int, MaterialTimeSeries] = {}
        self.legend: dict[int, str] = {}

    def parse(self) -> dict[int, MaterialTimeSeries]:
        """Parse matsum file and return material time series data."""
        if not self.file_path.exists():
            return self.materials

        with open(self.file_path, 'r', encoding='utf-8', errors='replace') as f:
            in_legend = False
            current_time = 0.0

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
                    #        1     Stack1_BoxMesh10000_0
                    match = re.match(r'\s*(\d+)\s+(.+)', stripped)
                    if match:
                        mat_id = int(match.group(1))
                        title = match.group(2).strip()
                        self.legend[mat_id] = title
                    continue

                # Parse time
                if stripped.startswith("time ="):
                    match = re.search(r'time\s*=\s*([\d.E+\-]+)', stripped)
                    if match:
                        current_time = float(match.group(1))
                    continue

                # Parse material data
                # mat.#=    1             inten=   0.0000E+00     kinen=   0.0000E+00     eroded_ie=   0.0000E+00     eroded_ke=   0.0000E+00
                if stripped.startswith("mat.#="):
                    snapshot = self._parse_material_block(line, f, current_time)
                    if snapshot:
                        mat_id = snapshot.material_id
                        if mat_id not in self.materials:
                            self.materials[mat_id] = MaterialTimeSeries(
                                material_id=mat_id,
                                material_name=self.legend.get(mat_id, ""),
                            )
                        self.materials[mat_id].snapshots.append(snapshot)

        return self.materials

    def _parse_material_block(self, first_line: str, file_iter, current_time: float) -> MaterialSnapshot | None:
        """Parse a single material block (3-4 lines)."""
        # Line 1: mat.#=    1             inten=   0.0000E+00     kinen=   0.0000E+00     eroded_ie=   0.0000E+00     eroded_ke=   0.0000E+00
        match = re.search(r'mat\.#\s*=\s*(\d+)', first_line)
        if not match:
            return None

        mat_id = int(match.group(1))
        snapshot = MaterialSnapshot(time=current_time, material_id=mat_id)

        # Parse first line fields
        for field, attr in [
            (r'inten\s*=\s*([\d.E+\-]+)', 'internal_energy'),
            (r'kinen\s*=\s*([\d.E+\-]+)', 'kinetic_energy'),
            (r'eroded_ie\s*=\s*([\d.E+\-]+)', 'eroded_ie'),
            (r'eroded_ke\s*=\s*([\d.E+\-]+)', 'eroded_ke'),
        ]:
            m = re.search(field, first_line)
            if m:
                setattr(snapshot, attr, float(m.group(1)))

        # Line 2: x-mom=   0.0000E+00     y-mom=   0.0000E+00     z-mom=   0.0000E+00
        try:
            line2 = next(file_iter)
            for field, attr in [
                (r'x-mom\s*=\s*([\d.E+\-]+)', 'x_momentum'),
                (r'y-mom\s*=\s*([\d.E+\-]+)', 'y_momentum'),
                (r'z-mom\s*=\s*([\d.E+\-]+)', 'z_momentum'),
            ]:
                m = re.search(field, line2)
                if m:
                    setattr(snapshot, attr, float(m.group(1)))
        except StopIteration:
            return snapshot

        # Line 3: x-rbv=   0.0000E+00     y-rbv=   0.0000E+00     z-rbv=   0.0000E+00
        try:
            line3 = next(file_iter)
            for field, attr in [
                (r'x-rbv\s*=\s*([\d.E+\-]+)', 'x_rbv'),
                (r'y-rbv\s*=\s*([\d.E+\-]+)', 'y_rbv'),
                (r'z-rbv\s*=\s*([\d.E+\-]+)', 'z_rbv'),
            ]:
                m = re.search(field, line3)
                if m:
                    setattr(snapshot, attr, float(m.group(1)))
        except StopIteration:
            return snapshot

        # Line 4: hgeng=   0.0000E+00                             eroded_he=   0.0000E+00
        try:
            line4 = next(file_iter)
            for field, attr in [
                (r'hgeng\s*=\s*([\d.E+\-]+)', 'hourglass_energy'),
                (r'eroded_he\s*=\s*([\d.E+\-]+)', 'eroded_he'),
            ]:
                m = re.search(field, line4)
                if m:
                    setattr(snapshot, attr, float(m.group(1)))
        except StopIteration:
            pass

        return snapshot
