"""Parser for LS-DYNA d3hsp file (high-speed post-processing database)."""

import re
from pathlib import Path

from koodyna.models import (
    SimulationHeader, ModelSize, TerminationInfo, TerminationStatus,
    WarningEntry, TimestepEntry, PartDefinition, PerformanceTiming,
    ContactTiming, MPPProcessorTiming, EnergySnapshot, ContactDefinition,
    DecompMetrics, MassProperty,
)

# --- Header patterns ---
RE_RUN_DATE = re.compile(r'^\s+Date:\s+(\S+)\s+Time:\s+(\S+)')
RE_VERSION = re.compile(r'^\s*\|\s+Version\s*:\s*(.+?)\s*\|')
RE_REVISION = re.compile(r'^\s*\|\s+Revision\s*:\s*(.+?)\s*\|')
RE_PLATFORM = re.compile(r'^\s*\|\s+Platform\s+:\s*(.+?)\s*\|')
RE_OS_LEVEL = re.compile(r'^\s*\|\s+OS Level\s+:\s*(.+?)\s*\|')
RE_COMPILER = re.compile(r'^\s*\|\s+Compiler\s+:\s*(.+?)\s*\|')
RE_HOSTNAME = re.compile(r'^\s*\|\s+Hostname\s+:\s*(.+?)\s*\|')
RE_PRECISION = re.compile(r'^\s*\|\s+Precision\s+:\s*(.+?)\s*\|')
RE_LICENSEE = re.compile(r'^\s*\|\s+Licensed to:\s*(.+?)\s*\|')
RE_INPUT_FILE = re.compile(r'Input file:\s*(\S+)')
RE_CMD_LINE = re.compile(r'Command line options:\s*i=(\S+)')
RE_MPP_PROCS = re.compile(r'(?:MPP|Parallel)\s+execution with\s+(\d+)\s+(?:MPP\s+)?procs?')

# --- Keyword counts ---
RE_KEYWORD_COUNT = re.compile(r"total # of \*([A-Za-z_0-9/,\.\+\-\(\)\s]+?)\.{2,}\s+(\d+)")

# --- Model size ---
RE_NUM_MATERIALS = re.compile(r'number of materials or property sets\.+\s+(\d+)')
RE_NUM_NODES = re.compile(r'number of nodal\+scalar points\.+\s+(\d+)')
RE_NUM_SOLIDS = re.compile(r'number of solid elements\.+\s+(\d+)')
RE_NUM_SHELLS = re.compile(r'number of shell elements\.+\s+(\d+)')
RE_NUM_BEAMS = re.compile(r'number of beam elements\.+\s+(\d+)')
RE_NUM_TSHELLS = re.compile(r'number of thick shell elements\.+\s+(\d+)')
RE_NUM_SPH = re.compile(r'number of SPH particles\.+\s+(\d+)')
RE_NUM_CONTACTS = re.compile(r'number of number of contact definitions\.+\s+(\d+)')
RE_NUM_SPC = re.compile(r'number of spc nodes\.+\s+(\d+)')
RE_NUM_PARTS = re.compile(r'total # of \*PART_option card\.+\s+(\d+)')

# --- Computation options ---
RE_TERM_TIME = re.compile(r'termination time\.+\s+([\d.E+\-]+)')
RE_TSSFAC = re.compile(r'time step scale factor\.+\s+([\d.E+\-]+)')
RE_DT2MS = re.compile(r'time step size for mass scaled solution.*?\.+\s+([\d.E+\-]+)')
RE_TSMIN = re.compile(r'reduction factor for minimum time step.*?\.+\s+([\d.E+\-]+)')

# --- Part definitions ---
RE_PART_SEPARATOR = re.compile(r'^\s*\*{60,}')
RE_PART_ID = re.compile(r'part\s+id\s*\.+\s*(\d+)')
RE_SECTION_ID = re.compile(r'section\s+id\s*\.+\s*(\d+)')
RE_MATERIAL_ID = re.compile(r'material\s+id\s*\.+\s*(\d+)')
RE_MATERIAL_TYPE = re.compile(r'material type\s*\.+\s*(\d+)')
RE_EOS_TYPE = re.compile(r'equation-of-state type\s*\.+\s*(\d+)')
RE_HG_TYPE = re.compile(r'hourglass type\s*\.+\s*(\d+)')
RE_DENSITY = re.compile(r'density\s*\.+\s*=\s*([\d.E+\-]+)')
RE_HG_COEFF = re.compile(r'hourglass coefficient\s*\.+\s*=\s*([\d.E+\-]+)')
RE_YOUNGS_MOD = re.compile(r'^\s+e\s+\.+\s*=\s*([\d.E+\-]+)')
RE_POISSON = re.compile(r'vnu\s*\.+\s*=\s*([\d.E+\-]+)')
RE_SOLID_FORM = re.compile(r'solid\s+formulation\s*\.+\s*=\s*(\d+)')
RE_SECTION_TITLE_MARKER = re.compile(r'section\s+title\s*\.+')
RE_MATERIAL_TITLE_MARKER = re.compile(r'material title\s*\.+')

