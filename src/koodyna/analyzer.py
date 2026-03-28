"""Main orchestrator that ties parsers, analysis, and report together."""

from pathlib import Path

from koodyna.models import Report
from koodyna.parsers.d3hsp import D3hspParser
from koodyna.parsers.glstat import GlstatParser
from koodyna.parsers.status import StatusParser
from koodyna.parsers.profile import ProfileParser, ContProfileParser
from koodyna.parsers.messag import parse_all_mes_files
from koodyna.parsers.matsum import MatsumParser
from koodyna.parsers.element_mapper import find_and_parse_input_deck
from koodyna.parsers.rcforc import RcforcParser
from koodyna.analysis.energy import analyze_energy
from koodyna.analysis.timestep import analyze_timestep
from koodyna.analysis.warnings import analyze_warnings
from koodyna.analysis.contact import analyze_contacts
from koodyna.analysis.performance import analyze_performance, project_scaling
from koodyna.analysis.diagnostics import run_diagnostics
from koodyna.analysis.failure_analysis import analyze_failure_source
from koodyna.analysis.matsum_analysis import analyze_matsum
from koodyna.analysis.implicit_diagnostics import analyze_implicit_solver, is_implicit_simulation
from koodyna.analysis.numerical_instability import (
    detect_shooting_nodes,
    detect_high_frequency_oscillation,
    detect_excessive_reaction_force,
    detect_hourglass_dominance,
    detect_kinetic_energy_explosion,
    detect_contact_energy_anomaly,
    detect_timestep_volatility,
    detect_nan_in_energy,
    detect_negative_energy_components,
    diagnose_slurm_failures,
)
from koodyna.parsers.slurm import find_and_parse_slurm
from koodyna.models import Finding, Severity


