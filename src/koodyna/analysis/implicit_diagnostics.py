"""Implicit solver specific diagnostics."""

from koodyna.models import Finding, Severity, EnergySnapshot

_IMPLICIT_KEYWORDS = {
    "CONTROL_IMPLICIT_GENERAL",
    "CONTROL_IMPLICIT_AUTO",
    "CONTROL_IMPLICIT_SOLUTION",
    "CONTROL_IMPLICIT_SOLVER",
    "CONTROL_IMPLICIT_BUCKLE",
    "CONTROL_IMPLICIT_DYNAMICS",
    "CONTROL_IMPLICIT_EIGENVALUE",
    "CONTROL_IMPLICIT_FORMING",
    "CONTROL_IMPLICIT_MODAL_DYNAMIC",
    "CONTROL_IMPLICIT_INERTIA_RELIEF",
    "CONTROL_IMPLICIT_STATIC_CONDENSATION",
    "CONTROL_IMPLICIT_JOINTS",
    "CONTROL_IMPLICIT_ROTATIONAL_INERTIA",
    "CONTROL_IMPLICIT_SPC",
}

_IMPLICIT_ERROR_DIAGNOSTICS: dict[int, dict] = {
    60004: {
        "severity": Severity.CRITICAL,
        "title": "Implicit solver: 강성 행렬 특이 (Error 60004)",
        "description": (
            "강성 행렬 K가 수치적으로 특이(singular)합니다. "
            "암묵적 적분에서는 매 스텝 KΔu = ΔF를 풀어야 하는데, K의 행렬식이 "
            "0에 가까우면 역행렬이 존재하지 않아 해를 구할 수 없습니다. "
            "주요 원인: (1) 구속이 불충분한 메커니즘(rigid body motion 허용), "
            "(2) 압축 좌굴에 의한 강성 소실, (3) 재료 softening으로 "
            "접선 강성이 음수로 전환됨."
        ),
        "recommendation": (
            "1. 구속 조건 확인 — *BOUNDARY_SPC에서 모든 강체 모드(6 DOF)가 "
            "구속되었는지 확인. *CONSTRAINED_GLOBAL 또는 *RIGID_BODY 사용 검토\n"
            "2. 좌굴 해석 — *CONTROL_IMPLICIT_BUCKLE로 임계 하중 인수 확인. "
            "좌굴 하중 미만에서 해석 수행\n"
            "3. 재료 softening 제거 — damage/erosion 모델에서 연화 구간 점검. "
            "*MAT_ADD_EROSION으로 요소 삭제 기준 설정"
        ),
    },
    60121: {
        "severity": Severity.WARNING,
        "title": "Implicit solver: 수렴 속도 저하 (Warning 60121)",
        "description": (
            "Newton-Raphson 반복이 지정된 허용 오차 내로 수렴하는 데 "
            "예상보다 많은 반복이 필요합니다. 잔차 r = F_ext - F_int의 크기가 "
            "허용 오차 tol × ||F||보다 작아야 수렴으로 판정됩니다. "
            "수렴이 느리면 계산 시간이 증가하고 극단적인 경우 비수렴으로 이어집니다."
        ),
        "recommendation": (
            "1. 하중 스텝 세분화 — *CONTROL_IMPLICIT_GENERAL의 DT0를 줄여 "
            "하중 증분을 작게. 비선형 문제에서 큰 증분은 수렴 실패의 주원인\n"
            "2. 수렴 기준 조정 — NLNORM=2(force residual) 대신 "
            "NLNORM=1(energy norm)이 강한 비선형에서 더 안정적\n"
            "3. 선형 솔버 변경 — LSOLVR=2(PARDISO) 직접법 솔버로 수치적으로 "
            "어려운 시스템에서 반복법보다 안정적"
        ),
    },
    60303: {
        "severity": Severity.CRITICAL,
        "title": "Implicit solver: line search 실패 (Error 60303)",
        "description": (
            "Line search 알고리즘이 에너지를 감소시키는 스텝 크기를 찾지 못했습니다. "
            "Newton-Raphson에서 ΔU = -K⁻¹R이 방향은 맞지만 크기가 너무 크면 "
            "line search로 최적 step length α를 탐색합니다. "
            "Line search 실패는 현재 증분이 수렴 반경(radius of convergence) 밖에 "
            "있음을 의미하며, 주로 급격한 비선형성(contact 상태 변화, 재료 항복) 발생 시 나타납니다."
        ),
        "recommendation": (
            "1. 시간 증분 축소 — *CONTROL_IMPLICIT_AUTO에서 DTMIN을 줄이고 "
            "ITEOPT(최적 반복 수)를 줄여 자동 스텝 크기를 보수적으로 설정\n"
            "2. 재료 모델 점검 — sudden strain softening이 있는 재료는 "
            "line search를 실패시킵니다. regularization length 또는 erosion 기준 점검\n"
            "3. Arc-length method 사용 — *CONTROL_IMPLICIT_GENERAL에서 "
            "NSOLVR=6(Riks method)으로 변경. 하중 제어 대신 변위-하중 동시 제어"
        ),
    },
    60315: {
        "severity": Severity.CRITICAL,
        "title": "Implicit solver: Newton-Raphson 발산 (Error 60315)",
        "description": (
            "Newton-Raphson 반복이 발산하여 시뮬레이션이 종료되었습니다. "
            "비선형 방정식 R(u) = 0을 Newton 반복으로 풀 때, "
            "잔차가 반복할수록 증가하면 발산으로 판단합니다. "
            "구조적 불안정(좌굴, 파괴), 재료 강성의 급격한 변화, "
            "또는 접촉 상태 변화(열림/닫힘)가 주요 원인입니다."
        ),
        "recommendation": (
            "1. 하중 증분 대폭 축소 — 발산 직전의 하중/시간에서 DT를 1/10으로 줄임. "
            "IMFLAG=5(자동 시간 증분 with cutback)로 수렴 실패 시 자동 재시작\n"
            "2. Adaptive stiffness — *CONTROL_IMPLICIT_GENERAL의 IMAT=1로 "
            "재료 접선 강성을 매 반복 업데이트. 초기 비용은 크지만 수렴 안정\n"
            "3. 명시적 해석 전환 — *CONTROL_IMPLICIT_AUTO의 CRIT로 명시적-암묵적 "
            "자동 전환 활성화. 불안정 구간에서 explicit으로 전환 후 복귀"
        ),
    },
}