# --- Contact interfaces ---
RE_CONTACT_HEADER = re.compile(r'Contact Interface\s+(\d+)')
RE_CONTACT_TYPE = re.compile(r'contact type\.+\s+(\d+)')

# --- Contact summary table ---
RE_CONTACT_SUMMARY_ENTRY = re.compile(
    r'^\s+(\d+)\s+(\d+)\s+([oa]?\s*\d+)\s+(.*?)\s*$'
)

# --- Warnings/Errors ---
RE_WARNING = re.compile(r'^\s*\*\*\*\s+Warning\s+(\d+)')
RE_ERROR = re.compile(r'^\s*\*\*\*\s+Error\s+(\d+)')
RE_TIED_INTERFACE = re.compile(r'tied interface #\s*=\s*(\d+)')
RE_TRACKED_NODE = re.compile(r'tracked node #\s*=\s*(\d+)')

# --- Energy blocks (from glstat section in d3hsp) ---
RE_DT_CYCLE = re.compile(
    r'dt of cycle\s+(\d+)\s+is controlled by\s+(\w+)\s+(\d+)\s+of part\s+(\d+)'
)
RE_ENERGY_FIELD = re.compile(r'^\s*([\w\s/().]+?)\.{2,}\s+([\d.E+\-]+|\d+)\s*$')

# --- 100 smallest timesteps ---
RE_SMALLEST_TS_HEADER = re.compile(r'100 smallest timesteps')
RE_SMALLEST_TS_ENTRY = re.compile(
    r'(solid|shell|beam|tshell)\s+(\d+)\s+(\d+)\s+([\d.E+\-]+)'
)

# --- Cycle progress ---
RE_CYCLE_PROGRESS = re.compile(
    r'^\s*(\d+)\s+t\s+([\d.E+\-]+)\s+dt\s+([\d.E+\-]+)'
)

# --- Termination ---
RE_TERM_REACHED = re.compile(r'\*\*\*\s+termination time reached\s+\*\*\*')
RE_NORMAL_TERM = re.compile(r'N o r m a l\s+t e r m i n a t i o n')
RE_ERROR_TERM = re.compile(r'E r r o r\s+t e r m i n a t i o n')

# --- Final summary ---
RE_PROBLEM_TIME = re.compile(r'Problem time\s+=\s+([\d.E+\-]+)')
RE_PROBLEM_CYCLE = re.compile(r'Problem cycle\s+=\s+(\d+)')
RE_TOTAL_CPU = re.compile(r'Total CPU time\s+=\s+(\d+)\s+seconds')
RE_CPU_PER_ZONE = re.compile(r'CPU time per zone cycle\s*=\s+([\d.]+)\s+nanoseconds')
RE_CLOCK_PER_ZONE = re.compile(r'Clock time per zone cycle\s*=\s+([\d.]+)\s+nanoseconds')

# --- Timing table ---
RE_TIMING_HEADER = re.compile(r'T i m i n g\s+i n f o r m a t i o n')
RE_TIMING_ENTRY = re.compile(
    r'^\s{1,2}(\S.*?)\s*\.{2,}\s*([\d.E+\-]+)\s+([\d.]+)\s+([\d.E+\-]+)\s+([\d.]+)'
)
RE_TIMING_SUB = re.compile(
    r'^\s{2,6}(\S.*?)\s*\.{2,}\s*([\d.E+\-]+)\s+([\d.]+)\s+([\d.E+\-]+)\s+([\d.]+)'
)
RE_INTERF_ID = re.compile(
    r'^\s+Interf\.\s+ID\s+(\d+)\s+([\d.E+\-]+)\s+([\d.]+)\s+([\d.E+\-]+)\s+([\d.]+)'
)

# --- CPU timing per processor ---
RE_CPU_PROC = re.compile(
    r'#\s+(\d+)\s+(\S+)\s+([\d.]+)\s+([\d.E+\-]+)'
)
# --- Decomposition metrics ---
RE_DECOMP_MIN = re.compile(r'Minumum:\s+([\d.E+\-]+)')
RE_DECOMP_MAX = re.compile(r'Maximum:\s+([\d.E+\-]+)')
RE_DECOMP_STDDEV = re.compile(r'Standard Deviation:\s+([\d.E+\-]+)')
RE_DECOMP_MEM = re.compile(r'Memory required for decomposition\s+:\s+(\d+)')
RE_DECOMP_DYN_MEM = re.compile(r'Additional dynamic memory required\s+:\s+(\d+)')

