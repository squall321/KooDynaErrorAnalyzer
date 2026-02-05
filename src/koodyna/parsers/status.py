"""Parser for LS-DYNA status.out file."""

import re
from pathlib import Path

from koodyna.models import StatusInfo

RE_CPU_ZONE = re.compile(r'cpu time per zone cycle\.+\s+(\d+)\s+nanoseconds')
RE_AVG_CPU_ZONE = re.compile(r'average cpu time per zone cycle\.+\s+(\d+)\s+nanoseconds')
RE_AVG_CLOCK_ZONE = re.compile(r'average clock time per zone cycle\.+\s+(\d+)\s+nanoseconds')
RE_EST_TOTAL_CPU = re.compile(r'estimated total cpu time\s+=\s+(\d+)\s+sec')
RE_EST_CPU_REMAIN = re.compile(r'estimated cpu time to complete\s+=\s+(\d+)\s+sec')
RE_EST_TOTAL_CLOCK = re.compile(r'estimated total clock time\s+=\s+(\d+)\s+sec')
RE_EST_CLOCK_REMAIN = re.compile(r'estimated clock time to complete\s+=\s+(\d+)\s+sec')


class StatusParser:
    """Parser for status.out file."""

    def __init__(self, filepath: Path):
        self.filepath = filepath

    def parse(self) -> StatusInfo:
        info = StatusInfo()

        with open(self.filepath, "r", errors="replace") as f:
            for line in f:
                stripped = line.strip().lower()

                for pattern, attr in [
                    (RE_CPU_ZONE, "cpu_per_zone_ns"),
                    (RE_AVG_CPU_ZONE, "avg_cpu_per_zone_ns"),
                    (RE_AVG_CLOCK_ZONE, "avg_clock_per_zone_ns"),
                    (RE_EST_TOTAL_CPU, "est_total_cpu_sec"),
                    (RE_EST_CPU_REMAIN, "est_cpu_remain_sec"),
                    (RE_EST_TOTAL_CLOCK, "est_total_clock_sec"),
                    (RE_EST_CLOCK_REMAIN, "est_clock_remain_sec"),
                ]:
                    m = pattern.search(line.lower())
                    if m:
                        setattr(info, attr, int(m.group(1)))

        return info