def _deduplicate_findings(findings: list[Finding]) -> list[Finding]:
    """Remove lower-priority findings that are made redundant by higher-priority ones.

    Rules:
    - "High sliding interface energy" (WARNING) is suppressed when any CRITICAL or WARNING
      finding for negative or excessive sliding energy already exists.
    """
    titles = {f.title for f in findings}
    has_superior_sliding = any(
        ("Negative sliding" in t or "Excessive contact sliding" in t)
        for t in titles
        if any(
            f.severity in (Severity.CRITICAL, Severity.WARNING) and f.title == t
            for f in findings
        )
    )

    result: list[Finding] = []
    for f in findings:
        if f.title == "High sliding interface energy" and has_superior_sliding:
            continue  # suppressed — more specific sliding finding already present
        result.append(f)
    return result


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

        slurm_info = None
        if self.verbose:
            print(f"  Checking for slurm error files...")
        slurm_info = find_and_parse_slurm(self.result_dir)
        if slurm_info:
            files_found.append(f"slurm_{slurm_info.job_id}.err")

        matsum_materials = {}
        if "matsum" in discovered:
            if self.verbose:
                print(f"  Parsing matsum...")
            matsum_materials = MatsumParser(discovered["matsum"]).parse()
            files_found.append("matsum")

        # rcforc parsing
        rcforc_interfaces = {}
        if "rcforc" in discovered:
            if self.verbose:
                print(f"  Parsing rcforc...")
            try:
                rcforc_interfaces = RcforcParser(discovered["rcforc"]).parse()
                files_found.append("rcforc")
                if self.verbose:
                    print(f"  rcforc: {len(rcforc_interfaces)} interfaces")
            except Exception:
                pass

        # Element→part mapping from input deck (.k / .dyn files)
        elem_to_part_deck: dict[int, int] = {}
        try:
            elem_to_part_deck = find_and_parse_input_deck(self.result_dir)
            if elem_to_part_deck and self.verbose:
                print(f"  element_mapper: {len(elem_to_part_deck)} elem→part mappings")
        except Exception:
            pass

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
            report.implicit_steps = d3hsp_data.implicit_steps

        if slurm_info:
            report.slurm_info = slurm_info

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

        # --- Phase 3b: Merge mes error counts with d3hsp ---
        # In MPP runs, errors may only appear in non-zero rank mes files
        merged_error_counts: dict[int, int] = dict(d3hsp_data.error_counts) if d3hsp_data else {}
        merged_error_messages: dict[int, str] = dict(d3hsp_data.error_messages) if d3hsp_data else {}
        if mes_data:
            for md in mes_data:
                for code, count in md.error_counts.items():
                    if code not in merged_error_counts:
                        merged_error_counts[code] = count
                    else:
                        merged_error_counts[code] = max(merged_error_counts[code], count)
                # Use error details from mes files as messages if d3hsp doesn't have them
                for detail in md.error_details:
                    # detail format: "Error NNNNN: description text"
                    parts = detail.split(": ", 1)
                    if len(parts) == 2:
                        try:
                            code = int(parts[0].replace("Error ", ""))
                            if code not in merged_error_messages:
                                merged_error_messages[code] = parts[1]
                        except ValueError:
                            pass

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

        # Enrich smallest_timesteps with part_number from input deck (element_mapper)
        # Only fill in where part_number is unknown (0)
        if elem_to_part_deck:
            for ts in report.timestep.smallest_timesteps:
                if ts.part_number == 0 and ts.element_number in elem_to_part_deck:
                    ts.part_number = elem_to_part_deck[ts.element_number]

        if self.verbose:
            print(f"  Running warning analysis...")
        warning_entries, warning_findings = analyze_warnings(
            warning_counts=d3hsp_data.warning_counts if d3hsp_data else {},
            warning_messages=d3hsp_data.warning_messages if d3hsp_data else {},
            warning_interfaces=d3hsp_data.warning_interfaces if d3hsp_data else {},
            error_counts=merged_error_counts,
            error_messages=merged_error_messages,
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

        # glstat-based instability checks
        if energy_snapshots:
            if self.verbose:
                print(f"    Checking hourglass energy...")
            numerical_findings.extend(detect_hourglass_dominance(energy_snapshots))

            if self.verbose:
                print(f"    Checking kinetic energy stability...")
            numerical_findings.extend(detect_kinetic_energy_explosion(energy_snapshots))

            if self.verbose:
                print(f"    Checking contact energy...")
            numerical_findings.extend(detect_contact_energy_anomaly(energy_snapshots))

            if self.verbose:
                print(f"    Checking timestep stability...")
            numerical_findings.extend(detect_timestep_volatility(energy_snapshots))

            if self.verbose:
                print(f"    Checking for NaN in energy...")
            numerical_findings.extend(detect_nan_in_energy(energy_snapshots))

            if self.verbose:
                print(f"    Checking for negative energy components...")
            numerical_findings.extend(detect_negative_energy_components(energy_snapshots))

        # Slurm failure diagnostics
        if slurm_info:
            if self.verbose:
                print(f"    Diagnosing slurm failures...")
            numerical_findings.extend(diagnose_slurm_failures(slurm_info))

        # --- Phase 5c: matsum analysis ---
        matsum_hg_entries, matsum_findings = [], []
        if matsum_materials:
            if self.verbose:
                print(f"  Analyzing matsum ({len(matsum_materials)} materials)...")
            matsum_hg_entries, matsum_findings = analyze_matsum(matsum_materials)
            report.matsum_hg_entries = matsum_hg_entries

        # Assign rcforc data to report
        if rcforc_interfaces:
            report.rcforc_interfaces = rcforc_interfaces

        # --- Phase 5d: Implicit solver diagnostics ---
        implicit_findings: list = []
        kw_counts = d3hsp_data.keyword_counts if d3hsp_data else {}
        report.is_implicit = is_implicit_simulation(kw_counts)
        if report.is_implicit:
            if self.verbose:
                print(f"  Analyzing implicit solver...")
            implicit_findings = analyze_implicit_solver(
                keyword_counts=kw_counts,
                error_counts=merged_error_counts,
                error_messages=merged_error_messages,
                energy_snapshots=energy_snapshots,
                implicit_steps=report.implicit_steps,
            )

        # --- Phase 6: Diagnostics ---
        if self.verbose:
            print(f"  Running diagnostics...")
        all_findings = run_diagnostics(
            termination=report.termination,
            energy_findings=energy_analysis.findings,
            timestep_findings=timestep_analysis.findings,
            warning_findings=warning_findings,
            contact_findings=contact_findings,
            performance_findings=perf_findings + failure_findings + numerical_findings + matsum_findings + implicit_findings,
            contact_dt_limit=report.contact_dt_limit,
            min_dt=timestep_analysis.min_dt,
            interface_surface_timesteps=report.interface_surface_timesteps,
            mass_properties=report.mass_properties,
            decomp_metrics=report.decomp_metrics,
            warnings=report.warnings,
            energy_snapshots=energy_analysis.snapshots,
            performance=report.performance,
            smallest_timesteps=timestep_analysis.smallest_timesteps,
            parts=report.parts,
            contact_definitions=report.contact_definitions,
        )
        report.findings = _deduplicate_findings(all_findings)

        return report

    def _discover_files(self) -> dict:
        """Auto-discover parseable files in the result directory."""
        d = self.result_dir
        files: dict = {}

        for name in ["d3hsp", "glstat", "status.out", "load_profile.csv", "cont_profile.csv", "matsum", "rcforc"]:
            p = d / name
            if p.exists() and p.stat().st_size > 0:
                files[name] = p

        mes = sorted(d.glob("mes[0-9][0-9][0-9][0-9]"))
        if mes:
            files["mes"] = mes

        return files
