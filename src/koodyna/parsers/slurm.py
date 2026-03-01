"""Parser for Slurm job output files (slurm_*.err)."""

import re
from pathlib import Path

from koodyna.models import SlurmJobInfo

# --- Regex patterns ---
# [node001:184025] Signal: Segmentation fault (11)
RE_SIGNAL = re.compile(r'Signal:\s+(.+?)\s+\((\d+)\)')
# [node001:184025] Failing at address: 0xfffffffe646feb2c
RE_FAIL_ADDR = re.compile(r'Failing at address:\s+(0x[0-9a-fA-F]+)')
# Stack trace frame: [ 0] /opt/ls-dyna/lsdyna_R16.1.1(+0x3f87ad0)[0x...]
RE_STACK_FRAME = re.compile(r'^\[?\s*\d+\]\s+\S+')
# Node name: [node001:184025]
RE_NODE = re.compile(r'\[(\w+):\d+\]')
# Exit code:    3
RE_EXIT_CODE = re.compile(r'Exit code:\s+(\d+)')
# exited on signal 11 (Segmentation fault)
RE_EXITED_SIGNAL = re.compile(r'exited on signal\s+(\d+)\s+\((.+?)\)')
# MPI_ERR_TRUNCATE: message truncated
RE_MPI_ERR = re.compile(r'MPI_ERR_\w+:\s+.+')
# An error occurred in MPI_Allreduce
RE_MPI_FUNC = re.compile(r'An error occurred in (MPI_\w+)')
# MPI_ABORT was invoked
RE_MPI_ABORT = re.compile(r'MPI_ABORT was invoked')


def parse_slurm_err(filepath: Path) -> SlurmJobInfo:
    """Parse a single slurm .err file and extract error information."""
    info = SlurmJobInfo()
    info.err_file = filepath.name

    # Extract job ID from filename: slurm_21130.err → 21130
    m = re.search(r'slurm_(\d+)\.err', filepath.name)
    if m:
        info.job_id = m.group(1)

    try:
        text = filepath.read_text(errors='replace')
    except OSError:
        return info

    lines = text.splitlines()
    in_stack = False

    for line in lines:
        stripped = line.strip()

        # Node name
        if not info.node_name:
            m = RE_NODE.search(stripped)
            if m and not m.group(1).startswith('MPI'):
                info.node_name = m.group(1)

        # Segmentation fault signal
        m = RE_SIGNAL.search(stripped)
        if m:
            signal_name = m.group(1)
            info.signal = int(m.group(2))
            if 'Segmentation fault' in signal_name:
                info.has_segfault = True
            if signal_name not in info.error_messages:
                info.error_messages.append(signal_name)
            continue

        # Failing address
        m = RE_FAIL_ADDR.search(stripped)
        if m:
            info.error_messages.append(f"Failing at address: {m.group(1)}")
            continue

        # Exit code
        m = RE_EXIT_CODE.search(stripped)
        if m:
            info.exit_code = int(m.group(1))
            continue

        # exited on signal N
        m = RE_EXITED_SIGNAL.search(stripped)
        if m:
            sig = int(m.group(1))
            sig_name = m.group(2)
            if info.signal < 0:
                info.signal = sig
            if 'Segmentation fault' in sig_name:
                info.has_segfault = True
            continue

        # MPI errors
        m = RE_MPI_ERR.search(stripped)
        if m:
            info.has_mpi_error = True
            msg = m.group(0)
            if msg not in info.error_messages:
                info.error_messages.append(msg)
            continue

        m = RE_MPI_FUNC.search(stripped)
        if m:
            info.has_mpi_error = True
            msg = f"Error in {m.group(1)}"
            if msg not in info.error_messages:
                info.error_messages.append(msg)
            continue

        # MPI_ABORT
        if RE_MPI_ABORT.search(stripped):
            info.has_mpi_abort = True
            if "MPI_ABORT invoked" not in info.error_messages:
                info.error_messages.append("MPI_ABORT invoked")
            continue

        # Stack trace frames (collect up to 10)
        if RE_STACK_FRAME.match(stripped) and len(info.stack_trace) < 10:
            info.stack_trace.append(stripped)
            continue

    return info


def find_and_parse_slurm(result_dir: Path) -> SlurmJobInfo | None:
    """Find the most relevant slurm .err file in the result directory and parse it.

    If multiple slurm files exist, pick the one with the most errors.
    If none have errors, return None.
    """
    err_files = sorted(result_dir.glob("slurm_*.err"))
    if not err_files:
        return None

    results: list[SlurmJobInfo] = []
    for f in err_files:
        info = parse_slurm_err(f)
        results.append(info)

    # Pick the one with the most error information
    def _score(info: SlurmJobInfo) -> int:
        s = 0
        if info.has_segfault:
            s += 100
        if info.has_mpi_error:
            s += 80
        if info.has_mpi_abort:
            s += 60
        if info.exit_code > 0:
            s += 40
        if info.signal > 0:
            s += 20
        s += len(info.error_messages)
        return s

    results.sort(key=_score, reverse=True)

    # Return the most informative result, or None if all are clean
    best = results[0]
    if _score(best) == 0:
        return None  # All slurm files are clean

    return best
