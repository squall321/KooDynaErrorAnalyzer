"""Parser for LS-DYNA glstat file (global statistics - energy data)."""

import math
import re
from pathlib import Path

from koodyna.models import EnergySnapshot

# Two formats:
#   "dt of cycle    1 is controlled by solid  34050 of part   12"
#   "dt of cycle    1 is controlled by dt2ms"
RE_DT_CYCLE = re.compile(
    r'dt of cycle\s+(\d+)\s+is controlled by\s+(\w+)(?:\s+(\d+)\s+of part\s+(\d+))?'
)
RE_ENERGY_FIELD = re.compile(r'^\s*([\w\s/().]+?)\.{2,}\s+([\d.E+\-]+|\d+|[Nn][Aa][Nn]|[-+]?[Ii][Nn][Ff])\s*$')

# Ordered from most specific to least specific to avoid substring conflicts
FIELD_MAP_ORDERED = [
    ("total energy / initial energy", "energy_ratio"),
    ("energy ratio w/o eroded energy", "energy_ratio_no_eroded"),
    ("eroded kinetic energy", "eroded_kinetic"),
    ("eroded internal energy", "eroded_internal"),
    ("eroded hourglass energy", "eroded_hourglass"),
    ("spring and damper energy", "spring_damper"),
    ("sliding interface energy", "sliding_interface"),
    ("system damping energy", "system_damping"),
    ("dissipated kinetic energy", "dissipated_kinetic"),
    ("dissipated internal energy", "dissipated_internal"),
    ("time per zone cycle", "zone_ns"),
    ("kinetic energy", "kinetic"),
    ("internal energy", "internal"),
    ("hourglass energy", "hourglass"),
    ("drilling energy", "drilling"),
    ("total energy", "total"),
    ("external work", "external_work"),
    ("global x velocity", "vx"),
    ("global y velocity", "vy"),
    ("global z velocity", "vz"),
    ("time step", "timestep"),
    ("time", "time"),
]


def _safe_float(s: str) -> float:
    """Convert string to float. NaN/Inf are returned as-is (not replaced with 0)."""
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def _safe_int(s: str) -> int:
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


class GlstatParser:
    """Parser for glstat energy balance file."""

    def __init__(self, filepath: Path):
        self.filepath = filepath

    def parse(self) -> list[EnergySnapshot]:
        snapshots: list[EnergySnapshot] = []
        current_cycle_info: dict = {}
        current_fields: dict[str, float] = {}
        block_has_nan = False
        in_block = False

        with open(self.filepath, "r", errors="replace") as f:
            for line in f:
                stripped = line.rstrip()

                m = RE_DT_CYCLE.search(stripped)
                if m:
                    # Flush previous block
                    if current_fields:
                        snap = self._build_snapshot(current_cycle_info, current_fields, block_has_nan)
                        if snap:
                            snapshots.append(snap)

                    current_cycle_info = {
                        "cycle": _safe_int(m.group(1)),
                        "elem_type": m.group(2),
                        "elem_num": _safe_int(m.group(3) or "0"),
                        "part_num": _safe_int(m.group(4) or "0"),
                    }
                    current_fields = {}
                    block_has_nan = False
                    in_block = True
                    continue

                if in_block:
                    m = RE_ENERGY_FIELD.match(stripped)
                    if m:
                        field_name = m.group(1).strip().lower()
                        value_str = m.group(2).strip()
                        val = _safe_float(value_str)
                        if math.isnan(val) or math.isinf(val):
                            block_has_nan = True
                        for key, attr in FIELD_MAP_ORDERED:
                            if key in field_name:
                                current_fields[attr] = val
                                break

        # Flush last block
        if current_fields:
            snap = self._build_snapshot(current_cycle_info, current_fields, block_has_nan)
            if snap:
                snapshots.append(snap)

        return snapshots

    def _build_snapshot(
        self, cycle_info: dict, fields: dict[str, float], has_nan: bool = False
    ) -> EnergySnapshot | None:
        if not fields:
            return None

        return EnergySnapshot(
            cycle=cycle_info.get("cycle", 0),
            time=fields.get("time", 0.0),
            timestep=fields.get("timestep", 0.0),
            kinetic=fields.get("kinetic", 0.0),
            internal=fields.get("internal", 0.0),
            spring_damper=fields.get("spring_damper", 0.0),
            hourglass=fields.get("hourglass", 0.0),
            system_damping=fields.get("system_damping", 0.0),
            sliding_interface=fields.get("sliding_interface", 0.0),
            external_work=fields.get("external_work", 0.0),
            eroded_kinetic=fields.get("eroded_kinetic", 0.0),
            eroded_internal=fields.get("eroded_internal", 0.0),
            eroded_hourglass=fields.get("eroded_hourglass", 0.0),
            total=fields.get("total", 0.0),
            energy_ratio=fields.get("energy_ratio", 1.0),
            energy_ratio_no_eroded=fields.get("energy_ratio_no_eroded", 1.0),
            global_velocity=(
                fields.get("vx", 0.0),
                fields.get("vy", 0.0),
                fields.get("vz", 0.0),
            ),
            controlling_element_type=cycle_info.get("elem_type", ""),
            controlling_element=cycle_info.get("elem_num", 0),
            controlling_part=cycle_info.get("part_num", 0),
            time_per_zone_ns=int(fields.get("zone_ns", 0)),
            has_nan=has_nan,
        )
