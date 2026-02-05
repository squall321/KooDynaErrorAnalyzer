"""Main orchestrator that ties parsers, analysis, and report together."""

from pathlib import Path

from koodyna.models import Report
from koodyna.parsers.d3hsp import D3hspParser
from koodyna.parsers.glstat import GlstatParser
from koodyna.parsers.status import StatusParser
from koodyna.parsers.profile import ProfileParser, ContProfileParser
from koodyna.parsers.messag import parse_all_mes_files
from koodyna.analysis.energy import analyze_energy
from koodyna.analysis.timestep import analyze_timestep
from koodyna.analysis.warnings import analyze_warnings
from koodyna.analysis.contact import analyze_contacts
from koodyna.analysis.performance import analyze_performance, project_scaling
from koodyna.analysis.diagnostics import run_diagnostics
from koodyna.analysis.failure_analysis import analyze_failure_source
from koodyna.analysis.numerical_instability import (
    detect_shooting_nodes,
    detect_high_frequency_oscillation,
    detect_excessive_reaction_force,
)


class Analyzer:
    """Main analysis orchestrator."""

    def __init__(self, result_dir: Path, verbose: bool = False):
        self.result_dir = result_dir
        self.verbose = verbose

    def run(self) -> Report:
        report = Report()
        files_found: list[str] = []

        # --- Phase 1: Discover files ---
        discovered = self._discover_files()

        # --- Phase 2: Parse files ---
        d3hsp_data = None
        if "d3hsp" in discovered:
            if self.verbose:
                print(f"  Parsing d3hsp...")
            d3hsp_data = D3hspParser(discovered["d3hsp"], verbose=self.verbose).parse()
            files_found.append("d3hsp")

        glstat_snapshots = []
        if "glstat" in discovered:
            if self.verbose:
                print(f"  Parsing glstat...")
            glstat_snapshots = GlstatParser(discovered["glstat"]).parse()
            files_found.append("glstat")

        status_info = None
        if "status.out" in discovered:
            if self.verbose:
                print(f"  Parsing status.out...")
            status_info = StatusParser(discovered["status.out"]).parse()
            files_found.append("status.out")

        load_abs, load_pct = [], []
        if "load_profile.csv" in discovered:
            if self.verbose:
                print(f"  Parsing load_profile.csv...")
            load_abs, load_pct = ProfileParser(discovered["load_profile.csv"]).parse()
            files_found.append("load_profile.csv")

        cont_abs, cont_pct = [], []
        if "cont_profile.csv" in discovered:
            if self.verbose:
                print(f"  Parsing cont_profile.csv...")
            cont_abs, cont_pct = ContProfileParser(discovered["cont_profile.csv"]).parse()
            files_found.append("cont_profile.csv")

        mes_data = []
        if "mes" in discovered:
            if self.verbose:
                print(f"  Parsing {len(discovered['mes'])} mes files...")
            mes_data = parse_all_mes_files(self.result_dir)
            files_found.append(f"mes[0000-{len(discovered['mes'])-1:04d}]")

        report.files_found = files_found

        # --- Phase 3: Populate report from d3hsp ---
        if d3hsp_data:
            report.header = d3hsp_data.header
            report.model_size = d3hsp_data.model_size
            report.termination = d3hsp_data.termination
            report.parts = d3hsp_data.parts
            report.performance = d3hsp_data.performance
            report.contact_timing = d3hsp_data.contact_timing
            report.mpp_timing = d3hsp_data.mpp_timing
            report.keyword_counts = d3hsp_data.keyword_counts
            report.contact_definitions = d3hsp_data.contact_definitions
            report.decomp_metrics = d3hsp_data.decomp_metrics
            report.mass_properties = d3hsp_data.mass_properties

        if status_info:
            report.status = status_info

        report.load_profile_abs = load_abs
        report.load_profile_pct = load_pct
        report.cont_profile_abs = cont_abs
        report.cont_profile_pct = cont_pct

        # Wire mes data
        if mes_data:
            # Use rank 0 for interface warning summary
            if mes_data[0].interface_warning_counts:
                report.interface_warning_counts = mes_data[0].interface_warning_counts
            # Merge initial penetrations across all ranks
            all_pens: dict[int, int] = {}
            for md in mes_data:
                for intf_id, count in md.initial_penetrations.items():
                    all_pens[intf_id] = all_pens.get(intf_id, 0) + count
            report.initial_penetrations = all_pens
            # Memory per rank
            report.memory_per_rank = [md.max_memory_d for md in mes_data]
            # Surface timestep + contact dt limit (from rank 0)
            rank0 = next((md for md in mes_data if md.rank == 0), None)
            if rank0:
                report.interface_surface_timesteps = rank0.interface_surface_timesteps
                report.contact_dt_limit = rank0.contact_dt_limit
            # Build element→processor lookup from mes timestep data
            elem_to_proc: dict[tuple[str, int], int] = {}
            for md in mes_data:
                for ts in md.smallest_timesteps:
                    key = (ts.element_type, ts.element_number)
                    if key not in elem_to_proc:
                        elem_to_proc[key] = ts.processor_id

        # --- Phase 4: Analysis ---
        # Use glstat snapshots if available, otherwise d3hsp energy data
        energy_snapshots = glstat_snapshots or (d3hsp_data.energy_snapshots if d3hsp_data else [])

        if self.verbose:
            print(f"  Running energy analysis ({len(energy_snapshots)} snapshots)...")
        energy_analysis = analyze_energy(energy_snapshots)
        report.energy = energy_analysis

        if self.verbose:
            print(f"  Running timestep analysis...")
        timestep_analysis = analyze_timestep(
            smallest_timesteps=d3hsp_data.smallest_timesteps if d3hsp_data else [],
            energy_snapshots=energy_snapshots,
            dt_scale_factor=d3hsp_data.dt_scale_factor if d3hsp_data else 0.0,
            dt2ms=d3hsp_data.dt2ms if d3hsp_data else 0.0,
            tsmin=d3hsp_data.tsmin if d3hsp_data else 0.0,
        )
        report.timestep = timestep_analysis

        # Map processor IDs onto timestep entries from mes data
        if mes_data:
            for ts in report.timestep.smallest_timesteps:
                key = (ts.element_type, ts.element_number)
                if key in elem_to_proc:
                    ts.processor_id = elem_to_proc[key]

        if self.verbose:
            print(f"  Running warning analysis...")
        warning_entries, warning_findings = analyze_warnings(
            warning_counts=d3hsp_data.warning_counts if d3hsp_data else {},
            warning_messages=d3hsp_data.warning_messages if d3hsp_data else {},
            warning_interfaces=d3hsp_data.warning_interfaces if d3hsp_data else {},
            error_counts=d3hsp_data.error_counts if d3hsp_data else {},
            error_messages=d3hsp_data.error_messages if d3hsp_data else {},
        )
        report.warnings = warning_entries

        if self.verbose:
            print(f"  Running contact analysis...")
        contact_findings = analyze_contacts(
            contact_timing=d3hsp_data.contact_timing if d3hsp_data else [],
            contact_types=d3hsp_data.contact_types if d3hsp_data else {},
            total_clock_seconds=d3hsp_data.termination.elapsed_seconds if d3hsp_data else 0.0,
        )

        if self.verbose:
            print(f"  Running performance analysis...")
        perf_findings = analyze_performance(
            timing=d3hsp_data.performance if d3hsp_data else [],
            mpp_timing=d3hsp_data.mpp_timing if d3hsp_data else [],
            load_profile_pct=load_pct,
        )

        # Scaling projections
        current_cores = report.header.num_procs if report.header.num_procs > 0 else 1
        report.scaling_projections = project_scaling(
            timing=d3hsp_data.performance if d3hsp_data else [],
            current_cores=current_cores,
            elapsed_seconds=report.termination.elapsed_seconds,
        )

        # --- Phase 5: Failure Source Analysis ---
        if self.verbose:
            print(f"  Analyzing failure sources...")

        # Find messag file if it exists
        messag_path = None
        for candidate in ['messag', 'message', 'MESSAG']:
            path = self.result_dir / candidate
            if path.exists():
                messag_path = path
                break

        failure_findings = analyze_failure_source(
            messag_path=messag_path,
            d3hsp_path=discovered.get("d3hsp"),
            smallest_timesteps=d3hsp_data.smallest_timesteps if d3hsp_data else [],
            result_dir=self.result_dir,
        )

        # --- Phase 5b: Numerical Instability Analysis ---
        if self.verbose:
            print(f"  Analyzing numerical instabilities...")

        # Find nodout and bndout files
        nodout_path = self.result_dir / "nodout" if (self.result_dir / "nodout").exists() else None
        bndout_path = self.result_dir / "bndout" if (self.result_dir / "bndout").exists() else None

        numerical_findings: list = []

        if nodout_path:
            if self.verbose:
                print(f"    Checking for shooting nodes...")
            numerical_findings.extend(detect_shooting_nodes(nodout_path))

            if self.verbose:
                print(f"    Checking for high-frequency oscillations...")
            numerical_findings.extend(detect_high_frequency_oscillation(nodout_path))

        if bndout_path:
            if self.verbose:
                print(f"    Checking for excessive reaction forces...")
            numerical_findings.extend(detect_excessive_reaction_force(bndout_path))

        # --- Phase 6: Diagnostics ---
        if self.verbose:
            print(f"  Running diagnostics...")
        all_findings = run_diagnostics(
            termination=report.termination,
            energy_findings=energy_analysis.findings,
            timestep_findings=timestep_analysis.findings,
            warning_findings=warning_findings,
            contact_findings=contact_findings,
            performance_findings=perf_findings + failure_findings + numerical_findings,
            contact_dt_limit=report.contact_dt_limit,
            min_dt=timestep_analysis.min_dt,
            interface_surface_timesteps=report.interface_surface_timesteps,
            mass_properties=report.mass_properties,
            decomp_metrics=report.decomp_metrics,
            warnings=report.warnings,
            energy_snapshots=energy_analysis.snapshots,
        )
        report.findings = all_findings

        return report

    def _discover_files(self) -> dict:
        """Auto-discover parseable files in the result directory."""
        d = self.result_dir
        files: dict = {}

        for name in ["d3hsp", "glstat", "status.out", "load_profile.csv", "cont_profile.csv"]:
            p = d / name
            if p.exists() and p.stat().st_size > 0:
                files[name] = p

        mes = sorted(d.glob("mes[0-9][0-9][0-9][0-9]"))
        if mes:
            files["mes"] = mes

        return files
