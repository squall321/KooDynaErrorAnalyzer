"""Analysis of specific parts/elements causing simulation failure."""

import re
from pathlib import Path
from koodyna.models import Finding, Severity, TimestepEntry
from koodyna.parsers.element_mapper import find_and_parse_input_deck


def analyze_failure_source(
    messag_path: Path | None,
    d3hsp_path: Path | None,
    smallest_timesteps: list[TimestepEntry],
    result_dir: Path | None = None,
) -> list[Finding]:
    """
    Identify specific parts/elements responsible for failure.

    Analyzes:
    1. Error messages in messag file (negative volume elements)
    2. Timestep controlling parts (elements with smallest dt)
    3. Cross-reference to identify problem parts
    4. Parse k/dyn file to map elements to parts
    """
    findings: list[Finding] = []

    # Parse input deck to get element→part mapping
    elem_to_part = {}
    if result_dir:
        elem_to_part = find_and_parse_input_deck(result_dir)

    # Extract failed elements from messag file
    failed_elements = _parse_failed_elements(messag_path)

    if failed_elements:
        # Group by error type
        by_error = {}
        for elem_info in failed_elements:
            error_type = elem_info['error_type']
            if error_type not in by_error:
                by_error[error_type] = []
            by_error[error_type].append(elem_info)

        for error_type, elems in by_error.items():
            elem_numbers = [e['element'] for e in elems]
            cycles = [e['cycle'] for e in elems if 'cycle' in e]

            if error_type == 'negative_volume':
                # Map elements to parts if possible
                part_ids = set()
                elem_part_map = []
                for elem_num in elem_numbers[:5]:  # Show up to 5 elements
                    if elem_num in elem_to_part:
                        part_id = elem_to_part[elem_num]
                        part_ids.add(part_id)
                        elem_part_map.append(f"{elem_num} (Part {part_id})")
                    else:
                        elem_part_map.append(str(elem_num))

                if elem_part_map:
                    elem_desc = ', '.join(elem_part_map)
                else:
                    elem_desc = ', '.join(map(str, elem_numbers[:5]))

                if len(elem_numbers) > 5:
                    elem_desc += '...'

                part_info = ""
                if part_ids:
                    part_list = ', '.join(map(str, sorted(part_ids)))
                    part_info = f" 영향받은 파트: {part_list}."

                findings.append(Finding(
                    severity=Severity.CRITICAL,
                    category="failure_source",
                    title=f"Negative volume in {len(elems)} element(s)",
                    description=(
                        f"요소 {elem_desc} "
                        f"에서 negative volume 발생. "
                        + (f"사이클 {cycles[0]}에서 처음 감지." if cycles else "")
                        + part_info
                    ),
                    recommendation=(
                        f"{'파트 ' + part_list + '의' if part_ids else '해당 요소가 속한 파트의'} "
                        f"메시 품질을 확인하세요. "
                        "*MAT_ADD_EROSION을 추가하여 극단적으로 변형된 요소를 제거하세요."
                    ),
                ))
            elif error_type == 'constraint_nan':
                findings.append(Finding(
                    severity=Severity.CRITICAL,
                    category="failure_source",
                    title="Constraint matrix NaN detected",
                    description=(
                        "제약조건 행렬에 NaN 발생. 'shooting nodes' (비정상 이동 노드) 의심."
                    ),
                    recommendation=(
                        "제약조건 정의(*CONSTRAINED_*)를 점검하고, "
                        "노드 속도/변위를 확인하세요."
                    ),
                ))

    # Analyze timestep controlling parts
    if smallest_timesteps:
        part_counts = {}
        for ts in smallest_timesteps:
            part_counts[ts.part_number] = part_counts.get(ts.part_number, 0) + 1

        # If one part dominates (>80%), it's likely the bottleneck
        total = sum(part_counts.values())
        for part_id, count in part_counts.items():
            ratio = count / total if total > 0 else 0
            if ratio > 0.8:
                min_dt = min((ts.timestep for ts in smallest_timesteps
                             if ts.part_number == part_id), default=0)
                findings.append(Finding(
                    severity=Severity.WARNING,
                    category="performance_bottleneck",
                    title=f"Part {part_id}: timestep bottleneck ({ratio:.0%})",
                    description=(
                        f"파트 {part_id}가 100개의 최소 timestep 중 {count}개를 차지합니다 "
                        f"({ratio:.0%}). 최소 dt = {min_dt:.3E}. "
                        "이 파트의 메시가 시뮬레이션 속도를 제한하고 있습니다."
                    ),
                    recommendation=(
                        f"파트 {part_id}의 메시를 조정하세요:\n"
                        "1. 매우 작은 요소를 제거하거나 coarsen\n"
                        "2. Mass scaling (DT2MS) 적용 고려\n"
                        "3. 요소 품질(aspect ratio, warpage) 확인"
                    ),
                ))

    return findings


def _parse_failed_elements(messag_path: Path | None) -> list[dict]:
    """Parse messag file to extract failed element information."""
    if not messag_path or not messag_path.exists():
        return []

    failed_elements = []

    try:
        with open(messag_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                lower = line.lower()

                # Negative volume: element # 35994 cycle 407415 time 1.6232E-04
                if 'negative volume' in lower:
                    match = re.search(r'element\s*#?\s*(\d+)', line, re.IGNORECASE)
                    if match:
                        elem_num = int(match.group(1))
                        cycle_match = re.search(r'cycle\s+(\d+)', line)
                        cycle = int(cycle_match.group(1)) if cycle_match else None

                        failed_elements.append({
                            'element': elem_num,
                            'error_type': 'negative_volume',
                            'cycle': cycle,
                            'line': line.strip(),
                        })

                # Constraint matrix NaN
                elif 'constraint matrix' in lower and 'nan' in lower:
                    failed_elements.append({
                        'error_type': 'constraint_nan',
                        'line': line.strip(),
                    })

    except Exception:
        pass

    return failed_elements
