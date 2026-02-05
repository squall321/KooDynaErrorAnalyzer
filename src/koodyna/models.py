"""Data models for LS-DYNA result analysis."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class TerminationStatus(Enum):
    NORMAL = "NORMAL"
    ERROR = "ERROR"
    INCOMPLETE = "INCOMPLETE"


@dataclass
class SimulationHeader:
    version: str = ""
    revision: str = ""
    date: str = ""
    time: str = ""
    platform: str = ""
    os_level: str = ""
    compiler: str = ""
    hostname: str = ""
    precision: str = ""
    input_file: str = ""
    licensee: str = ""
    num_procs: int = 0


@dataclass
class ModelSize:
    num_materials: int = 0
    num_nodes: int = 0
    num_solid_elements: int = 0
    num_shell_elements: int = 0
    num_beam_elements: int = 0
    num_thick_shell_elements: int = 0
    num_sph_particles: int = 0
    num_contacts: int = 0
    num_spc_nodes: int = 0
    num_parts: int = 0


@dataclass
class TerminationInfo:
    status: TerminationStatus = TerminationStatus.INCOMPLETE
    target_time: float = 0.0
    actual_time: float = 0.0
    total_cycles: int = 0
    total_cpu_seconds: float = 0.0
    elapsed_seconds: float = 0.0
    cpu_per_zone_cycle_ns: float = 0.0
    clock_per_zone_cycle_ns: float = 0.0
    start_datetime: str = ""
    end_datetime: str = ""
    error_code: Optional[int] = None
    error_message: Optional[str] = None


@dataclass
class WarningEntry:
    code: int = 0
    count: int = 0
    message: str = ""
    severity: Severity = Severity.WARNING
    recommendation: str = ""
    affected_interfaces: list[int] = field(default_factory=list)
    sample_details: list[str] = field(default_factory=list)


@dataclass
class EnergySnapshot:
    cycle: int = 0
    time: float = 0.0
    timestep: float = 0.0
    kinetic: float = 0.0
    internal: float = 0.0
    spring_damper: float = 0.0
    hourglass: float = 0.0
    system_damping: float = 0.0
    sliding_interface: float = 0.0
    external_work: float = 0.0
    eroded_kinetic: float = 0.0
    eroded_internal: float = 0.0
    eroded_hourglass: float = 0.0
    total: float = 0.0
    energy_ratio: float = 1.0
    energy_ratio_no_eroded: float = 1.0
    global_velocity: tuple[float, float, float] = (0.0, 0.0, 0.0)
    controlling_element_type: str = ""
    controlling_element: int = 0
    controlling_part: int = 0
    time_per_zone_ns: int = 0


@dataclass
class EnergyAnalysis:
    snapshots: list[EnergySnapshot] = field(default_factory=list)
    initial_total_energy: float = 0.0
    final_total_energy: float = 0.0
    max_hourglass_ratio: float = 0.0
    max_sliding_ratio: float = 0.0
    energy_ratio_range: tuple[float, float] = (1.0, 1.0)
    findings: list["Finding"] = field(default_factory=list)


@dataclass
class TimestepEntry:
    element_type: str = ""
    element_number: int = 0
    part_number: int = 0
    timestep: float = 0.0
    processor_id: int = -1  # -1 = unknown, from mesXXXX file number


@dataclass
class TimestepAnalysis:
    smallest_timesteps: list[TimestepEntry] = field(default_factory=list)
    controlling_parts: dict[int, int] = field(default_factory=dict)
    initial_dt: float = 0.0
    final_dt: float = 0.0
    min_dt: float = 0.0
    dt_scale_factor: float = 0.0
    dt2ms: float = 0.0
    tsmin: float = 0.0
    findings: list["Finding"] = field(default_factory=list)


@dataclass
class PartDefinition:
    part_id: int = 0
    name: str = ""
    section_id: int = 0
    material_id: int = 0
    material_type: int = 0
    material_type_name: str = ""
    eos_type: int = 0
    hourglass_type: int = 0
    density: float = 0.0
    youngs_modulus: float = 0.0
    poisson_ratio: float = 0.0
    hourglass_coefficient: float = 0.0
    solid_formulation: int = 0
    section_title: str = ""
    material_title: str = ""


@dataclass
class PerformanceTiming:
    component: str = ""
    cpu_seconds: float = 0.0
    cpu_percent: float = 0.0
    clock_seconds: float = 0.0
    clock_percent: float = 0.0


@dataclass
class ContactTiming:
    interface_id: int = 0
    cpu_seconds: float = 0.0
    cpu_percent: float = 0.0
    clock_seconds: float = 0.0
    clock_percent: float = 0.0


@dataclass
class MPPProcessorTiming:
    processor_id: int = 0
    hostname: str = ""
    cpu_ratio: float = 0.0
    cpu_seconds: float = 0.0


@dataclass
class LoadProfileEntry:
    processor_id: int = 0
    solids: float = 0.0
    shells: float = 0.0
    tshells: float = 0.0
    beams: float = 0.0
    sph: float = 0.0
    e_other: float = 0.0
    force_shr: float = 0.0
    tstep_shr: float = 0.0
    swtch_shr: float = 0.0
    matrl_shr: float = 0.0
    elmnt_shr: float = 0.0
    time_step: float = 0.0
    contact: float = 0.0
    rigid_bdy: float = 0.0
    others: float = 0.0


@dataclass
class ContactDefinition:
    order: int = 0
    contact_id: int = 0
    type_code: str = ""
    type_number: int = 0
    type_prefix: str = ""
    title: str = ""


@dataclass
class ContProfileEntry:
    processor_id: int = 0
    interface_timings: dict[int, float] = field(default_factory=dict)


@dataclass
class ScalingProjection:
    target_cores: int = 0
    est_elapsed_seconds: float = 0.0
    est_speedup: float = 0.0
    est_efficiency: float = 0.0
    est_sharing_pct: float = 0.0


@dataclass
class InterfaceSurfaceTimestep:
    interface_id: int = 0
    surface: str = ""           # "surfa" or "surfb"
    type_code: str = ""         # e.g. "13", "o 6"
    surface_timestep: float = 0.0
    controlling_node_id: int = 0
    part_id: int = 0
    is_active: bool = True      # False if timestep == 1e16


@dataclass
class DecompMetrics:
    min_cost: float = 0.0
    max_cost: float = 0.0
    std_deviation: float = 0.0
    decomp_memory: int = 0
    dynamic_memory: int = 0


@dataclass
class MassProperty:
    part_id: int = 0
    total_mass: float = 0.0
    cx: float = 0.0
    cy: float = 0.0
    cz: float = 0.0
    i11: float = 0.0
    i22: float = 0.0
    i33: float = 0.0


@dataclass
class StatusInfo:
    cpu_per_zone_ns: int = 0
    avg_cpu_per_zone_ns: int = 0
    avg_clock_per_zone_ns: int = 0
    est_total_cpu_sec: int = 0
    est_cpu_remain_sec: int = 0
    est_total_clock_sec: int = 0
    est_clock_remain_sec: int = 0


@dataclass
class Finding:
    severity: Severity = Severity.INFO
    category: str = ""
    title: str = ""
    description: str = ""
    recommendation: str = ""


@dataclass
class Report:
    header: SimulationHeader = field(default_factory=SimulationHeader)
    model_size: ModelSize = field(default_factory=ModelSize)
    termination: TerminationInfo = field(default_factory=TerminationInfo)
    warnings: list[WarningEntry] = field(default_factory=list)
    energy: EnergyAnalysis = field(default_factory=EnergyAnalysis)
    timestep: TimestepAnalysis = field(default_factory=TimestepAnalysis)
    parts: list[PartDefinition] = field(default_factory=list)
    performance: list[PerformanceTiming] = field(default_factory=list)
    contact_timing: list[ContactTiming] = field(default_factory=list)
    mpp_timing: list[MPPProcessorTiming] = field(default_factory=list)
    load_profile_abs: list[LoadProfileEntry] = field(default_factory=list)
    load_profile_pct: list[LoadProfileEntry] = field(default_factory=list)
    contact_definitions: list[ContactDefinition] = field(default_factory=list)
    cont_profile_abs: list[ContProfileEntry] = field(default_factory=list)
    cont_profile_pct: list[ContProfileEntry] = field(default_factory=list)
    interface_warning_counts: dict[int, int] = field(default_factory=dict)
    initial_penetrations: dict[int, int] = field(default_factory=dict)
    memory_per_rank: list[int] = field(default_factory=list)
    scaling_projections: list[ScalingProjection] = field(default_factory=list)
    interface_surface_timesteps: list[InterfaceSurfaceTimestep] = field(default_factory=list)
    contact_dt_limit: float = 0.0  # LS-DYNA 권장 접촉 안정성 dt 상한
    decomp_metrics: DecompMetrics = field(default_factory=DecompMetrics)
    mass_properties: list[MassProperty] = field(default_factory=list)
    status: StatusInfo = field(default_factory=StatusInfo)
    findings: list[Finding] = field(default_factory=list)
    keyword_counts: dict[str, int] = field(default_factory=dict)
    files_found: list[str] = field(default_factory=list)
