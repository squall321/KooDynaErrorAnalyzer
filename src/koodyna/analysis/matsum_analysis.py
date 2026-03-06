"""Material-level hourglass energy analysis from matsum file."""

from koodyna.models import Finding, Severity, MaterialHGEntry
from koodyna.parsers.matsum import MaterialTimeSeries


def analyze_matsum(
    materials: dict[int, MaterialTimeSeries],
) -> tuple[list[MaterialHGEntry], list[Finding]]:
    """Analyze per-material energy to detect hourglass-dominated materials.

    Returns:
        hg_entries: sorted by max_hg_ratio descending
        findings: CRITICAL if any material > 20%, WARNING if any 10-20%
    """
    hg_entries: list[MaterialHGEntry] = []
    findings: list[Finding] = []

    for mat_id, ts in sorted(materials.items()):
        if not ts.snapshots:
            continue

        final = ts.snapshots[-1]
        max_hg_ratio = 0.0
        max_hg_energy = 0.0

        for snap in ts.snapshots:
            if snap.internal_energy > 1e-15:
                ratio = snap.hourglass_energy / snap.internal_energy
                if ratio > max_hg_ratio:
                    max_hg_ratio = ratio
                    max_hg_energy = snap.hourglass_energy

        entry = MaterialHGEntry(
            mat_id=mat_id,
            name=ts.material_name or f"Mat {mat_id}",
            max_hg_ratio=max_hg_ratio,
            max_hg_energy=max_hg_energy,
            final_ie=final.internal_energy,
            final_hg=final.hourglass_energy,
        )
        hg_entries.append(entry)

    hg_entries.sort(key=lambda x: x.max_hg_ratio, reverse=True)

    critical_mats = [e for e in hg_entries if e.max_hg_ratio > 0.20]
    warning_mats = [e for e in hg_entries if 0.10 < e.max_hg_ratio <= 0.20]

    if critical_mats:
        mat_desc = "; ".join([
            f"Mat{e.mat_id}({e.name}): {e.max_hg_ratio:.1%}"
            for e in critical_mats[:5]
        ])
        if len(critical_mats) > 5:
            mat_desc += f" +{len(critical_mats)-5}개"
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="material",
            title=f"재료별 Hourglass 에너지 과다 ({len(critical_mats)}개 재료 > 20%)",
            description=(
                f"{mat_desc}. 해당 재료의 요소들에서 Hourglass 에너지가 내부에너지의 20%를 초과합니다. "
                f"Reduced integration 요소(single-point)는 강성행렬 rank가 부족하여 "
                f"zero-energy deformation mode(hourglass mode)가 존재합니다. "
                f"특정 재료/파트에 hourglass가 집중된다면 해당 영역의 요소 형상(종횡비, "
                f"왜곡)이나 하중 방향이 hourglass mode와 일치한다는 뜻입니다. "
                f"글로벌 HG/IE 비율이 낮아도 개별 재료에 집중된 hourglass는 "
                f"해당 파트의 응력 결과를 왜곡시킵니다."
            ),
            recommendation=(
                f"1. 해당 재료 파트의 요소 공식 변경 — ELFORM=16(shell 4-point full integration) "
                f"또는 ELFORM=2(solid selective reduced). Hourglass mode 원천 제거\n"
                f"2. Hourglass control 강화 — *HOURGLASS에서 IHQ=4(stiffness-based Flanagan), "
                f"QH=0.05~0.10으로 설정. 해당 파트에만 별도 *SECTION으로 적용 가능\n"
                f"3. 메시 개선 — 해당 재료의 요소 종횡비(aspect ratio)를 5 미만으로 유지. "
                f"왜곡된 요소는 hourglass mode에 더 취약"
            ),
        ))

    if warning_mats:
        mat_desc = "; ".join([
            f"Mat{e.mat_id}({e.name}): {e.max_hg_ratio:.1%}"
            for e in warning_mats[:5]
        ])
        if len(warning_mats) > 5:
            mat_desc += f" +{len(warning_mats)-5}개"
        findings.append(Finding(
            severity=Severity.WARNING,
            category="material",
            title=f"재료별 Hourglass 에너지 주의 ({len(warning_mats)}개 재료 10~20%)",
            description=(
                f"{mat_desc}. 해당 재료의 Hourglass 에너지 비율이 10~20% 범위입니다. "
                f"당장 결과를 무효화할 수준은 아니지만 시뮬레이션 진행에 따라 증가할 수 있습니다."
            ),
            recommendation=(
                f"Hourglass control 보강 (IHQ=4, QH 증가) 또는 해당 재료 파트의 메시 품질 점검"
            ),
        ))

    return hg_entries, findings
