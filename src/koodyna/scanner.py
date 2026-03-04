"""Scanner: discover LS-DYNA result directories and maintain an index."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


# ── Default index location ────────────────────────────────────────────────────
DEFAULT_INDEX_PATH = Path.home() / ".koodyna" / "index.json"

# Files that mark a directory as an LS-DYNA result folder
_RESULT_MARKERS = {"d3plot", "d3hsp", "mes0000", "glstat"}

# Known LS-DYNA output files to inventory
_KNOWN_FILES = [
    "d3plot", "d3hsp", "glstat", "mes0000", "mes0001",
    "status.out", "nodout", "bndout",
    "load_profile.csv", "cont_profile.csv",
]


# ── Directory scanning ────────────────────────────────────────────────────────

def scan_for_result_dirs(base_dir: Path) -> list[Path]:
    """Recursively find all LS-DYNA result directories under *base_dir*.

    A directory qualifies if it contains at least one of the known result
    marker files (d3plot, d3hsp, mes0000, glstat).
    """
    found: list[Path] = []
    try:
        for candidate in sorted(base_dir.rglob("d3plot")):
            found.append(candidate.parent)
    except PermissionError:
        pass

    # Deduplicate (rglob may yield duplicates on some filesystems)
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in found:
        resolved = p.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(p)
    return sorted(unique)


def _infer_study_type(result_dir: Path) -> str:
    """Infer study type from the parent directory name."""
    parts = result_dir.parts
    if len(parts) >= 2:
        return parts[-2]
    return "unknown"


def _inventory_files(result_dir: Path) -> list[str]:
    """List which known LS-DYNA output files are present."""
    present: list[str] = []
    for name in _KNOWN_FILES:
        if (result_dir / name).exists():
            present.append(name)
    # Also note if slurm .err files are present
    if list(result_dir.glob("slurm*.err")):
        present.append("slurm.err")
    return present


# ── Index file I/O ────────────────────────────────────────────────────────────

def _empty_index() -> dict:
    return {
        "version": 1,
        "last_scan": None,
        "directories": {},
    }


def load_index(index_path: Path) -> dict:
    """Load existing index JSON.  Returns empty structure if file not found."""
    if not index_path.exists():
        return _empty_index()
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "directories" not in data:
            data["directories"] = {}
        return data
    except (json.JSONDecodeError, OSError):
        return _empty_index()


def save_index(index: dict, index_path: Path) -> None:
    """Save index to JSON file, creating parent directories as needed."""
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def update_index(index: dict, dirs: list[Path]) -> int:
    """Add newly-discovered directories to the index.

    Existing entries are preserved unchanged.
    Returns the count of newly added entries.
    """
    now = datetime.now(timezone.utc).isoformat()
    added = 0
    for d in dirs:
        key = str(d.resolve())
        if key not in index["directories"]:
            index["directories"][key] = {
                "study_type": _infer_study_type(d),
                "files": _inventory_files(d),
                "first_indexed": now,
                "last_analyzed": None,
                "status": "pending",
            }
            added += 1
    index["last_scan"] = now
    return added


def mark_analyzed(index: dict, result_dir: Path, status: str = "analyzed") -> None:
    """Update the status and last_analyzed timestamp for a directory."""
    key = str(result_dir.resolve())
    if key in index["directories"]:
        index["directories"][key]["last_analyzed"] = (
            datetime.now(timezone.utc).isoformat()
        )
        index["directories"][key]["status"] = status
    else:
        # Add entry on first encounter
        now = datetime.now(timezone.utc).isoformat()
        index["directories"][key] = {
            "study_type": _infer_study_type(result_dir),
            "files": _inventory_files(result_dir),
            "first_indexed": now,
            "last_analyzed": now,
            "status": status,
        }


# ── Batch scan ────────────────────────────────────────────────────────────────

def run_batch_scan(
    base_dir: Path,
    index_path: Path = DEFAULT_INDEX_PATH,
    verbose: bool = False,
) -> dict:
    """Discover all d3plot directories under *base_dir*, update the index, and
    return a summary dict.

    Does NOT run analysis — use run_batch_analyze() for that.
    """
    from rich.console import Console
    from rich.table import Table

    console = Console()

    console.print(f"\n[bold cyan]스캔 시작:[/bold cyan] {base_dir}")
    dirs = scan_for_result_dirs(base_dir)
    console.print(f"  d3plot 디렉터리 발견: [bold]{len(dirs):,}개[/bold]")

    index = load_index(index_path)
    added = update_index(index, dirs)
    save_index(index, index_path)

    console.print(f"  인덱스에 새로 추가: [bold green]{added:,}개[/bold green]")
    console.print(f"  인덱스 총 항목: [bold]{len(index['directories']):,}개[/bold]")
    console.print(f"  저장 위치: [dim]{index_path}[/dim]\n")

    # Summary by study type
    study_counts: dict[str, int] = {}
    for entry in index["directories"].values():
        st = entry.get("study_type", "unknown")
        study_counts[st] = study_counts.get(st, 0) + 1

    if study_counts and verbose:
        table = Table(title="Study Type 분포", show_header=True)
        table.add_column("Study Type", style="cyan")
        table.add_column("디렉터리 수", justify="right")
        for st, cnt in sorted(study_counts.items(), key=lambda x: -x[1])[:20]:
            table.add_row(st, str(cnt))
        console.print(table)

    return {
        "base_dir": str(base_dir),
        "dirs_found": len(dirs),
        "dirs_added": added,
        "total_indexed": len(index["directories"]),
        "index_path": str(index_path),
    }


def run_batch_analyze(
    index_path: Path = DEFAULT_INDEX_PATH,
    output_dir: Path | None = None,
    verbose: bool = False,
    limit: int = 0,
    reanalyze: bool = False,
) -> dict:
    """Run koodyna analysis on all pending (or all, if reanalyze=True) entries.

    For each directory:
    - Runs Analyzer.run()
    - Saves JSON report to output_dir/<study_type>/<case_name>.json
    - Updates index status (analyzed / failed)
    - Saves index every 50 cases to preserve progress

    Args:
        index_path:  Path to the index JSON file.
        output_dir:  Where to save JSON reports.
                     Defaults to ~/.koodyna/reports/
        verbose:     Show per-case progress.
        limit:       Max cases to process (0 = all).
        reanalyze:   If True, re-run even already-analyzed entries.

    Returns:
        Summary dict with counts.
    """
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

    console = Console()

    if output_dir is None:
        output_dir = DEFAULT_INDEX_PATH.parent / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    index = load_index(index_path)
    all_entries = list(index["directories"].items())

    # Filter to pending (or all if reanalyze)
    if reanalyze:
        targets = all_entries
    else:
        targets = [(p, e) for p, e in all_entries if e.get("status") != "analyzed"]

    if limit > 0:
        targets = targets[:limit]

    total = len(targets)
    if total == 0:
        console.print("[green]분석할 항목이 없습니다 (모두 완료됨).[/green]")
        return {"analyzed": 0, "failed": 0, "skipped": 0}

    console.print(
        f"\n[bold cyan]배치 분석 시작:[/bold cyan] {total:,}개 폴더\n"
        f"  리포트 저장 위치: [dim]{output_dir}[/dim]\n"
    )

    analyzed = failed = skipped = 0
    SAVE_INTERVAL = 50  # index 저장 주기

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("분석 중...", total=total)

        for i, (path_str, entry) in enumerate(targets):
            result_dir = Path(path_str)
            case_name = result_dir.name
            study_type = entry.get("study_type", "unknown")

            progress.update(task, description=f"[cyan]{study_type}[/cyan] / {case_name}")

            # Check d3hsp or mes0000 exists
            if not (result_dir / "d3hsp").exists() and not (result_dir / "mes0000").exists():
                skipped += 1
                mark_analyzed(index, result_dir, status="skipped")
                progress.advance(task)
                continue

            # Determine output path
            report_subdir = output_dir / study_type
            report_subdir.mkdir(parents=True, exist_ok=True)
            json_path = report_subdir / f"{case_name}.json"

            try:
                from koodyna.analyzer import Analyzer
                from koodyna.report.json_report import write_json_report

                analyzer = Analyzer(result_dir, verbose=False)
                report = analyzer.run()
                write_json_report(report, json_path)

                mark_analyzed(index, result_dir, status="analyzed")
                analyzed += 1

                if verbose:
                    n_crit = sum(
                        1 for f in report.findings
                        if hasattr(f, "severity") and str(f.severity) in ("CRITICAL", "Severity.CRITICAL")
                    )
                    console.print(f"  [green]✓[/green] {study_type}/{case_name}  CRIT:{n_crit}")

            except Exception as exc:
                mark_analyzed(index, result_dir, status="failed")
                failed += 1
                if verbose:
                    console.print(f"  [red]✗[/red] {study_type}/{case_name}: {exc}")

            progress.advance(task)

            # Periodic save
            if (i + 1) % SAVE_INTERVAL == 0:
                save_index(index, index_path)

    # Final save
    save_index(index, index_path)

    console.print(
        f"\n[bold]배치 분석 완료:[/bold]"
        f"  성공 [green]{analyzed:,}[/green]"
        f"  실패 [red]{failed:,}[/red]"
        f"  건너뜀 [yellow]{skipped:,}[/yellow]\n"
        f"  리포트: [dim]{output_dir}[/dim]"
    )

    return {"analyzed": analyzed, "failed": failed, "skipped": skipped}


def print_index(index_path: Path = DEFAULT_INDEX_PATH) -> None:
    """Print a summary table of the index to the terminal."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    index = load_index(index_path)

    if not index["directories"]:
        console.print(
            "[yellow]인덱스가 비어 있습니다. "
            "먼저 --scan <BASE_DIR> 명령으로 스캔하세요.[/yellow]"
        )
        return

    total = len(index["directories"])
    analyzed = sum(
        1 for e in index["directories"].values() if e.get("status") == "analyzed"
    )
    failed = sum(
        1 for e in index["directories"].values() if e.get("status") == "failed"
    )
    pending = total - analyzed - failed

    console.print(
        f"\n인덱스: [bold]{index_path}[/bold]"
        f"  총 [bold]{total:,}개[/bold]"
        f"  분석완료 [green]{analyzed:,}[/green]"
        f"  실패 [red]{failed:,}[/red]"
        f"  대기 [yellow]{pending:,}[/yellow]\n"
    )

    # Group by study type
    by_study: dict[str, list[tuple[str, dict]]] = {}
    for path_str, entry in index["directories"].items():
        st = entry.get("study_type", "unknown")
        by_study.setdefault(st, []).append((path_str, entry))

    table = Table(show_header=True, show_lines=False)
    table.add_column("Study Type", style="cyan", min_width=24)
    table.add_column("디렉터리", style="dim", overflow="fold")
    table.add_column("파일", style="dim")
    table.add_column("상태", justify="center")
    table.add_column("마지막 분석", style="dim")

    for st in sorted(by_study):
        for path_str, entry in sorted(by_study[st]):
            status = entry.get("status", "pending")
            color = {"analyzed": "green", "failed": "red"}.get(status, "yellow")
            last = (entry.get("last_analyzed") or "-")[:19].replace("T", " ")
            files = ", ".join(entry.get("files", []))
            short_path = Path(path_str).name
            table.add_row(
                st, short_path, files,
                f"[{color}]{status}[/{color}]",
                last,
            )

    console.print(table)