# --- Mass properties ---
RE_MASS_PART_HEADER = re.compile(r'm a s s\s+p r o p e r t i e s\s+o f\s+p a r t\s*#\s*(\d+)')
RE_MASS_TOTAL = re.compile(r'total mass of part\s+=\s+([\d.E+\-]+)')
RE_MASS_CX = re.compile(r'x-coordinate of mass center\s*=\s*(-?[\d.E+\-]+)')
RE_MASS_CY = re.compile(r'y-coordinate of mass center\s*=\s*(-?[\d.E+\-]+)')
RE_MASS_CZ = re.compile(r'z-coordinate of mass center\s*=\s*(-?[\d.E+\-]+)')
RE_MASS_I11 = re.compile(r'i11\s*=\s*([\d.E+\-]+)')
RE_MASS_I22 = re.compile(r'i22\s*=\s*([\d.E+\-]+)')
RE_MASS_I33 = re.compile(r'i33\s*=\s*([\d.E+\-]+)')

RE_START_TIME = re.compile(r'Start time\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})')
RE_END_TIME = re.compile(r'End time\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})')
RE_ELAPSED = re.compile(r'Elapsed time\s+(\d+)\s+seconds')

# Material type name map
MATERIAL_TYPE_NAMES = {
    1: "Elastic", 2: "Orthotropic", 3: "Elastic-Plastic (von Mises)",
    5: "Soil/Crushable Foam", 6: "Viscoelastic", 7: "Blatz-Ko Rubber",
    9: "Null", 20: "Rigid", 24: "Piecewise Linear Plasticity",
    57: "Low Density Urethane Foam", 76: "Linear Viscoelastic",
    77: "General Hyperelastic/Ogden", 98: "Simplified Johnson Cook",
}


def _safe_float(s: str) -> float:
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def _safe_int(s: str) -> int:
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


class D3hspData:
    """Container for all parsed d3hsp data."""

    def __init__(self):
        self.header = SimulationHeader()
        self.model_size = ModelSize()
        self.termination = TerminationInfo()
        self.keyword_counts: dict[str, int] = {}
        self.parts: list[PartDefinition] = []
        self.contact_ids: list[int] = []
        self.contact_types: dict[int, int] = {}
        self.warning_counts: dict[int, int] = {}
        self.warning_messages: dict[int, str] = {}
        self.warning_interfaces: dict[int, set[int]] = {}
        self.error_counts: dict[int, int] = {}
        self.error_messages: dict[int, str] = {}
        self.energy_snapshots: list[EnergySnapshot] = []
        self.smallest_timesteps: list[TimestepEntry] = []
        self.performance: list[PerformanceTiming] = []
        self.contact_timing: list[ContactTiming] = []
        self.mpp_timing: list[MPPProcessorTiming] = []
        self.contact_definitions: list[ContactDefinition] = []
        self.dt_scale_factor: float = 0.0
        self.dt2ms: float = 0.0
        self.tsmin: float = 0.0
        self.decomp_metrics = DecompMetrics()
        self.mass_properties: list[MassProperty] = []


