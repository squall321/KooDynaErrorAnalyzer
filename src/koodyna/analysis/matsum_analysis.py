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

    # --- 파트별 에너지 이상 감지 ---

    # 1) 음수 내부 에너지 감지
    for mat_id, ts in sorted(materials.items()):
        if not ts.snapshots:
            continue
        for snap in ts.snapshots:
            if snap.internal_energy < -1e-10:
                name = ts.material_name or f"Mat {mat_id}"
                findings.append(Finding(
                    severity=Severity.CRITICAL,
                    category="material",
                    title=f"재료 {mat_id} ({name}): 음수 내부 에너지 (IE={snap.internal_energy:.3E})",
                    description=(
                        f"재료 {mat_id} ({name})에서 내부 에너지가 {snap.internal_energy:.3E}로 "
                        f"음수입니다 (time={snap.time:.4E}). "
                        f"내부 에너지(IE)는 요소의 변형 에너지 합으로, 물리적으로 항상 ≥ 0이어야 합니다. "
                        f"음수 IE는 재료 모델의 응력-변형률 관계가 비물리적이거나, "
                        f"과도한 인위적 에너지 추출(접촉 penalty, 제약조건)이 원인입니다."
                    ),
                    recommendation=(
                        "1. 해당 재료의 *MAT 파라미터 검토 — softening 곡선이 과도한지 확인\n"
                        "2. 접촉/제약 설정 확인 — 해당 파트의 접촉에서 과도한 penalty 에너지 추출\n"
                        "3. *MAT_ADD_EROSION으로 과도 변형 요소 삭제 검토"
                    ),
                ))
                break  # 재료당 한 번만

    # 2) 에너지 집중 파트 감지 (한 파트가 전체 IE의 90% 이상)
    total_final_ie = 0.0
    part_ie: dict[int, float] = {}
    for mat_id, ts in materials.items():
        if ts.snapshots:
            ie = ts.snapshots[-1].internal_energy
            part_ie[mat_id] = ie
            if ie > 0:
                total_final_ie += ie

    if total_final_ie > 1e-10 and len(part_ie) >= 3:
        for mat_id, ie in sorted(part_ie.items(), key=lambda x: -x[1]):
            ratio = ie / total_final_ie
            if ratio > 0.90:
                name = materials[mat_id].material_name or f"Mat {mat_id}"
                findings.append(Finding(
                    severity=Severity.INFO,
                    category="material",
                    title=f"재료 {mat_id} ({name})에 에너지 집중 ({ratio:.0%})",
                    description=(
                        f"재료 {mat_id} ({name})가 전체 내부 에너지의 {ratio:.0%}를 "
                        f"차지합니다 (IE={ie:.3E} / 전체={total_final_ie:.3E}). "
                        f"에너지가 한 파트에 집중되면 해당 파트에서 과도한 변형이 발생하고 있거나, "
                        f"다른 파트가 거의 변형되지 않는(강체에 가까운) 상태일 수 있습니다."
                    ),
                    recommendation=(
                        "1. 해당 파트의 변형 상태를 d3plot에서 확인\n"
                        "2. 다른 파트가 rigid로 설정되어 있다면 정상적인 현상\n"
                        "3. 비정상적 집중이면 하중 경로와 경계조건 검토"
                    ),
                ))
            break  # 최대 1개만

    # 3) KE 급증 파트 감지 (특정 파트의 KE가 갑자기 폭증)
    for mat_id, ts in sorted(materials.items()):
        if len(ts.snapshots) < 3:
            continue
        name = ts.material_name or f"Mat {mat_id}"
        for i in range(2, len(ts.snapshots)):
            prev_ke = ts.snapshots[i-1].kinetic_energy
            curr_ke = ts.snapshots[i].kinetic_energy
            if prev_ke > 1e-10 and curr_ke > prev_ke * 100:
                findings.append(Finding(
                    severity=Severity.WARNING,
                    category="material",
                    title=f"재료 {mat_id} ({name}): KE 급증 ({curr_ke/prev_ke:.0f}배)",
                    description=(
                        f"재료 {mat_id} ({name})의 운동 에너지가 "
                        f"time={ts.snapshots[i].time:.4E}에서 {curr_ke/prev_ke:.0f}배 급증 "
                        f"(KE: {prev_ke:.3E} → {curr_ke:.3E}). "
                        f"특정 파트에서 노드가 비정상적으로 가속되었습니다 (shooting node 가능성)."
                    ),
                    recommendation=(
                        "1. 해당 시점의 d3plot에서 비정상 고속 노드 확인\n"
                        "2. 접촉 설정 검토 — 관통에 의한 과도한 반력\n"
                        "3. *CONTROL_CONTACT의 RWPNAL(접촉력 제한) 설정 검토"
                    ),
                ))
                break  # 재료당 한 번만

    return hg_entries, findings
