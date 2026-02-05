"""Parser for LS-DYNA load_profile.csv and cont_profile.csv files."""

from pathlib import Path

from koodyna.models import LoadProfileEntry, ContProfileEntry


def _safe_float(s: str) -> float:
    try:
        return float(s.strip())
    except (ValueError, TypeError):
        return 0.0


PROFILE_FIELDS = [
    "solids", "shells", "tshells", "beams", "sph", "e_other",
    "force_shr", "tstep_shr", "swtch_shr", "matrl_shr", "elmnt_shr",
    "time_step", "contact", "rigid_bdy", "others",
]


class ProfileParser:
    """Parser for load_profile.csv file."""

    def __init__(self, filepath: Path):
        self.filepath = filepath

    def parse(self) -> tuple[list[LoadProfileEntry], list[LoadProfileEntry]]:
        """Parse load_profile.csv, returns (absolute_entries, percentage_entries)."""
        abs_entries: list[LoadProfileEntry] = []
        pct_entries: list[LoadProfileEntry] = []

        with open(self.filepath, "r", errors="replace") as f:
            lines = f.readlines()

        section = 0  # 0=none, 1=absolute, 2=percentage
        proc_id = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if section == 1 and abs_entries:
                    section = 0
                    proc_id = 0
                continue

            if '"Clock (seconds)"' in stripped:
                section = 1
                proc_id = 0
                continue
            elif '"Clock and percentage(%)"' in stripped:
                section = 2
                proc_id = 0
                continue
            elif stripped.startswith('"') or stripped.startswith("Solids"):
                continue

            if section in (1, 2):
                values = stripped.split(",")
                if len(values) >= 15:
                    entry = LoadProfileEntry(
                        processor_id=proc_id,
                        solids=_safe_float(values[0]),
                        shells=_safe_float(values[1]),
                        tshells=_safe_float(values[2]),
                        beams=_safe_float(values[3]),
                        sph=_safe_float(values[4]),
                        e_other=_safe_float(values[5]),
                        force_shr=_safe_float(values[6]),
                        tstep_shr=_safe_float(values[7]),
                        swtch_shr=_safe_float(values[8]),
                        matrl_shr=_safe_float(values[9]),
                        elmnt_shr=_safe_float(values[10]),
                        time_step=_safe_float(values[11]),
                        contact=_safe_float(values[12]),
                        rigid_bdy=_safe_float(values[13]),
                        others=_safe_float(values[14]),
                    )
                    if section == 1:
                        abs_entries.append(entry)
                    else:
                        pct_entries.append(entry)
                    proc_id += 1

        return abs_entries, pct_entries


class ContProfileParser:
    """Parser for cont_profile.csv file (per-contact interface timing)."""

    def __init__(self, filepath: Path):
        self.filepath = filepath

    def parse(self) -> tuple[list[ContProfileEntry], list[ContProfileEntry]]:
        """Parse cont_profile.csv, returns (absolute_entries, percentage_entries)."""
        abs_entries: list[ContProfileEntry] = []
        pct_entries: list[ContProfileEntry] = []

        with open(self.filepath, "r", errors="replace") as f:
            lines = f.readlines()

        section = 0  # 0=none, 1=absolute, 2=percentage
        interface_ids: list[int] = []
        proc_id = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if section == 1 and abs_entries:
                    section = 0
                    proc_id = 0
                    interface_ids = []
                continue

            if '"Clock (seconds)"' in stripped:
                section = 1
                proc_id = 0
                continue
            elif '"Clock percentage(%)"' in stripped:
                section = 2
                proc_id = 0
                continue
            elif stripped.startswith('"'):
                continue

            if section in (1, 2) and not interface_ids:
                # This line has interface IDs (zero-padded integers)
                interface_ids = [int(x.strip()) for x in stripped.split(",") if x.strip()]
                continue

            if section in (1, 2) and interface_ids:
                values = stripped.split(",")
                timings: dict[int, float] = {}
                for i, intf_id in enumerate(interface_ids):
                    if i < len(values):
                        timings[intf_id] = _safe_float(values[i])
                entry = ContProfileEntry(processor_id=proc_id, interface_timings=timings)
                if section == 1:
                    abs_entries.append(entry)
                else:
                    pct_entries.append(entry)
                proc_id += 1

        return abs_entries, pct_entries