class D3hspParser:
    """Streaming line-by-line parser for LS-DYNA d3hsp file."""

    def __init__(self, filepath: Path, verbose: bool = False):
        self.filepath = filepath
        self.verbose = verbose

    def parse(self) -> D3hspData:
        data = D3hspData()

        # State machine phases: HEADER → KEYWORD_COUNTS → CONTROL_INFO →
        # PART_DEFS → CONTACTS → BODY → TAIL
        # BODY: warnings + energy blocks (bulk of the file, regex-minimal loop)
        # TAIL: timing, cpu, decomp, mass, summary (only after "T i m i n g")
        state = "HEADER"
        part_block: list[str] = []
        in_contact_summary = False
        in_smallest_ts = False
        in_timing = False
        in_cpu_timing = False
        in_energy_block = False
        current_energy: dict[str, float] = {}
        current_cycle_info: dict = {}
        last_warning_code: int | None = None
        lines_after_warning: int = 0

        # 진행율 추적용
        total_bytes = self.filepath.stat().st_size if self.verbose else 1
        last_pct_reported = -1
        line_counter = 0
        bytes_read = 0

        with open(self.filepath, "r", errors="replace") as f:
            for line in f:
                stripped = line.rstrip()

                # --- 진행율 출력 (verbose, 매 1000줄마다 체크) ---
                if self.verbose:
                    bytes_read += len(line)
                    line_counter += 1
                    if line_counter % 1000 == 0:
                        pct = min(int(bytes_read / total_bytes * 100), 99)
                        if pct != last_pct_reported and pct % 10 == 0:
                            print(f"    d3hsp: {pct}% ({state})")
                            last_pct_reported = pct

                # ========== HEADER ==========
                if state == "HEADER":
                    self._parse_header_line(stripped, data)
                    if "L I S T   O F   K E Y W O R D   C O U N T S" in stripped:
                        state = "KEYWORD_COUNTS"
                    continue

                # ========== KEYWORD_COUNTS ==========
                if state == "KEYWORD_COUNTS":
                    if "c o n t r o l   i n f o r m a t i o n" in stripped:
                        state = "CONTROL_INFO"
                        continue
                    m = RE_KEYWORD_COUNT.match(stripped)
                    if m:
                        kw = m.group(1).strip()
                        count = _safe_int(m.group(2))
                        if count > 0:
                            data.keyword_counts[kw] = count
                        if "PART_option card" in kw:
                            data.model_size.num_parts = count
                    else:
                        m = RE_MPP_PROCS.search(stripped)
                        if m:
                            data.header.num_procs = _safe_int(m.group(1))
                    continue

                # ========== CONTROL_INFO ==========
                if state == "CONTROL_INFO":
                    if "p a r t   d e f i n i t i o n s" in stripped:
                        state = "PART_DEFS"
                        continue
                    self._parse_model_size(stripped, data)
                    self._parse_computation_options(stripped, data)
                    m = RE_MPP_PROCS.search(stripped)
                    if m:
                        data.header.num_procs = _safe_int(m.group(1))
                    continue

                # ========== PART_DEFS ==========
                if state == "PART_DEFS":
                    if "c o n t a c t   i n t e r f a c e s" in stripped:
                        if part_block:
                            part = self._parse_part_block(part_block)
                            if part:
                                data.parts.append(part)
                            part_block = []
                        state = "CONTACTS"
                        continue
                    if RE_PART_SEPARATOR.match(stripped):
                        if part_block:
                            part = self._parse_part_block(part_block)
                            if part:
                                data.parts.append(part)
                            part_block = []
                    else:
                        part_block.append(stripped)
                    continue

                # ========== CONTACTS ==========
                if state == "CONTACTS":
                    # Transition to BODY on first warning/error or energy block
                    if "***" in stripped and ("Warning" in stripped or "Error" in stripped):
                        state = "BODY"
                        # fall through to BODY handling below
                    else:
                        if "Contact summary" in stripped:
                            in_contact_summary = True
                            continue
                        if in_contact_summary:
                            if "Order #" in stripped:
                                continue
                            m = RE_CONTACT_SUMMARY_ENTRY.match(stripped)
                            if m:
                                type_raw = m.group(3).strip()
                                prefix = ""
                                type_num = 0
                                parts = type_raw.split()
                                if len(parts) == 2:
                                    prefix = parts[0]
                                    type_num = _safe_int(parts[1])
                                else:
                                    type_num = _safe_int(parts[0])
                                data.contact_definitions.append(ContactDefinition(
                                    order=_safe_int(m.group(1)),
                                    contact_id=_safe_int(m.group(2)),
                                    type_code=type_raw,
                                    type_number=type_num,
                                    type_prefix=prefix,
                                    title=m.group(4).strip(),
                                ))
                                continue
                            if RE_PART_SEPARATOR.match(stripped):
                                in_contact_summary = False
                                continue
                        m = RE_CONTACT_HEADER.search(stripped)
                        if m:
                            data.contact_ids.append(_safe_int(m.group(1)))
                        else:
                            m = RE_CONTACT_TYPE.search(stripped)
                            if m and data.contact_ids:
                                data.contact_types[data.contact_ids[-1]] = _safe_int(m.group(1))
                        continue

                # ========== BODY (warnings + energy — bulk of file) ==========
                if state == "BODY":
                    # Transition to TAIL on timing header or termination
                    if "T i m i n g   i n f o r m a t i o n" in stripped:
                        state = "TAIL"
                        in_timing = True
                        continue
                    if "N o r m a l   t e r m i n a t i o n" in stripped:
                        data.termination.status = TerminationStatus.NORMAL
                        state = "TAIL"
                        continue
                    if "E r r o r   t e r m i n a t i o n" in stripped:
                        data.termination.status = TerminationStatus.ERROR
                        state = "TAIL"
                        continue

                    # --- Warnings / Errors (hot path — cheap prefix check) ---
                    if "***" in stripped:
                        m = RE_WARNING.match(stripped)
                        if m:
                            code = _safe_int(m.group(1))
                            data.warning_counts[code] = data.warning_counts.get(code, 0) + 1
                            last_warning_code = code
                            lines_after_warning = 0
                            continue
                        m = RE_ERROR.match(stripped)
                        if m:
                            code = _safe_int(m.group(1))
                            data.error_counts[code] = data.error_counts.get(code, 0) + 1
                            last_warning_code = None
                            continue
                        # "*** termination time reached ***"
                        if "termination time reached" in stripped:
                            data.termination.status = TerminationStatus.NORMAL
                        continue

                    # Warning context capture (tied interface info)
                    if last_warning_code is not None:
                        lines_after_warning += 1
                        if lines_after_warning <= 5:
                            if last_warning_code not in data.warning_messages:
                                data.warning_messages[last_warning_code] = ""
                            if data.warning_counts.get(last_warning_code, 0) <= 3:
                                data.warning_messages[last_warning_code] += stripped.strip() + " "
                            m_intf = RE_TIED_INTERFACE.search(stripped)
                            if m_intf:
                                intf_id = _safe_int(m_intf.group(1))
                                if last_warning_code not in data.warning_interfaces:
                                    data.warning_interfaces[last_warning_code] = set()
                                data.warning_interfaces[last_warning_code].add(intf_id)
                        else:
                            last_warning_code = None
                        continue

                    # --- Energy blocks ---
                    if in_energy_block:
                        m = RE_ENERGY_FIELD.match(stripped)
                        if m:
                            current_energy[m.group(1).strip().lower()] = _safe_float(m.group(2).strip())
                        elif not stripped.strip():
                            snap = self._build_energy_snapshot(current_cycle_info, current_energy)
                            if snap:
                                data.energy_snapshots.append(snap)
                            in_energy_block = False
                            current_energy = {}
                        continue

                    if "dt of cycle" in stripped:
                        m = RE_DT_CYCLE.search(stripped)
                        if m:
                            current_cycle_info = {
                                "cycle": _safe_int(m.group(1)),
                                "elem_type": m.group(2),
                                "elem_num": _safe_int(m.group(3)),
                                "part_num": _safe_int(m.group(4)),
                            }
                            current_energy = {}
                            in_energy_block = True
                        continue

                    # --- 100 smallest timesteps ---
                    if in_smallest_ts:
                        m = RE_SMALLEST_TS_ENTRY.match(stripped.strip())
                        if m:
                            data.smallest_timesteps.append(TimestepEntry(
                                element_type=m.group(1),
                                element_number=_safe_int(m.group(2)),
                                part_number=_safe_int(m.group(3)),
                                timestep=_safe_float(m.group(4)),
                            ))
                        elif not stripped.strip() and data.smallest_timesteps:
                            in_smallest_ts = False
                        continue

                    if "100 smallest timesteps" in stripped:
                        in_smallest_ts = True
                        continue

                    # --- Decomposition metrics (cheap keyword gate) ---
                    if "Minumum:" in stripped:
                        m = RE_DECOMP_MIN.search(stripped)
                        if m:
                            data.decomp_metrics.min_cost = _safe_float(m.group(1))
                        continue
                    if "Maximum:" in stripped:
                        m = RE_DECOMP_MAX.search(stripped)
                        if m:
                            data.decomp_metrics.max_cost = _safe_float(m.group(1))
                        continue
                    if "Standard Deviation:" in stripped:
                        m = RE_DECOMP_STDDEV.search(stripped)
                        if m:
                            data.decomp_metrics.std_deviation = _safe_float(m.group(1))
                        continue
                    if "Memory required for decomposition" in stripped:
                        m = RE_DECOMP_MEM.search(stripped)
                        if m:
                            data.decomp_metrics.decomp_memory = _safe_int(m.group(1))
                        continue
                    if "Additional dynamic memory" in stripped:
                        m = RE_DECOMP_DYN_MEM.search(stripped)
                        if m:
                            data.decomp_metrics.dynamic_memory = _safe_int(m.group(1))
                        continue

                    # --- Mass properties (cheap keyword gate) ---
                    if "m a s s" in stripped and "p r o p e r t i e s" in stripped:
                        m = RE_MASS_PART_HEADER.search(stripped)
                        if m:
                            data.mass_properties.append(MassProperty(part_id=_safe_int(m.group(1))))
                        continue
                    if data.mass_properties:
                        mp = data.mass_properties[-1]
                        if "mass center" in stripped:
                            if "x-coordinate" in stripped:
                                m = RE_MASS_CX.search(stripped)
                                if m:
                                    mp.cx = _safe_float(m.group(1))
                            elif "y-coordinate" in stripped:
                                m = RE_MASS_CY.search(stripped)
                                if m:
                                    mp.cy = _safe_float(m.group(1))
                            elif "z-coordinate" in stripped:
                                m = RE_MASS_CZ.search(stripped)
                                if m:
                                    mp.cz = _safe_float(m.group(1))
                            continue
                        if "total mass" in stripped:
                            m = RE_MASS_TOTAL.search(stripped)
                            if m:
                                mp.total_mass = _safe_float(m.group(1))
                            continue
                        if "i11" in stripped:
                            m = RE_MASS_I11.search(stripped)
                            if m:
                                mp.i11 = _safe_float(m.group(1))
                            continue
                        if "i22" in stripped:
                            m = RE_MASS_I22.search(stripped)
                            if m:
                                mp.i22 = _safe_float(m.group(1))
                            continue
                        if "i33" in stripped:
                            m = RE_MASS_I33.search(stripped)
                            if m:
                                mp.i33 = _safe_float(m.group(1))
                            continue

                    continue

                # ========== TAIL (timing, cpu, decomp, mass, summary) ==========
                # Only ~200 lines — no performance concern, run all patterns
                if in_timing:
                    if "T o t a l s" in stripped and "C P U" not in stripped:
                        in_timing = False
                        continue
                    m_interf = RE_INTERF_ID.match(stripped)
                    if m_interf:
                        data.contact_timing.append(ContactTiming(
                            interface_id=_safe_int(m_interf.group(1)),
                            cpu_seconds=_safe_float(m_interf.group(2)),
                            cpu_percent=_safe_float(m_interf.group(3)),
                            clock_seconds=_safe_float(m_interf.group(4)),
                            clock_percent=_safe_float(m_interf.group(5)),
                        ))
                        continue
                    m = RE_TIMING_ENTRY.match(stripped)
                    if m:
                        data.performance.append(PerformanceTiming(
                            component=m.group(1).strip(),
                            cpu_seconds=_safe_float(m.group(2)),
                            cpu_percent=_safe_float(m.group(3)),
                            clock_seconds=_safe_float(m.group(4)),
                            clock_percent=_safe_float(m.group(5)),
                        ))
                    continue

                if in_cpu_timing:
                    if "T o t a l s" in stripped:
                        in_cpu_timing = False
                        continue
                    m = RE_CPU_PROC.match(stripped.strip())
                    if m:
                        data.mpp_timing.append(MPPProcessorTiming(
                            processor_id=_safe_int(m.group(1)),
                            hostname=m.group(2),
                            cpu_ratio=_safe_float(m.group(3)),
                            cpu_seconds=_safe_float(m.group(4)),
                        ))
                    continue

                # --- Tail section markers ---
                if "C P U   T i m i n g" in stripped:
                    in_cpu_timing = True
                    continue
                if "T i m i n g   i n f o r m a t i o n" in stripped:
                    in_timing = True
                    continue

                # --- Termination markers (tail) ---
                if "N o r m a l" in stripped and "t e r m i n a t i o n" in stripped:
                    data.termination.status = TerminationStatus.NORMAL
                    continue
                if "E r r o r" in stripped and "t e r m i n a t i o n" in stripped:
                    data.termination.status = TerminationStatus.ERROR
                    continue

                # --- Mass properties (spaced header) ---
                if "m a s s" in stripped and "p r o p e r t i e s" in stripped:
                    m = RE_MASS_PART_HEADER.search(stripped)
                    if m:
                        data.mass_properties.append(MassProperty(part_id=_safe_int(m.group(1))))
                    continue

                # --- Mass property fields ---
                if data.mass_properties:
                    mp = data.mass_properties[-1]
                    if "mass center" in stripped:
                        if "x-coordinate" in stripped:
                            m = RE_MASS_CX.search(stripped)
                            if m:
                                mp.cx = _safe_float(m.group(1))
                        elif "y-coordinate" in stripped:
                            m = RE_MASS_CY.search(stripped)
                            if m:
                                mp.cy = _safe_float(m.group(1))
                        elif "z-coordinate" in stripped:
                            m = RE_MASS_CZ.search(stripped)
                            if m:
                                mp.cz = _safe_float(m.group(1))
                        continue
                    if "total mass" in stripped:
                        m = RE_MASS_TOTAL.search(stripped)
                        if m:
                            mp.total_mass = _safe_float(m.group(1))
                        continue
                    if "i11" in stripped:
                        m = RE_MASS_I11.search(stripped)
                        if m:
                            mp.i11 = _safe_float(m.group(1))
                        continue
                    if "i22" in stripped:
                        m = RE_MASS_I22.search(stripped)
                        if m:
                            mp.i22 = _safe_float(m.group(1))
                        continue
                    if "i33" in stripped:
                        m = RE_MASS_I33.search(stripped)
                        if m:
                            mp.i33 = _safe_float(m.group(1))
                        continue

                # --- Decomposition metrics ---
                if "Minumum:" in stripped:
                    m = RE_DECOMP_MIN.search(stripped)
                    if m:
                        data.decomp_metrics.min_cost = _safe_float(m.group(1))
                elif "Maximum:" in stripped:
                    m = RE_DECOMP_MAX.search(stripped)
                    if m:
                        data.decomp_metrics.max_cost = _safe_float(m.group(1))
                elif "Standard Deviation:" in stripped:
                    m = RE_DECOMP_STDDEV.search(stripped)
                    if m:
                        data.decomp_metrics.std_deviation = _safe_float(m.group(1))
                elif "Memory required for decomposition" in stripped:
                    m = RE_DECOMP_MEM.search(stripped)
                    if m:
                        data.decomp_metrics.decomp_memory = _safe_int(m.group(1))
                elif "Additional dynamic memory" in stripped:
                    m = RE_DECOMP_DYN_MEM.search(stripped)
                    if m:
                        data.decomp_metrics.dynamic_memory = _safe_int(m.group(1))

                # --- Final summary ---
                elif "Problem time" in stripped:
                    m = RE_PROBLEM_TIME.search(stripped)
                    if m:
                        data.termination.actual_time = _safe_float(m.group(1))
                elif "Problem cycle" in stripped:
                    m = RE_PROBLEM_CYCLE.search(stripped)
                    if m:
                        data.termination.total_cycles = _safe_int(m.group(1))
                elif "Total CPU time" in stripped:
                    m = RE_TOTAL_CPU.search(stripped)
                    if m:
                        data.termination.total_cpu_seconds = _safe_float(m.group(1))
                elif "CPU time per zone cycle" in stripped:
                    m = RE_CPU_PER_ZONE.search(stripped)
                    if m:
                        data.termination.cpu_per_zone_cycle_ns = _safe_float(m.group(1))
                elif "Clock time per zone cycle" in stripped:
                    m = RE_CLOCK_PER_ZONE.search(stripped)
                    if m:
                        data.termination.clock_per_zone_cycle_ns = _safe_float(m.group(1))
                elif "Start time" in stripped:
                    m = RE_START_TIME.search(stripped)
                    if m:
                        data.termination.start_datetime = m.group(1)
                elif "End time" in stripped:
                    m = RE_END_TIME.search(stripped)
                    if m:
                        data.termination.end_datetime = m.group(1)
                elif "Elapsed time" in stripped:
                    m = RE_ELAPSED.search(stripped)
                    if m:
                        data.termination.elapsed_seconds = _safe_float(m.group(1))

        if self.verbose:
            print(f"    d3hsp: 100% done ({line_counter} lines)")

        return data

    def _parse_header_line(self, line: str, data: D3hspData):
        for pattern, attr in [
            (RE_RUN_DATE, None),
            (RE_VERSION, "version"),
            (RE_REVISION, "revision"),
            (RE_PLATFORM, "platform"),
            (RE_OS_LEVEL, "os_level"),
            (RE_COMPILER, "compiler"),
            (RE_HOSTNAME, "hostname"),
            (RE_PRECISION, "precision"),
            (RE_LICENSEE, "licensee"),
        ]:
            m = pattern.search(line)
            if m:
                if attr is None:  # date/time
                    data.header.date = m.group(1)
                    data.header.time = m.group(2)
                else:
                    setattr(data.header, attr, m.group(1))
                return

        m = RE_INPUT_FILE.search(line)
        if m:
            data.header.input_file = m.group(1)
            return

        m = RE_CMD_LINE.search(line)
        if m and not data.header.input_file:
            data.header.input_file = m.group(1)
            return

        m = RE_MPP_PROCS.search(line)
        if m:
            data.header.num_procs = _safe_int(m.group(1))

    def _parse_model_size(self, line: str, data: D3hspData):
        for pattern, attr in [
            (RE_NUM_MATERIALS, "num_materials"),
            (RE_NUM_NODES, "num_nodes"),
            (RE_NUM_SOLIDS, "num_solid_elements"),
            (RE_NUM_SHELLS, "num_shell_elements"),
            (RE_NUM_BEAMS, "num_beam_elements"),
            (RE_NUM_TSHELLS, "num_thick_shell_elements"),
            (RE_NUM_SPH, "num_sph_particles"),
            (RE_NUM_CONTACTS, "num_contacts"),
            (RE_NUM_SPC, "num_spc_nodes"),
        ]:
            m = pattern.search(line)
            if m:
                setattr(data.model_size, attr, _safe_int(m.group(1)))
                return

    def _parse_computation_options(self, line: str, data: D3hspData):
        m = RE_TERM_TIME.search(line)
        if m:
            data.termination.target_time = _safe_float(m.group(1))

        m = RE_TSSFAC.search(line)
        if m:
            data.dt_scale_factor = _safe_float(m.group(1))

        m = RE_DT2MS.search(line)
        if m:
            data.dt2ms = _safe_float(m.group(1))

        m = RE_TSMIN.search(line)
        if m:
            data.tsmin = _safe_float(m.group(1))

    def _parse_part_block(self, lines: list[str]) -> PartDefinition | None:
        part = PartDefinition()
        name_line = ""
        expect_section_title = False
        expect_material_title = False

        for i, line in enumerate(lines):
            if expect_section_title:
                part.section_title = line.strip()
                expect_section_title = False
                continue
            if expect_material_title:
                part.material_title = line.strip()
                expect_material_title = False
                continue

            m = RE_PART_ID.search(line)
            if m:
                part.part_id = _safe_int(m.group(1))
                # Part name is usually 2-3 lines before part id
                for j in range(max(0, i - 3), i):
                    candidate = lines[j].strip()
                    if candidate and not candidate.startswith("*") and "part" not in candidate.lower():
                        part.name = candidate
                        break
                continue

            m = RE_SECTION_ID.search(line)
            if m:
                part.section_id = _safe_int(m.group(1))
                continue

            m = RE_MATERIAL_ID.search(line)
            if m:
                part.material_id = _safe_int(m.group(1))
                continue

            if RE_SECTION_TITLE_MARKER.search(line):
                expect_section_title = True
                continue

            if RE_MATERIAL_TITLE_MARKER.search(line):
                expect_material_title = True
                continue

            m = RE_MATERIAL_TYPE.search(line)
            if m:
                part.material_type = _safe_int(m.group(1))
                part.material_type_name = MATERIAL_TYPE_NAMES.get(
                    part.material_type, f"Type {part.material_type}"
                )
                continue

            m = RE_EOS_TYPE.search(line)
            if m:
                part.eos_type = _safe_int(m.group(1))
                continue

            m = RE_HG_TYPE.search(line)
            if m:
                part.hourglass_type = _safe_int(m.group(1))
                continue

            m = RE_DENSITY.search(line)
            if m:
                part.density = _safe_float(m.group(1))
                continue

            m = RE_HG_COEFF.search(line)
            if m:
                part.hourglass_coefficient = _safe_float(m.group(1))
                continue

            m = RE_YOUNGS_MOD.search(line)
            if m:
                part.youngs_modulus = _safe_float(m.group(1))
                continue

            m = RE_POISSON.search(line)
            if m:
                part.poisson_ratio = _safe_float(m.group(1))
                continue

            m = RE_SOLID_FORM.search(line)
            if m:
                part.solid_formulation = _safe_int(m.group(1))
                continue

        if part.part_id == 0:
            return None
        return part

    def _build_energy_snapshot(
        self, cycle_info: dict, energy: dict
    ) -> EnergySnapshot | None:
        if not cycle_info or not energy:
            return None

        def get_exact(key: str) -> float:
            """Get value by exact key match first, then substring."""
            if key in energy:
                return energy[key]
            return 0.0

        # Use exact key lookup from the energy dict
        # Keys are lowercase field names from the regex match
        return EnergySnapshot(
            cycle=cycle_info.get("cycle", 0),
            time=get_exact("time"),
            timestep=get_exact("time step"),
            kinetic=get_exact("kinetic energy"),
            internal=get_exact("internal energy"),
            spring_damper=get_exact("spring and damper energy"),
            hourglass=get_exact("hourglass energy"),
            system_damping=get_exact("system damping energy"),
            sliding_interface=get_exact("sliding interface energy"),
            external_work=get_exact("external work"),
            eroded_kinetic=get_exact("eroded kinetic energy"),
            eroded_internal=get_exact("eroded internal energy"),
            eroded_hourglass=get_exact("eroded hourglass energy"),
            total=get_exact("total energy"),
            energy_ratio=get_exact("total energy / initial energy") or 1.0,
            energy_ratio_no_eroded=get_exact("energy ratio w/o eroded energy") or 1.0,
            global_velocity=(
                get_exact("global x velocity"),
                get_exact("global y velocity"),
                get_exact("global z velocity"),
            ),
            controlling_element_type=cycle_info.get("elem_type", ""),
            controlling_element=cycle_info.get("elem_num", 0),
            controlling_part=cycle_info.get("part_num", 0),
            time_per_zone_ns=int(get_exact("time per zone cycle.(nanosec)")),
        )