def is_implicit_simulation(keyword_counts: dict[str, int]) -> bool:
    """Check if this simulation uses implicit time integration."""
    for kw in _IMPLICIT_KEYWORDS:
        # keyword_counts keys may be with or without leading *
        if keyword_counts.get(kw, 0) > 0 or keyword_counts.get(f"*{kw}", 0) > 0:
            return True
    return False


def analyze_implicit_solver(
    keyword_counts: dict[str, int],
    error_counts: dict[int, int],
    error_messages: dict[int, str],
    energy_snapshots: list[EnergySnapshot],
) -> list[Finding]:
    """Detect implicit solver convergence and stability issues."""
    findings: list[Finding] = []

    if not is_implicit_simulation(keyword_counts):
        return findings

    # Report errors in priority order: CRITICAL first
    for code in [60315, 60303, 60004, 60121]:
        count = error_counts.get(code, 0)
        if count == 0:
            continue
        diag = _IMPLICIT_ERROR_DIAGNOSTICS.get(code)
        if not diag:
            continue
        findings.append(Finding(
            severity=diag["severity"],
            category="implicit_solver",
            title=diag["title"],
            description=diag["description"] + f" (발생 {count}회)",
            recommendation=diag["recommendation"],
        ))

    # Check energy ratio for implicit runs
    if energy_snapshots and len(energy_snapshots) > 5:
        final = energy_snapshots[-1]
        if final.energy_ratio > 2.0:
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="implicit_solver",
                title=f"Implicit 에너지 수지 불균형 (비율: {final.energy_ratio:.3f})",
                description=(
                    f"암묵적 해석에서 에너지 비율이 {final.energy_ratio:.3f}로 1.0에서 크게 벗어났습니다. "
                    f"암묵적 적분(Newmark-β, HHT-α)은 무조건 안정(unconditionally stable)이지만, "
                    f"비선형 문제에서 Newton 반복이 부정확하거나 하중 증분이 너무 크면 "
                    f"에너지 수지가 맞지 않습니다. 접촉 조건 변화나 강한 재료 비선형이 원인일 수 있습니다."
                ),
                recommendation=(
                    "1. 수렴 기준 강화 — *CONTROL_IMPLICIT_GENERAL의 DNORM 허용 오차를 "
                    "더 작은 값으로 설정하여 각 스텝의 해 정확도 향상\n"
                    "2. 하중 증분 감소 — 비선형이 강한 구간에서 DT를 줄여 "
                    "Newton 반복이 선형 범위에서 동작하도록 유지\n"
                    "3. LENRGT=1(에너지 norm) 수렴 기준 적용 — 에너지 보존에 민감한 판단 기준"
                ),
            ))

    # INFO finding when implicit is used without errors
    has_critical = any(f.severity == Severity.CRITICAL for f in findings)
    has_warning = any(f.severity == Severity.WARNING for f in findings)
    if not has_critical and not has_warning:
        findings.append(Finding(
            severity=Severity.INFO,
            category="implicit_solver",
            title="Implicit 시간 적분 감지 (수렴 오류 없음)",
            description=(
                "이 해석은 암묵적(Implicit) 시간 적분을 사용합니다. "
                "수렴 오류 없이 정상 완료되었습니다. "
                "암묵적 해석은 명시적 해석보다 스텝당 비용이 크지만(선형 시스템 풀이), "
                "타임스텝 제한이 없어 준정적(quasi-static) 및 저주파 동적 해석에 적합합니다."
            ),
            recommendation="",
        ))

    return findings
