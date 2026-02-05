"""Parser for LS-DYNA mesXXXX message files (per-MPI-rank logs)."""

import re
from pathlib import Path


RE_WARNING = re.compile(r'^\s*\*\*\*\s+Warning\s+(\d+)')
RE_ERROR = re.compile(r'^\s*\*\*\*\s+Error\s+(\d+)')
RE_INIT_PENETRATION = re.compile(
    r'(\d+)\s+initial penetrations? (?:were|was) found for interface\s+(\d+)'
)
RE_TERM_REACHED = re.compile(r'\*\*\*\s+termination time reached\s+\*\*\*')
RE_NORMAL_TERM = re.compile(r'N o r m a l\s+t e r m i n a t i o n')
RE_ERROR_TERM = re.compile(r'E r r o r\s+t e r m i n a t i o n')
RE_MEMORY_EXPAND = re.compile(
    r'(?:expanding|allocating|contracting)\s+memory to\s+(\d+)\s+d\s+(\d+)'
)
RE_INTF_WARN_SUMMARY = re.compile(
    r'Summary of warning messages for interface # =\s+(\d+)'
)
RE_INTF_WARN_COUNT = re.compile(
    r'number of warning messages\s+=\s+(\d+)'
)


class MessagData:
    """Parsed data from a single mes file."""

    def __init__(self, rank: int, filepath: Path):
        self.rank = rank
        self.filepath = filepath
        self.warning_counts: dict[int, int] = {}
        self.error_counts: dict[int, int] = {}
        self.initial_penetrations: dict[int, int] = {}  # interface_id -> count
        self.interface_warning_counts: dict[int, int] = {}
        self.normal_termination: bool = False
        self.error_termination: bool = False
        self.max_memory_d: int = 0


def discover_mes_files(result_dir: Path) -> list[Path]:
    """Find all mesXXXX files in the result directory."""
    return sorted(result_dir.glob("mes[0-9][0-9][0-9][0-9]"))


def parse_mes_file(filepath: Path) -> MessagData:
    """Parse a single mes file, focusing on warnings, errors, and termination."""
    rank_str = filepath.name.replace("mes", "")
    rank = int(rank_str) if rank_str.isdigit() else 0
    data = MessagData(rank, filepath)
    pending_intf_id: int | None = None

    with open(filepath, "r", errors="replace") as f:
        for line in f:
            stripped = line.rstrip()

            m = RE_WARNING.match(stripped)
            if m:
                code = int(m.group(1))
                data.warning_counts[code] = data.warning_counts.get(code, 0) + 1
                continue

            m = RE_ERROR.match(stripped)
            if m:
                code = int(m.group(1))
                data.error_counts[code] = data.error_counts.get(code, 0) + 1
                continue

            m = RE_INIT_PENETRATION.search(stripped)
            if m:
                count = int(m.group(1))
                intf_id = int(m.group(2))
                data.initial_penetrations[intf_id] = count

            # Per-interface warning summary
            m = RE_INTF_WARN_SUMMARY.search(stripped)
            if m:
                pending_intf_id = int(m.group(1))
                continue
            if pending_intf_id is not None:
                m = RE_INTF_WARN_COUNT.search(stripped)
                if m:
                    data.interface_warning_counts[pending_intf_id] = int(m.group(1))
                    pending_intf_id = None
                elif stripped.strip():
                    pending_intf_id = None

            if RE_NORMAL_TERM.search(stripped):
                data.normal_termination = True
            if RE_ERROR_TERM.search(stripped):
                data.error_termination = True

            m = RE_MEMORY_EXPAND.search(stripped)
            if m:
                mem = int(m.group(2))
                if mem > data.max_memory_d:
                    data.max_memory_d = mem

    return data


def parse_all_mes_files(result_dir: Path) -> list[MessagData]:
    """Parse all mes files in the result directory."""
    files = discover_mes_files(result_dir)
    return [parse_mes_file(f) for f in files]
