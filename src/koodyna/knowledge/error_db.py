"""LS-DYNA error and warning code database with recommendations."""

from dataclasses import dataclass
from koodyna.models import Severity


@dataclass
class ErrorInfo:
    code: int
    severity: Severity
    title: str
    description: str
    recommendation: str


ERROR_DATABASE: dict[int, ErrorInfo] = {
    # ===== Contact / Interface Warnings (50xxx) =====
    50135: ErrorInfo(
        code=50135,
        severity=Severity.WARNING,
        title="Tracked node not constrained (tied interface)",
        description=(
            "Tied contact 인터페이스에서 slave 노드를 master segment에 투영(projection)"
            "하지 못했습니다. Tied contact는 slave 노드의 변위를 가장 가까운 master "
            "segment의 보간 변위에 구속하는 방식(Multi-Point Constraint)으로 작동합니다. "
            "투영 실패한 노드는 구속되지 않아 인터페이스에서 분리될 수 있습니다. "
            "주요 원인: (1) 메시 불일치로 slave 노드가 master segment의 법선 방향 "
            "투영 범위 밖에 위치, (2) 검색 거리(search distance) 초과, "
            "(3) master surface의 세그먼트 법선이 slave 반대 방향."
        ),
        recommendation=(
            "1. 메시 호환성 확인 — slave/master 면의 요소 크기를 비슷하게 맞추고, "
            "특히 모서리/꼭짓점에서 노드가 master 면을 벗어나지 않도록 확인\n"
            "2. SBOPT=3(투영 방향 최적화) + DEPTH=5(검색 깊이 증가) 설정 — "
            "*CONTACT 카드에서 투영 알고리즘을 강화하여 검색 범위를 확장\n"
            "3. SFACT 값 증가 — 검색 거리 스케일 팩터를 늘려 멀리 있는 노드도 투영 가능\n"
            "4. 인터페이스 근처 메시 세분화 — master 면의 메시를 세분화하면 "
            "투영 대상 세그먼트가 증가하여 투영 성공률 향상"
        ),
    ),
    50136: ErrorInfo(
        code=50136,
        severity=Severity.WARNING,
        title="Tracked node too far from segment",
        description=(
            "Tied contact의 slave 노드가 가장 가까운 master segment까지의 거리가 "
            "검색 허용치(search tolerance)를 초과합니다. Tied contact에서 노드-세그먼트 "
            "거리 d는 법선 방향 투영으로 계산되는데, d > SFACT × (segment_area)^0.5이면 "
            "해당 노드는 구속에서 제외됩니다. 이는 두 파트 사이에 기하학적 간격(gap)이 "
            "있거나, 메시 정렬이 불량하거나, 검색 허용치가 너무 작을 때 발생합니다."
        ),
        recommendation=(
            "1. SFACT(검색 거리 계수) 증가 — *CONTACT의 SFACT를 2.0~5.0으로 설정하여 "
            "검색 범위 확장. 기본값은 작아서 약간의 간격에도 실패할 수 있음\n"
            "2. 기하학적 간격 확인 — 후처리기에서 tied interface 사이의 간격을 시각화하고, "
            "간격이 존재하면 메시를 조정하여 면이 밀착되도록 수정\n"
            "3. 메시 정렬 개선 — slave/master 면이 평행하고 가까이 위치하도록 "
            "메시 모핑 또는 이동. 비평면(non-planar) 인터페이스에서는 법선 방향 "
            "투영이 실패하기 쉬우므로 곡률을 줄이는 것이 도움"
        ),
    ),
    50120: ErrorInfo(
        code=50120,
        severity=Severity.WARNING,
        title="Contact segment normals inconsistent",
        description=(
            "접촉 세그먼트의 법선(normal) 방향이 일관되지 않거나 뒤집혀 있습니다. "
            "LS-DYNA의 접촉 알고리즘은 세그먼트 법선을 기준으로 관통 방향을 판별하는데, "
            "법선이 뒤집혀 있으면 접촉 검출이 실패하거나, 관통 방향을 반대로 "
            "판단하여 노드를 잘못된 방향으로 밀어냅니다. "
            "Shell 요소에서 법선은 노드 연결 순서(connectivity)의 오른손 법칙으로 "
            "결정되며, 인접 요소 간 법선이 반대이면 inconsistent합니다."
        ),
        recommendation=(
            "1. 세그먼트 법선 방향 확인 — 후처리기에서 법선 벡터를 시각화하여 "
            "모든 접촉면의 법선이 상대 면을 향하도록 확인\n"
            "2. *CONTACT_..._ID에서 SSTYP/MSTYP 설정 — 세그먼트 세트 정의 시 "
            "법선 방향을 명시적으로 지정\n"
            "3. *CONTACT_AUTOMATIC_...류 사용 고려 — AUTOMATIC 접촉은 법선 방향을 "
            "자동으로 판별하여 inconsistency 문제를 우회할 수 있음\n"
            "4. 세그먼트 연결순서(connectivity) 수정 — 쉘 요소의 노드 순서를 "
            "수정하여 법선이 일관되도록 변경"
        ),
    ),

    # ===== Contact Penetration Warnings (20xxx) =====
    20248: ErrorInfo(
        code=20248,
        severity=Severity.WARNING,
        title="Initial penetration in contact",
        description=(
            "노드가 접촉면을 초기에 관통(penetrate)하고 있습니다. "
            "Penalty contact에서 관통 깊이 g > 0이면 F = k × g의 접촉력이 발생하는데, "
            "시뮬레이션 시작 시점부터 관통이 있으면 0번 스텝에서 갑자기 큰 접촉력이 "
            "작용합니다. 이 순간적인 에너지 주입(artificial energy injection)은 "
            "초기 운동 에너지를 증가시키고, 접촉면 근처 요소를 왜곡시킬 수 있습니다. "
            "특히 얇은 쉘 요소에서 초기 관통은 첫 스텝에서 요소를 뒤집어 "
            "negative volume을 유발할 수 있습니다."
        ),
        recommendation=(
            "1. *CONTROL_CONTACT의 PENOPT 설정 — PENOPT=1(기본): 관통 유지, "
            "PENOPT=4: 초기 관통을 자동 해소하여 에너지 주입 방지. "
            "PENOPT=4가 권장됨\n"
            "2. IGNORE 옵션 — IGNORE=1: 관통을 기록만 하고 무시(경고 출력), "
            "IGNORE=2: 관통을 시간에 걸쳐 점진적으로 해소\n"
            "3. 메시 정렬 개선 — 접촉면의 메시를 조정하여 기하학적으로 "
            "관통이 없도록 수정. 후처리기에서 초기 관통을 시각화하여 위치 확인\n"
            "4. 쉘 두께 확인 — 쉘 두께가 요소 크기에 비해 크면 "
            "인접 파트와 두께 간섭이 발생합니다"
        ),
    ),
    20200: ErrorInfo(
        code=20200,
        severity=Severity.WARNING,
        title="Contact interface has no segments",
        description=(
            "접촉 인터페이스에 세그먼트가 정의되어 있지 않습니다. "
            "*CONTACT 카드에서 참조하는 slave 또는 master 세트(part set, segment set)에 "
            "해당하는 요소가 없어 접촉면이 비어 있습니다. "
            "이 접촉 정의는 실질적으로 비활성 상태이며, 해당 파트 간 "
            "접촉 검출이 이루어지지 않습니다."
        ),
        recommendation=(
            "1. 접촉 정의에서 참조하는 Part/Set ID 확인 — *SET_PART 또는 "
            "*SET_SEGMENT의 ID가 *CONTACT에서 사용하는 SSID/MSID와 일치하는지 확인\n"
            "2. 세트 정의 누락 확인 — *SET_PART_LIST에 해당 파트 ID가 포함되어 있는지, "
            "또는 *SET_SEGMENT가 올바르게 정의되어 있는지 확인\n"
            "3. SSTYP/MSTYP 설정 — slave/master 타입 설정이 올바른지 확인 "
            "(0=segment set, 2=part set, 3=part ID)"
        ),
    ),

    # ===== Negative Volume Errors (30xxx/40xxx) =====
    30010: ErrorInfo(
        code=30010,
        severity=Severity.CRITICAL,
        title="Negative volume (error termination)",
        description=(
            "요소에 negative volume이 발생하여 시뮬레이션이 에러로 종료되었습니다. "
            "유한요소법에서 요소의 체적은 Jacobian 행렬식(det(J))으로 계산되며, "
            "J < 0이면 요소의 노드 순서가 뒤집어져 체적이 음수가 됩니다. "
            "이는 요소가 물리적 한계를 넘어 극심하게 왜곡(distorted)되어 "
            "노드들이 서로 교차했다는 의미입니다. "
            "일반적으로 과도한 압축, 전단 변형, 또는 접촉 관통에 의해 발생하며, "
            "한 번 발생하면 계산이 불가능해져 즉시 종료됩니다."
        ),
        recommendation=(
            "1. 요소 침식(erosion) 추가 — *MAT_ADD_EROSION으로 과도하게 왜곡된 "
            "요소를 자동 삭제. MXEPS(최대 유효 소성 변형률: 강재 0.3~0.5)를 설정하면 "
            "negative volume 이전에 요소가 제거됨\n"
            "2. *CONTROL_TIMESTEP의 ERODE=1 + TSMIN 설정 — dt < TSMIN인 "
            "요소를 자동 삭제하여 극도로 왜곡된 요소가 negative volume에 "
            "도달하기 전에 제거\n"
            "3. 메시 품질 개선 — 문제 영역의 요소 크기를 줄이고, 초기 "
            "aspect ratio < 3, warpage < 15도, Jacobian > 0.5 확보\n"
            "4. 경계조건/하중 점검 — 국부적으로 과도한 변형을 유발하는 "
            "하중 조건이나 구속 조건 확인"
        ),
    ),
    40003: ErrorInfo(
        code=40003,
        severity=Severity.CRITICAL,
        title="Negative volume in element",
        description=(
            "계산 중 요소에 negative volume이 발생했습니다. "
            "Solid 요소에서 Jacobian det(J) = ∂(x,y,z)/∂(ξ,η,ζ)이며, "
            "J < 0은 요소의 자연좌표(natural coordinates)와 물리좌표의 매핑이 "
            "뒤집어졌음을 의미합니다. 8노드 hexahedron에서는 내부 Gauss 점에서 "
            "J를 평가하며, 심한 왜곡(특히 요소 한 면이 반대편으로 넘어감)에서 발생합니다. "
            "이 요소는 더 이상 유효한 강성 행렬을 계산할 수 없으므로 "
            "시뮬레이션 불안정 또는 종료의 원인이 됩니다."
        ),
        recommendation=(
            "1. 문제 요소 주변 메시 품질 개선 — 후처리기에서 에러가 발생한 "
            "요소의 위치를 확인하고, 해당 영역의 메시를 세분화하여 "
            "변형이 분산되도록 개선\n"
            "2. 요소 침식(erosion) 설정 — *MAT_ADD_EROSION 또는 "
            "*CONTROL_TIMESTEP의 ERODE=1으로 과도 왜곡 요소 자동 삭제\n"
            "3. Timestep scale factor 감소 — TSSFAC를 줄여 각 스텝에서의 "
            "변형량을 줄이면 요소 왜곡이 점진적으로 진행되어 "
            "침식이 적시에 작동할 수 있음"
        ),
    ),
    40004: ErrorInfo(
        code=40004,
        severity=Severity.CRITICAL,
        title="Negative volume in shell element",
        description=(
            "Shell 요소에서 negative area/volume이 발생했습니다. "
            "Shell 요소는 면적(area)과 두께(thickness)의 곱으로 체적을 계산하며, "
            "면적이 음수가 되면(노드가 교차하여 요소가 뒤집어짐) negative volume이 됩니다. "
            "얇은 쉘에서는 면내(in-plane) 압축이나 전단에 의해 요소가 "
            "접혀서(folding) 발생하기도 합니다. "
            "Shell 두께가 요소 크기에 비해 큰 경우, 두께 방향 적분점에서 "
            "비물리적 변형이 발생할 수도 있습니다."
        ),
        recommendation=(
            "1. Shell 두께 확인 — 두께/요소크기 비율이 0.5 이하인지 확인. "
            "비율이 너무 크면 solid 요소로 모델링 변경 권장\n"
            "2. 요소 침식 추가 — *MAT_ADD_EROSION으로 과도 변형 쉘 삭제. "
            "Shell의 TSMIN을 설정하여 dt가 너무 작아지는 요소 제거\n"
            "3. Shell element formulation 변경 — ELFORM=2(Belytschko-Tsay) → "
            "ELFORM=16(fully-integrated)으로 변경하면 면내 안정성 향상\n"
            "4. 접촉 설정 점검 — 쉘 표면의 접촉 관통이 쉘을 뒤집는 "
            "원인일 수 있으므로, 쉘 두께를 고려한 접촉 설정 확인"
        ),
    ),

    # ===== Negative Volume Warning (40509) =====
    40509: ErrorInfo(
        code=40509,
        severity=Severity.WARNING,
        title="Negative volume warning",
        description=(
            "요소에서 negative volume(Jacobian J < 0) 경고가 발생했습니다. "
            "이 경고는 에러(30010)와 달리 시뮬레이션을 즉시 종료하지 않지만, "
            "해당 요소의 계산이 비물리적임을 나타냅니다. "
            "반복 발생하면 시뮬레이션의 수치적 안정성이 저하되고, "
            "결국 에러로 종료될 가능성이 높습니다. "
            "이 경고의 빈도(총 사이클 대비 경고 횟수)가 "
            "시뮬레이션의 건전성을 판단하는 핵심 지표입니다."
        ),
        recommendation=(
            "1. 경고 빈도 분석 — 총 사이클 대비 40509 경고 비율 확인. "
            "> 50%이면 시스템적 문제, > 10%이면 개선 필요\n"
            "2. 문제 요소에 침식 설정 — *MAT_ADD_EROSION의 MXEPS 또는 "
            "*CONTROL_TIMESTEP의 ERODE=1로 과도 왜곡 요소 제거\n"
            "3. 메시 품질 개선 — 문제 발생 영역의 메시를 세분화하고, "
            "초기 요소 품질(Jacobian, aspect ratio) 개선\n"
            "4. 하중 조건 점검 — 국부 하중이 과도한지 확인"
        ),
    ),

    # ===== NaN Detection Errors (40455/40456) =====
    40455: ErrorInfo(
        code=40455,
        severity=Severity.CRITICAL,
        title="NaN detected on processor",
        description=(
            "프로세서에서 NaN(Not a Number)이 검출되었습니다. "
            "LS-DYNA의 명시적 시간 적분에서 v(t+dt) = v(t) + (F/m)×dt를 계산할 때, "
            "힘 F가 무한대이거나 질량 m이 0이면 NaN이 발생합니다. "
            "NaN은 IEEE 754 부동소수점 연산에서 0/0, ∞-∞, 0×∞ 등의 "
            "결과이며, 한 번 발생하면 모든 후속 계산으로 전파됩니다(NaN + x = NaN). "
            "MPP 환경에서는 특정 프로세서에서 먼저 발생하여 MPI 통신을 통해 "
            "다른 프로세서로 전파됩니다. Error 40455는 프로세서별 NaN 감지로, "
            "Error 40456(전역 NaN 감지)의 전조입니다."
        ),
        recommendation=(
            "1. NaN 발생 프로세서의 도메인 확인 — 해당 프로세서가 담당하는 "
            "요소/노드 영역에서 극심한 변형이나 접촉 불안정 확인\n"
            "2. Timestep scale factor(TSSFAC) 감소 — 0.9 → 0.67로 줄여 "
            "각 스텝의 변형량을 제한. 특히 대변형 해석에서 효과적\n"
            "3. Negative volume 경고(40509) 확인 — NaN의 전조 증상인 "
            "negative volume이 선행했는지 d3hsp/mes 파일에서 확인\n"
            "4. 재료 물성 검증 — 밀도, 탄성계수가 0이 아닌지 확인. "
            "단위 시스템(mm-ton-s vs m-kg-s) 통일 여부 점검\n"
            "5. 요소 침식(*MAT_ADD_EROSION) 추가 — 과도 변형 요소를 "
            "NaN 발생 전에 자동 제거"
        ),
    ),
    40456: ErrorInfo(
        code=40456,
        severity=Severity.CRITICAL,
        title="NaN detected (global)",
        description=(
            "전역적으로 NaN(Not a Number)이 검출되어 시뮬레이션이 종료됩니다. "
            "Error 40456은 Error 40455(프로세서별 NaN)가 전역으로 전파된 후 "
            "최종적으로 감지되는 에러입니다. 이 시점에서는 이미 수치 해가 "
            "완전히 발산했으며, 복구가 불가능합니다. "
            "NaN의 근본 원인은 대부분 (1) negative volume 요소, "
            "(2) 과도한 접촉 관통, (3) 재료 모델의 비물리적 파라미터, "
            "(4) 과도한 mass scaling 중 하나입니다. "
            "glstat에서 NaN이 나타나는 시점 직전의 에너지 변화를 분석하면 "
            "원인을 추적할 수 있습니다."
        ),
        recommendation=(
            "1. glstat 에너지 이력 분석 — NaN 직전 사이클에서 "
            "kinetic energy 급증, energy ratio 발산, 또는 "
            "sliding interface energy 이상 여부 확인\n"
            "2. mes 파일에서 Error 40455 확인 — 어느 프로세서에서 "
            "NaN이 먼저 발생했는지 추적하여 문제 영역 특정\n"
            "3. Negative volume 경고(40509) 추적 — NaN 발생 전에 "
            "negative volume이 축적되었다면 해당 요소에 침식 기준 추가\n"
            "4. 접촉 설정 검토 — 접촉 관통이 에너지 불안정을 유발했다면 "
            "penalty scale factor(SLSFAC) 조정 또는 soft constraint(SOFT=1) 사용\n"
            "5. TSSFAC 감소 + ERODE 활성화 — dt를 줄이고 "
            "과도 왜곡 요소를 자동 제거하여 NaN 전파 방지"
        ),
    ),

    # ===== NaN / Numerical Errors (30xxx) =====
    30200: ErrorInfo(
        code=30200,
        severity=Severity.CRITICAL,
        title="NaN velocity detected",
        description=(
            "NaN(Not a Number) 속도가 검출되어 시뮬레이션이 수치적으로 발산했습니다. "
            "명시적 적분에서 v(t+dt) = v(t) + (F/m)×dt로 계산하는데, "
            "F가 무한대(Inf)이거나, m이 0이거나, 이전 스텝에서 이미 NaN이 "
            "전파되면 NaN이 발생합니다. NaN은 IEEE 754 부동소수점 연산에서 "
            "0/0, ∞-∞, 0×∞ 등의 연산 결과이며, 한 번 발생하면 "
            "모든 후속 계산으로 전파됩니다(NaN + x = NaN). "
            "일반적으로 zero-volume 요소, 과도한 mass scaling, "
            "또는 접촉 불안정에서 시작됩니다."
        ),
        recommendation=(
            "1. Timestep scale factor(TSSFAC) 감소 — dt를 줄여 각 스텝의 "
            "변형량을 제한하면 발산 방지. 0.9 → 0.67 → 0.5 단계적 감소 시도\n"
            "2. Zero-volume 요소 점검 — negative volume 경고(40509)가 "
            "NaN의 전조. 요소 침식(*MAT_ADD_EROSION)으로 문제 요소 제거\n"
            "3. 재료 물성 검증 — 밀도, 탄성계수, 항복응력이 0이 아닌 "
            "물리적으로 합리적인 값인지 확인. 특히 단위 시스템 통일 "
            "(mm-ton-s, m-kg-s 등) 확인\n"
            "4. Mass scaling 확인 — DT2MS가 너무 공격적이면 "
            "인공 질량이 과도하여 불안정 유발. |DT2MS|를 줄이거나 "
            "mass scaling 제거 후 재실행"
        ),
    ),
    30100: ErrorInfo(
        code=30100,
        severity=Severity.CRITICAL,
        title="NaN in stress calculation",
        description=(
            "응력 계산에서 NaN이 검출되었습니다. "
            "구성 방정식(constitutive equation) σ = f(ε)에서 비물리적 변형률이 "
            "입력되거나, 재료 모델의 내부 변수가 비정상적 범위에 도달했을 때 발생합니다. "
            "예: von Mises 항복 조건에서 σ_eq = √(3/2 × s_ij × s_ij)를 계산할 때 "
            "s_ij에 NaN이 전파되면 항복 판정 자체가 불가능해집니다. "
            "손상(damage) 모델에서는 D=1.0 도달 후 응력이 0이 되어야 하지만, "
            "수치적 오차로 D > 1.0이 되면 비물리적 응력이 계산될 수 있습니다."
        ),
        recommendation=(
            "1. 재료 물성 확인 — 밀도(RO), 탄성계수(E), 항복응력(SIGY)이 "
            "0이 아닌 물리적 값인지 확인. 특히 단위 시스템이 일관되는지 "
            "검증 (예: mm 시스템에서 E는 MPa, 밀도는 ton/mm³)\n"
            "2. TSSFAC 감소 — 스트레인 증분이 너무 크면 구성 방정식의 "
            "수렴이 실패할 수 있음. 스텝 크기를 줄여 안정성 확보\n"
            "3. 재료 모델 검토 — 복잡한 재료 모델(GISSMO, Johnson-Cook 등)의 "
            "파라미터가 올바른 범위에 있는지 확인. "
            "변형률 속도 의존성 파라미터가 극단값을 생성하지 않는지 검증"
        ),
    ),

    # ===== Constraint Matrix Error (30358) =====
    30358: ErrorInfo(
        code=30358,
        severity=Severity.CRITICAL,
        title="Constraint matrix error",
        description=(
            "Constraint 행렬 오류가 발생했습니다. "
            "LS-DYNA에서 *CONSTRAINED_* 키워드로 정의된 구속(MPC, rigid body, "
            "joint 등)은 내부적으로 constraint 행렬 [C]를 구성하는데, "
            "이 행렬이 특이(singular)하거나 과잉 구속(over-constrained)이면 "
            "역행렬을 구할 수 없어 오류가 발생합니다. "
            "주요 원인: (1) 같은 노드에 여러 constraint가 중복 적용, "
            "(2) *CONSTRAINED_RIGID_BODIES에서 순환 참조, "
            "(3) 너무 많은 자유도가 구속되어 강체 운동조차 불가."
        ),
        recommendation=(
            "1. 중복 constraint 확인 — 같은 노드가 여러 *CONSTRAINED_* "
            "정의에 포함되어 있지 않은지 확인. 특히 *CONSTRAINED_EXTRA_NODES와 "
            "*CONSTRAINED_RIGID_BODIES의 중복 주의\n"
            "2. 순환 참조 제거 — 강체 A→B, B→A와 같은 순환 연결이 없는지 확인\n"
            "3. Contact과 constraint 충돌 — 같은 노드에 tied contact와 "
            "SPC가 동시 적용되면 과잉 구속. 하나를 제거\n"
            "4. MPP 분해 관련 — MPP에서 constraint가 프로세서 경계를 "
            "넘으면 통신 오류 가능. DECOMP 설정 확인"
        ),
    ),

    # ===== Memory Errors (10xxx) =====
    10103: ErrorInfo(
        code=10103,
        severity=Severity.CRITICAL,
        title="Out of memory",
        description=(
            "LS-DYNA 실행 중 할당된 메모리가 부족합니다. "
            "LS-DYNA는 시작 시 memory/memory2 키워드로 지정된 양의 메모리를 "
            "미리 할당(pre-allocate)하며, 접촉 검색(bucket sort), 요소 계산, "
            "MPP 통신 버퍼 등에 사용합니다. 특히 접촉 세그먼트 수가 많거나, "
            "적응적 재메싱(adaptive remeshing)으로 요소 수가 증가하면 "
            "런타임 중 메모리가 부족해질 수 있습니다."
        ),
        recommendation=(
            "1. 메모리 할당 증가 — 명령줄에서 memory=NWORDS memory2=NWORDS 옵션 추가. "
            "예: memory=500m memory2=500m (500MB). 기본값보다 2~4배로 시작\n"
            "2. 접촉 세그먼트 최적화 — 불필요한 접촉 정의 제거, "
            "*CONTACT_AUTOMATIC_SINGLE_SURFACE 사용 시 파트 수가 많으면 "
            "메모리 사용량 급증. 접촉이 필요한 파트만 포함하도록 설정\n"
            "3. MPP에서 프로세서 수 증가 — 메모리가 프로세서 간 분산되므로 "
            "더 많은 프로세서를 사용하면 각 프로세서의 메모리 부담 감소\n"
            "4. 모델 크기 축소 — 관심 영역 외의 메시를 조대화(coarsen)하여 "
            "전체 요소 수와 노드 수를 줄임"
        ),
    ),
    10100: ErrorInfo(
        code=10100,
        severity=Severity.CRITICAL,
        title="Insufficient memory for decomposition",
        description=(
            "MPP(Massively Parallel Processing) 도메인 분해에 필요한 메모리가 "
            "부족합니다. MPP 모드에서는 메시를 여러 프로세서에 분배하기 위해 "
            "도메인 분해(domain decomposition)를 수행하는데, "
            "이 과정에서 전체 메시의 연결 정보(connectivity graph)를 "
            "메모리에 로드해야 합니다. 대규모 모델(백만 요소 이상)에서는 "
            "분해 과정 자체에 상당한 메모리가 필요합니다."
        ),
        recommendation=(
            "1. 메모리 할당 대폭 증가 — memory=200m memory2=200m 이상으로 설정. "
            "대규모 모델(>1M 요소)에서는 memory=1000m 이상 필요할 수 있음\n"
            "2. 분해 방법 변경 — *CONTROL_MPP_DECOMPOSITION에서 분해 알고리즘 변경. "
            "RCB(Recursive Coordinate Bisection)가 METIS보다 메모리 효율적\n"
            "3. 물리 메모리 확인 — 시스템의 가용 RAM 확인. "
            "LS-DYNA 할당량이 물리 메모리를 초과하면 스왑 발생으로 "
            "극심한 성능 저하. 시스템 RAM의 80% 이하로 할당 권장"
        ),
    ),

    # ===== Element Quality Warnings =====
    40100: ErrorInfo(
        code=40100,
        severity=Severity.WARNING,
        title="Degenerate element detected",
        description=(
            "품질이 매우 나쁜 퇴화(degenerate) 요소가 감지되었습니다. "
            "요소의 종횡비(aspect ratio)가 극단적으로 크거나, 내각이 0도 또는 "
            "180도에 가까운 요소입니다. 유한요소법에서 요소 품질은 "
            "수치 해의 정확도에 직접 영향을 미칩니다. "
            "이상적인 요소(정방형, 정사면체)에서 멀어질수록 "
            "강성 행렬의 조건수(condition number)가 증가하고, "
            "응력/변형률의 수치 오차가 커집니다. "
            "극단적으로 나쁜 요소는 시뮬레이션 초기부터 "
            "최소 timestep을 결정하여 계산 효율도 저하시킵니다."
        ),
        recommendation=(
            "1. 메시 품질 개선 — 후처리기의 메시 품질 검사 기능으로 "
            "문제 요소를 식별하고 리메싱. 목표: aspect ratio < 3, "
            "warpage < 15도, Jacobian > 0.5\n"
            "2. *CONTROL_CHECK 사용 — 시뮬레이션 실행 전 메시 품질을 "
            "자동 검사하여 문제 요소 목록 확인\n"
            "3. 메시 전환(transition) 영역 확인 — 세밀한 메시에서 "
            "조대한 메시로 전환되는 영역에서 퇴화 요소가 생기기 쉬움. "
            "전환 비율을 1:2 이하로 유지"
        ),
    ),

    # ===== Timestep Warnings =====
    30001: ErrorInfo(
        code=30001,
        severity=Severity.WARNING,
        title="Element timestep below minimum",
        description=(
            "요소의 timestep이 TSMIN(최소 허용 timestep) 이하로 감소했습니다. "
            "명시적 적분에서 dt_element = L_char / c (L_char=특성 길이, c=음속)이며, "
            "요소가 왜곡되면 L_char이 줄어들어 dt가 감소합니다. "
            "dt < TSMIN이면 *CONTROL_TIMESTEP의 ERODE 설정에 따라 "
            "요소가 삭제(erosion)되거나 시뮬레이션이 종료됩니다. "
            "ERODE=1이면 해당 요소를 모델에서 제거하고 계산을 계속하며, "
            "ERODE=0이면 시뮬레이션을 종료합니다."
        ),
        recommendation=(
            "1. TSMIN과 ERODE 설정 검토 — *CONTROL_TIMESTEP에서 "
            "TSMIN=적절한 최소 dt 설정, ERODE=1로 과도 왜곡 요소 자동 삭제. "
            "TSMIN은 초기 최소 dt의 1/100 ~ 1/10 수준 권장\n"
            "2. 침식 여부 확인 — ERODE=1이 활성화되었는데 너무 많은 요소가 "
            "삭제되면 해석 결과의 신뢰성이 저하. 삭제 요소 수를 전체의 "
            "5% 이내로 유지하는 것이 권장\n"
            "3. 메시 품질 개선 — 해당 요소 영역의 메시를 세분화하여 "
            "변형이 분산되도록 개선. 초기 요소 품질이 나쁘면 "
            "작은 변형에도 dt가 급락"
        ),
    ),

    # ===== Material Warnings =====
    41200: ErrorInfo(
        code=41200,
        severity=Severity.WARNING,
        title="Material failure criterion met",
        description=(
            "재료 파괴 기준이 충족되었습니다. "
            "LS-DYNA에서 재료 파괴는 *MAT_ADD_EROSION 또는 재료 모델 내장 "
            "파괴 기준(예: Johnson-Cook의 D=1.0, GISSMO의 ECRIT)에 의해 "
            "판정됩니다. 파괴된 요소는 모델에서 제거(erosion)되며, "
            "질량과 에너지가 시스템에서 사라집니다. "
            "파괴 기준이 너무 보수적이면 과도한 요소 삭제로 "
            "해석 결과가 왜곡되고, 너무 관대하면 비물리적 변형이 허용됩니다."
        ),
        recommendation=(
            "1. 파괴 변형률/응력 값 검증 — 재료 시험 데이터와 비교하여 "
            "파괴 기준이 합리적인지 확인. 인장 시험의 파단 변형률과 "
            "시뮬레이션의 유효 소성 변형률(effective plastic strain) 비교\n"
            "2. 파괴 모델 적합성 — 하중 유형(인장, 압축, 전단)에 맞는 "
            "파괴 모델 사용. 삼축 응력 의존성을 고려하는 모델 "
            "(GISSMO, Johnson-Cook damage) 권장\n"
            "3. 삭제 요소 수 모니터링 — 전체 요소 대비 삭제 비율이 "
            "5%를 초과하면 파괴 기준 또는 메시를 재검토"
        ),
    ),

    # ===== Rigid Body Warnings =====
    60100: ErrorInfo(
        code=60100,
        severity=Severity.WARNING,
        title="Rigid body mass too small",
        description=(
            "강체(rigid body)의 질량이 매우 작습니다. "
            "LS-DYNA에서 *MAT_RIGID(MAT 20)로 정의된 파트는 강체로 처리되어 "
            "내부 변형 없이 운동합니다. 강체의 운동은 F = ma로 계산되는데, "
            "질량 m이 매우 작으면 작은 접촉력에도 큰 가속도가 발생합니다. "
            "이는 접촉하는 변형체(deformable body)에 비정상적으로 큰 "
            "충격을 전달하여 수치 불안정을 유발할 수 있습니다. "
            "도구(tool) 등 질량이 작은 강체는 관성을 무시하고 "
            "속도/변위 구속으로 제어하는 것이 안정적입니다."
        ),
        recommendation=(
            "1. 강체 질량 확인 — *MAT_RIGID의 밀도(RO)와 체적의 곱이 "
            "합리적인지 확인. 필요하면 밀도를 인위적으로 높여 "
            "접촉 안정성 확보\n"
            "2. 속도/변위 경계조건 사용 — *BOUNDARY_PRESCRIBED_MOTION으로 "
            "강체 운동을 직접 제어하면 질량에 무관하게 안정적\n"
            "3. 접촉 soft constraint — 질량이 작은 강체와의 접촉에서 "
            "SOFT=1/2 사용하여 접촉 강성을 양면 질량 기반으로 계산"
        ),
    ),

    # ===== Adaptive/Remeshing =====
    70100: ErrorInfo(
        code=70100,
        severity=Severity.WARNING,
        title="Adaptive remeshing issue",
        description=(
            "적응적 리메싱(adaptive remeshing) 과정에서 문제가 발생했습니다. "
            "LS-DYNA의 r-adaptive 또는 h-adaptive 리메싱은 "
            "변형이 큰 영역의 메시를 자동으로 세분화하는데, "
            "리메싱 알고리즘이 유효한 메시를 생성하지 못하면 "
            "이 경고가 발생합니다. 원인: 극심한 왜곡, 복잡한 기하형상, "
            "또는 리메싱 기준(refinement criteria)의 부적절한 설정."
        ),
        recommendation=(
            "1. 리메싱 파라미터 검토 — *CONTROL_ADAPTIVE에서 리메싱 기준과 "
            "최대 세분화 레벨(MAXLVL) 확인. MAXLVL이 너무 크면 "
            "과도하게 세밀한 메시가 생성되어 메모리/시간 문제 발생\n"
            "2. 리메싱 간격 조정 — 리메싱 주기(FREQ)를 늘려 "
            "변형이 충분히 진행된 후 리메싱 수행\n"
            "3. 초기 메시 품질 개선 — 초기 메시가 양호하면 "
            "리메싱 알고리즘도 안정적으로 작동합니다"
        ),
    ),

    # ===== SPH Warnings =====
    80100: ErrorInfo(
        code=80100,
        severity=Severity.WARNING,
        title="SPH particle issue",
        description=(
            "SPH(Smoothed Particle Hydrodynamics) 입자 계산에서 문제가 발생했습니다. "
            "SPH는 메시 없이 입자(particle) 기반으로 계산하는 방법으로, "
            "커널 함수 W(r,h)의 영향 반경(smoothing length h) 내의 "
            "이웃 입자들과의 상호작용으로 물리량을 계산합니다. "
            "입자 간격이 불균일하거나, 영향 반경 내 이웃 입자 수가 "
            "부족하면 수치 오차가 증가합니다."
        ),
        recommendation=(
            "1. SPH 파라미터 검토 — smoothing length, 입자 간격, "
            "이웃 입자 수(CSLH) 등 확인\n"
            "2. 입자 분포 개선 — 초기 입자 배치를 균일하게 조정\n"
            "3. SPH-FEM 커플링 확인 — FEM과 SPH 경계에서 "
            "접촉 설정이 적절한지 확인"
        ),
    ),

    # ===== Contact Velocity / Release Warnings (40xxx, 41xxx) =====
    40532: ErrorInfo(
        code=40532,
        severity=Severity.WARNING,
        title="Slave node penetration velocity exceeds limit",
        description=(
            "접촉 slave 노드의 관통 속도(penetration velocity)가 허용 한계를 초과했습니다. "
            "Penalty contact에서 slave 노드가 master surface를 통과할 때 접촉력 F = k × g을 "
            "적용하여 관통을 복원하는데, 속도가 너무 크면 penalty force가 불안정해집니다. "
            "이 경고는 고속 충격 해석에서 자주 발생하며, 반복될수록 에너지 보존이 "
            "깨져 에너지 비율(energy ratio)이 1.0에서 벗어납니다. "
            "원인: (1) 과도한 초기 속도, (2) 너무 작은 접촉 stiffness, "
            "(3) 메시 크기 불일치로 큰 요소가 작은 요소를 빠르게 관통."
        ),
        recommendation=(
            "1. SLSFAC(penalty scale factor) 증가 — *CONTROL_CONTACT에서 SLSFAC를 "
            "기본값(0.1)에서 0.3~0.5로 늘려 접촉 강성 향상\n"
            "2. Soft constraint 사용 — SOFT=1(segment-based)로 변경하면 "
            "관통 속도 기반이 아닌 면 기반 접촉력을 계산하여 안정성 향상\n"
            "3. 메시 크기 균일화 — slave/master 면의 요소 크기 비율을 1:3 이하로 유지. "
            "큰 요소 → 작은 요소 충돌 시 penetration velocity가 급증\n"
            "4. TSSFAC 감소 — timestep scale factor를 낮춰 각 스텝의 관통 증가량을 제한"
        ),
    ),
    40533: ErrorInfo(
        code=40533,
        severity=Severity.WARNING,
        title="Contact velocity too high — slave node removed from tracking",
        description=(
            "접촉 slave 노드의 속도가 너무 높아 접촉 추적에서 제외되었습니다. "
            "LS-DYNA의 segment-based contact(SOFT=1/2)에서 slave 노드 속도 |v| > VTHK × c "
            "(c = 음속, VTHK = 속도 임계값 계수)이면 해당 노드를 contact bucket에서 제거합니다. "
            "이는 비현실적인 고속 노드가 접촉 계산을 불안정하게 만드는 것을 방지하는 보호 메커니즘이지만, "
            "제거된 노드는 그 후로 접촉력을 받지 않아 물리적 오류가 발생할 수 있습니다. "
            "발생 빈도가 높으면(> 총 사이클의 10%) 접촉 불안정 또는 수치적 발산의 전조입니다."
        ),
        recommendation=(
            "1. 에너지 이력 모니터링 — glstat의 kinetic energy와 sliding interface energy 확인. "
            "비정상적인 급증이 있으면 수치 불안정이 발생 중\n"
            "2. VTHK 파라미터 검토 — *CONTROL_CONTACT에서 VTHK를 높여 "
            "더 많은 속도 범위를 허용. 단, 수치 안정성과 trade-off\n"
            "3. 초기 속도 조건 검토 — 과도한 초기 속도(*INITIAL_VELOCITY)가 "
            "설정되어 있지 않은지 확인. 단위 오류로 인한 과대 속도 주의\n"
            "4. 접촉 타입 변경 — AUTOMATIC_SURFACE_TO_SURFACE 대신 "
            "AUTOMATIC_NODES_TO_SURFACE 또는 ERODING_SURFACE_TO_SURFACE 사용 검토"
        ),
    ),
    40538: ErrorInfo(
        code=40538,
        severity=Severity.WARNING,
        title="Slave node released from contact surface",
        description=(
            "접촉 slave 노드가 접촉 표면에서 해제(released)되었습니다. "
            "LS-DYNA는 접촉에서 노드 해제 시 에너지 보존을 위해 인공 에너지를 주입하는데, "
            "이 경고는 그 과정이 발생했음을 알립니다. "
            "노드 해제는 (1) 접촉면이 분리될 때(정상적), (2) 관통이 너무 깊어 "
            "복원 불가능할 때(비정상적), (3) 접촉 검색 영역을 벗어날 때 발생합니다. "
            "비정상적 해제가 반복되면 에너지 비율이 1.0을 벗어나고 "
            "결과의 신뢰성이 저하됩니다."
        ),
        recommendation=(
            "1. 초기 관통(initial penetration) 확인 — 시뮬레이션 시작 시 "
            "d3hsp의 'initial penetration' 항목에서 관통 규모 확인. "
            "큰 초기 관통이 있으면 PENOPT=4로 해소\n"
            "2. 접촉 bucket 크기 확인 — BSORT(bucket sort 주기)를 줄여 "
            "접촉 검색을 더 자주 수행하면 노드가 검색 영역을 벗어나는 것을 방지\n"
            "3. 에너지 비율 추적 — energy ratio가 1.1을 초과하면 "
            "비정상적인 노드 해제로 인한 에너지 누입이 발생 중\n"
            "4. IGNORE 옵션 — *CONTACT에서 IGNORE=2 설정으로 초기 관통을 "
            "점진적으로 해소하면 초기 해제 빈도 감소"
        ),
    ),
    40552: ErrorInfo(
        code=40552,
        severity=Severity.WARNING,
        title="Contact penetration depth exceeds penalty limit",
        description=(
            "접촉 slave 노드의 관통 깊이(penetration depth)가 "
            "penalty contact의 허용 한계를 초과했습니다. "
            "Penalty contact에서 최대 허용 관통 깊이는 MPAR × (요소 크기) × SLSFAC로 결정되며, "
            "이를 초과하면 penalty force가 더 이상 증가하지 않거나 "
            "노드가 해제됩니다. 이는 접촉 강성이 실제 재료 강성보다 "
            "너무 낮게 설정되어 있음을 의미합니다."
        ),
        recommendation=(
            "1. SLSFAC 증가 — penalty scale factor를 높여 접촉 강성 증가. "
            "너무 크면 timestep이 줄어들 수 있으므로 단계적으로 조정(0.1 → 0.3 → 0.5)\n"
            "2. 메시 세분화 — 접촉 영역의 요소 크기를 줄이면 "
            "상대적 관통 깊이(penetration/element_size 비율)가 감소\n"
            "3. SOFT=2 사용 — segment-based penalty를 사용하면 "
            "segment 면적 기반으로 강성을 계산하여 더 일관된 접촉 거동\n"
            "4. 접촉 타입 검토 — 매우 딱딱한(rigid/stiff) 재료 간 접촉에서는 "
            "constraint-based contact(SOFT=0에서 TIED 계열) 사용 검토"
        ),
    ),
    40571: ErrorInfo(
        code=40571,
        severity=Severity.INFO,
        title="Initial penetration detected and adjusted",
        description=(
            "시뮬레이션 초기화 시 접촉면에서 초기 관통(initial penetration)이 "
            "감지되어 자동으로 조정되었습니다. "
            "LS-DYNA는 *CONTROL_CONTACT의 PENOPT 설정에 따라 초기 관통을 "
            "다르게 처리합니다: PENOPT=1(기본)은 관통을 무시, "
            "PENOPT=4는 초기 관통 기저값을 설정하여 접촉력이 관통 증분에만 반응하도록 합니다. "
            "이 경고 자체는 정상 처리되었음을 나타내지만, "
            "관통 규모가 요소 크기의 10%를 초과하면 초기 응력 오류가 발생할 수 있습니다."
        ),
        recommendation=(
            "1. 초기 관통 규모 확인 — d3hsp에서 'initial penetration' 항목으로 "
            "관통 깊이와 영향받는 인터페이스 확인\n"
            "2. 기하학적 수정 — 메시 편집 도구에서 접촉면 사이의 초기 간격을 "
            "제거하여 근본적으로 관통이 없는 초기 형상 구성\n"
            "3. IGNORE=2 사용 — 관통을 처음 몇 스텝에 걸쳐 점진적으로 해소하여 "
            "충격적인 초기 접촉력 방지"
        ),
    ),
    41314: ErrorInfo(
        code=41314,
        severity=Severity.WARNING,
        title="Contact slave node velocity exceeds removal threshold",
        description=(
            "접촉 slave 노드의 속도가 제거(removal) 임계값을 초과하여 "
            "접촉 추적에서 제거되었습니다. "
            "40533 경고와 유사하지만, 41314는 특히 eroding/failure 접촉에서 "
            "노드가 파괴(erosion) 직전 고속으로 이동할 때 발생합니다. "
            "이 경고가 발생하면 해당 노드는 접촉 계산에서 완전히 제외되어 "
            "인접 요소와의 충돌이 무시될 수 있습니다."
        ),
        recommendation=(
            "1. 침식 기준 검토 — *MAT_ADD_EROSION의 파괴 변형률이 너무 커서 "
            "요소가 장시간 고속 거동하고 있는 것은 아닌지 확인\n"
            "2. VTHK 값 조정 — *CONTROL_CONTACT에서 노드 제거 속도 임계값 조정\n"
            "3. Eroding contact 사용 — *CONTACT_ERODING_SURFACE_TO_SURFACE 등 "
            "erosion을 고려한 접촉 타입 사용이 적합한지 검토"
        ),
    ),

    # ===== Curve / Table Warnings (21xxx) =====
    21129: ErrorInfo(
        code=21129,
        severity=Severity.WARNING,
        title="Curve value extrapolated beyond defined range",
        description=(
            "로드 커브(*DEFINE_CURVE)의 독립 변수값이 정의된 범위를 벗어나 "
            "외삽(extrapolation)이 적용되었습니다. "
            "LS-DYNA는 커브 범위 밖에서 마지막 두 점을 잇는 직선으로 외삽하는데, "
            "이 결과는 재료의 실제 거동과 크게 다를 수 있습니다. "
            "특히 응력-변형률 커브, 변형률 속도 의존 커브, 하중 이력 커브에서 "
            "외삽이 발생하면 재료 응답이 비물리적으로 계산됩니다. "
            "예: LCID가 유효 소성 변형률 vs 항복응력인데, 변형이 커브 끝점 이상 "
            "진행되면 항복응력이 외삽값으로 계산되어 비현실적 결과 발생."
        ),
        recommendation=(
            "1. 커브 정의 범위 확장 — 시뮬레이션의 최대 예상 변수 범위까지 "
            "커브 데이터 포인트를 추가. 특히 충격 해석에서 변형률 속도 범위 확인\n"
            "2. OFFA/OFFO 설정 — *DEFINE_CURVE의 오프셋 파라미터 검토\n"
            "3. EXTRAP 옵션 — 일부 재료 모델에서 외삽 방법(선형/일정값)을 "
            "제어할 수 있으므로 재료 카드 매뉴얼 참조\n"
            "4. 외삽 영역 확인 — d3hsp의 경고 메시지에서 커브 ID와 "
            "외삽이 발생한 변수값을 확인하여 현실적인 범위인지 판단"
        ),
    ),
    21329: ErrorInfo(
        code=21329,
        severity=Severity.WARNING,
        title="Curve discretization error — too few data points",
        description=(
            "커브(*DEFINE_CURVE)의 데이터 포인트가 너무 적어 "
            "정확한 보간이 어렵습니다. "
            "LS-DYNA는 커브를 선형 보간(linear interpolation)으로 처리하는데, "
            "비선형 거동(예: 지수함수, S-곡선 형태의 응력-변형률)을 "
            "소수의 데이터 포인트로 표현하면 보간 오차가 누적됩니다. "
            "이 이산화 오차는 응력 계산의 정확도를 떨어뜨리고, "
            "특히 재료 거동의 변곡점 근처에서 오차가 커집니다."
        ),
        recommendation=(
            "1. 데이터 포인트 추가 — 커브의 곡률이 큰 영역에 데이터를 추가. "
            "일반적으로 50~100개 포인트가 적절하며, 변곡점 근처는 촘촘히 배치\n"
            "2. 커브 정확도 검증 — 보간된 커브를 플롯하여 원래 재료 데이터와 "
            "비교하고, 최대 오차가 1% 이내인지 확인\n"
            "3. 자동 이산화 도구 — 재료 공급업체의 FEA 입력 파일에서 "
            "충분한 포인트가 있는 커브 데이터를 요청"
        ),
    ),

    # ===== Material Parameter Warnings (20xxx) =====
    20268: ErrorInfo(
        code=20268,
        severity=Severity.WARNING,
        title="Material parameter outside recommended range",
        description=(
            "재료 파라미터가 해당 재료 모델의 권장 범위를 벗어났습니다. "
            "LS-DYNA의 재료 모델은 특정 파라미터 범위를 가정하여 개발되었으며, "
            "범위를 벗어나면 구성 방정식이 비물리적 결과를 반환할 수 있습니다. "
            "예: Poisson 비율 ν ≥ 0.5(명시적 해석에서 체적 보존 문제), "
            "밀도 = 0, 음의 탄성계수 등. "
            "단위 시스템 불일치로 인한 파라미터 스케일 오류가 흔한 원인입니다."
        ),
        recommendation=(
            "1. 재료 물성 단위 검증 — 프로젝트의 단위 시스템(m-kg-s, mm-ton-s, mm-g-ms 등)을 "
            "확인하고 모든 재료 파라미터가 동일한 단위계를 사용하는지 검토\n"
            "2. 경고 메시지의 파라미터 ID 확인 — d3hsp에서 어떤 파라미터가 "
            "범위를 벗어났는지 확인 후 LS-DYNA 매뉴얼의 유효 범위와 비교\n"
            "3. 재료 데이터 검증 — 실험 측정값 또는 문헌 데이터와 비교하여 "
            "물성값이 합리적인지 확인"
        ),
    ),
    20282: ErrorInfo(
        code=20282,
        severity=Severity.WARNING,
        title="Material density is too low or zero",
        description=(
            "재료 밀도(density)가 매우 낮거나 0에 가깝습니다. "
            "명시적 시간 적분에서 timestep dt = TSSFAC × L/c = TSSFAC × L × √(ρ/E)이므로, "
            "밀도 ρ가 0에 가까우면 dt → 0이 되어 계산이 불가능해집니다. "
            "또한 접촉에서 노드 질량 m = ρ × V/n에 따라 관성이 결정되는데, "
            "질량이 0에 가까우면 작은 접촉력에도 무한한 가속도가 발생합니다. "
            "원인: 단위 오류(예: SI 단위계 밀도 7850 kg/m³를 mm-ton-s 단위 "
            "7.85E-9 ton/mm³로 변환하지 않고 입력)."
        ),
        recommendation=(
            "1. 단위 변환 확인 — 프로젝트 단위 시스템에 맞게 밀도를 변환: "
            "  mm-ton-s: 강철 = 7.85E-9 ton/mm³\n"
            "  mm-kg-ms: 강철 = 7.85E-3 kg/mm³\n"
            "  m-kg-s:   강철 = 7850 kg/m³\n"
            "2. RO(density) 값 직접 확인 — *MAT 카드의 RO 파라미터가 "
            "0이 아닌 합리적인 값인지 확인\n"
            "3. *MAT_ELASTIC 또는 *MAT_RIGID의 경우 강체 파트는 "
            "CMO+CON1+CON2로 질량을 직접 지정하는 방법도 있음"
        ),
    ),
    20546: ErrorInfo(
        code=20546,
        severity=Severity.WARNING,
        title="Material model convergence warning",
        description=(
            "재료 모델의 응력 업데이트(stress update) 알고리즘이 수렴 문제를 겪고 있습니다. "
            "탄-소성 재료에서 응력은 return mapping algorithm으로 계산되는데, "
            "변형률 증분 Δε이 너무 크거나 항복면(yield surface)의 곡률이 크면 "
            "반복 계산이 지정된 횟수(NITER) 내에 수렴하지 못합니다. "
            "이는 주로 rate-dependent 재료(Cowper-Symonds, Johnson-Cook)나 "
            "손상 모델(GISSMO)에서 타임스텝이 클 때 발생합니다."
        ),
        recommendation=(
            "1. TSSFAC 감소 — 타임스텝을 줄이면 Δε 증분이 작아져 "
            "return mapping 수렴이 개선됨\n"
            "2. 재료 모델 파라미터 검토 — 항복면의 곡률이 큰 영역(변형률 경화 지수, "
            "변형률 속도 파라미터)의 파라미터가 물리적으로 합리적인지 확인\n"
            "3. NITER 증가 — 일부 재료 모델에서 최대 반복 횟수를 늘릴 수 있음 "
            "(재료 카드의 NIT 또는 NITER 파라미터 참조)"
        ),
    ),

    # ===== Initialization Warnings (30xxx) =====
    30062: ErrorInfo(
        code=30062,
        severity=Severity.WARNING,
        title="Part or section definition inconsistency",
        description=(
            "파트(*PART)와 섹션(*SECTION) 정의 간에 불일치가 발생했습니다. "
            "예: *SECTION_SOLID에서 ELFORM=2(fully integrated S/R solid)로 "
            "설정했지만 해당 파트의 요소가 이 formulation을 지원하지 않는 경우, "
            "또는 *SECTION_SHELL에서 NIP(두께 방향 적분점 수)가 재료 모델의 "
            "요구사항과 맞지 않는 경우 발생합니다. "
            "LS-DYNA는 불일치를 감지하면 기본값으로 대체할 수 있으며, "
            "이때 설계 의도와 다른 요소 공식이 사용될 수 있습니다."
        ),
        recommendation=(
            "1. *SECTION 정의와 실제 요소 타입 확인 — 솔리드 요소 파트에 "
            "shell section이 할당되어 있거나 그 반대인 경우 수정\n"
            "2. ELFORM 지원 여부 확인 — 사용하려는 ELFORM이 해당 요소 타입에서 "
            "지원되는지 LS-DYNA 매뉴얼 확인\n"
            "3. d3hsp 경고 메시지 확인 — 어떤 파트 ID에서 문제가 발생했는지 "
            "상세 내용을 d3hsp에서 확인"
        ),
    ),
    30128: ErrorInfo(
        code=30128,
        severity=Severity.WARNING,
        title="ALE mesh initialization warning",
        description=(
            "ALE(Arbitrary Lagrangian-Eulerian) 메시 초기화 중 경고가 발생했습니다. "
            "ALE 해석에서는 유체/기체 영역이 고정된 Euler 메시에서 계산되며, "
            "구조물과의 FSI(Fluid-Structure Interaction) 경계면 설정이 중요합니다. "
            "경고 원인: (1) ALE 메시가 Lagrange 구조물 메시와 충분히 겹치지 않음, "
            "(2) *ALE_MULTI-MATERIAL_GROUP 정의 오류, "
            "(3) ALE 요소의 초기 void fraction 설정 문제."
        ),
        recommendation=(
            "1. ALE 메시 범위 확인 — ALE 메시가 시뮬레이션 전 구간에서 "
            "Lagrange 구조물이 이동하는 영역을 모두 포함하는지 확인\n"
            "2. *CONSTRAINED_LAGRANGE_IN_SOLID 검토 — FSI 커플링 카드의 "
            "파라미터(NQUAD, CTYPE)가 올바르게 설정되어 있는지 확인\n"
            "3. 초기 void fraction — *INITIAL_VOLUME_FRACTION_GEOMETRY로 "
            "각 ALE 그룹의 초기 체적 비율이 올바르게 설정되어 있는지 확인"
        ),
    ),
    30131: ErrorInfo(
        code=30131,
        severity=Severity.WARNING,
        title="Constrained nodeset initialization warning",
        description=(
            "구속 노드셋(*CONSTRAINED_NODESET) 초기화 중 경고가 발생했습니다. "
            "이 경고는 구속 정의에서 (1) 중복 노드(같은 노드가 여러 구속에 포함), "
            "(2) 존재하지 않는 노드 ID 참조, (3) 자유도(DOF) 충돌(같은 "
            "자유도가 여러 구속에 의해 이중 구속)이 발생했을 때 나타납니다."
        ),
        recommendation=(
            "1. 노드셋 중복 확인 — 여러 *CONSTRAINED_* 정의에 동일한 노드가 "
            "중복 포함되지 않는지 확인\n"
            "2. 노드 ID 유효성 검증 — *SET_NODE에서 참조하는 모든 노드 ID가 "
            "모델에 실제로 존재하는지 확인\n"
            "3. DOF 충돌 제거 — 같은 노드의 같은 자유도에 multiple constraint가 "
            "적용되지 않도록 구속 정의 검토"
        ),
    ),
    30455: ErrorInfo(
        code=30455,
        severity=Severity.WARNING,
        title="Contact segment not found during initialization",
        description=(
            "접촉 정의 초기화 중 slave 또는 master segment를 찾을 수 없었습니다. "
            "*CONTACT 카드에서 참조하는 세그먼트 세트(SSID/MSID)에 해당하는 "
            "면 요소가 없거나, part set 정의에 문제가 있을 때 발생합니다. "
            "이 접촉 정의는 초기화에 실패하여 비활성 상태이며, "
            "해당 파트 간 접촉이 감지되지 않습니다."
        ),
        recommendation=(
            "1. SSTYP/MSTYP 확인 — slave/master 타입 코드가 올바른지 확인 "
            "(0=세그먼트 세트, 1=쉘 요소 세트, 2=파트 세트, 3=파트 ID)\n"
            "2. SSID/MSID 유효성 — 참조하는 set ID가 *SET_PART, *SET_SEGMENT 등에 "
            "실제로 정의되어 있는지 확인\n"
            "3. 파트 요소 타입 — shell 파트만 surface contact의 master가 될 수 있으며, "
            "solid 파트는 face 기반 세그먼트 세트를 별도 정의해야 함"
        ),
    ),

    # ===== Implicit Solver Warnings (60xxx) =====
    60121: ErrorInfo(
        code=60121,
        severity=Severity.WARNING,
        title="Implicit solver convergence is slow",
        description=(
            "암시적(implicit) 솔버의 Newton-Raphson 반복이 수렴하지만 느립니다. "
            "암시적 해석에서 잔류력(residual) R = F_ext - F_int가 수렴 기준 이하로 "
            "줄어드는 데 많은 반복이 필요하다는 의미입니다. "
            "수렴이 느린 원인: (1) 하중 증분이 너무 커서 비선형 곡률이 강함, "
            "(2) 접촉 상태 변화(이중 접촉 반복), "
            "(3) 재료 비선형성(항복면 근처), "
            "(4) 좌굴 근처의 기하 비선형."
        ),
        recommendation=(
            "1. 하중 증분 감소 — *CONTROL_IMPLICIT_SOLUTION에서 DT0를 줄여 "
            "각 스텝의 비선형도를 낮춤\n"
            "2. 선접촉 알고리즘 개선 — *CONTROL_IMPLICIT_SOLUTION의 "
            "CONVERG 기준과 NLPRINT 설정 검토\n"
            "3. 자동 타임스텝 제어 — *CONTROL_IMPLICIT_AUTO 사용으로 "
            "수렴이 어려울 때 자동으로 스텝 크기 감소\n"
            "4. 선형화 기법 검토 — 수치 접선 강성(KFAIL) 사용을 고려하여 "
            "수렴 안정성 향상"
        ),
    ),

    # ===== Contact/Interface Errors (30xxx) =====
    30099: ErrorInfo(
        code=30099,
        severity=Severity.CRITICAL,
        title="Contact pair definition error",
        description=(
            "접촉 쌍(contact pair) 정의에 오류가 있어 초기화에 실패했습니다. "
            "이 에러는 *CONTACT 카드에서 (1) 존재하지 않는 파트/세트 ID 참조, "
            "(2) 같은 slave와 master에 대해 충돌하는 접촉 옵션이 중복 정의, "
            "(3) 특정 접촉 타입에서 지원되지 않는 파라미터 조합, "
            "(4) 대규모 모델에서 segment 수가 내부 한계를 초과할 때 발생합니다. "
            "에러가 발생한 접촉은 완전히 비활성화되므로 해당 파트 간 "
            "충돌이 전혀 감지되지 않아 비물리적 결과가 발생합니다."
        ),
        recommendation=(
            "1. 접촉 카드의 ID 참조 검증 — *CONTACT에서 참조하는 모든 "
            "SSID, MSID가 유효한 파트/세트/세그먼트 ID인지 확인\n"
            "2. 중복 접촉 정의 제거 — 동일한 파트 쌍에 여러 접촉이 정의된 경우 "
            "하나로 통합하거나 충돌 방지 옵션 확인\n"
            "3. 접촉 타입 호환성 — 사용하는 접촉 타입이 요소 타입(solid/shell/beam)과 "
            "호환되는지 LS-DYNA 매뉴얼에서 확인\n"
            "4. d3hsp 에러 상세 확인 — 에러 발생 직후 라인에서 어떤 접촉 ID가 "
            "문제인지 특정하여 해당 *CONTACT 카드 검토"
        ),
    ),

    # ===== Curve/Table Errors (21xxx) =====
    21302: ErrorInfo(
        code=21302,
        severity=Severity.CRITICAL,
        title="Curve ID not found or invalid",
        description=(
            "재료 또는 경계조건 카드에서 참조하는 커브 ID(*DEFINE_CURVE)를 "
            "찾을 수 없거나 유효하지 않습니다. "
            "LS-DYNA는 커브를 찾지 못하면 해당 물리량(하중, 응력, 속도 등)을 "
            "0 또는 기본값으로 처리합니다. 이는 하중 조건이 완전히 제거된 것과 동일하며, "
            "예상 외의 결과를 초래합니다. "
            "원인: (1) LCID 번호 오타, (2) *DEFINE_CURVE 카드 누락, "
            "(3) include 파일 참조 오류."
        ),
        recommendation=(
            "1. LCID 번호 확인 — 재료/하중 카드의 LCID 값이 *DEFINE_CURVE에 "
            "정의된 ID와 정확히 일치하는지 확인\n"
            "2. *DEFINE_CURVE 누락 확인 — 입력 파일에 해당 ID의 커브가 "
            "실제로 정의되어 있는지 grep/텍스트 검색으로 확인\n"
            "3. Include 파일 경로 확인 — 커브가 별도 파일에 있다면 "
            "*INCLUDE 카드의 파일 경로가 올바른지 확인\n"
            "4. ID 충돌 확인 — 같은 ID를 두 곳에서 다르게 정의한 경우 "
            "LS-DYNA는 마지막 정의를 사용하므로 ID 일관성 점검"
        ),
    ),

    # ===== Material Errors (20xxx) =====
    20018: ErrorInfo(
        code=20018,
        severity=Severity.CRITICAL,
        title="Material model initialization failed",
        description=(
            "재료 모델 초기화에 실패했습니다. "
            "이 에러는 재료 파라미터가 특정 재료 모델의 내부 요구사항을 만족하지 못할 때 발생합니다. "
            "예: *MAT_ELASTIC에서 E=0(탄성계수 0은 무한 유연체를 의미, 수치 불가), "
            "*MAT_PIECEWISE_LINEAR_PLASTICITY에서 항복응력 커브 ID가 잘못됨, "
            "*MAT_MOONEY-RIVLIN_RUBBER에서 C10+C01 ≤ 0(음의 초기 전단 강성). "
            "초기화에 실패한 파트는 올바른 강성 행렬 없이 계산되어 즉시 수치 불안정을 유발합니다."
        ),
        recommendation=(
            "1. d3hsp 에러 상세 확인 — 어떤 재료 ID(MID)와 파라미터가 문제인지 "
            "에러 메시지에서 확인\n"
            "2. 재료 파라미터 물성 검증 — E, G, ν, σ_y, ρ가 모두 양수이고 "
            "물리적 범위에 있는지 확인 (예: ν < 0.5 for explicit)\n"
            "3. 커브 ID 참조 — 항복 커브, 손상 커브 등이 올바른 LCID를 참조하고 "
            "해당 커브가 정의되어 있는지 확인\n"
            "4. 재료 타입 호환성 — 해당 *MAT 타입이 요소 타입(solid/shell/beam)과 "
            "호환되는지 LS-DYNA 매뉴얼 확인"
        ),
    ),
    20216: ErrorInfo(
        code=20216,
        severity=Severity.CRITICAL,
        title="Material parameter physically invalid",
        description=(
            "재료 파라미터가 물리적으로 불가능한 값을 가집니다. "
            "음의 탄성계수(E < 0), 포아송 비율 ν ≥ 0.5(명시적 해석에서 "
            "체적 변형률이 발산), 음의 밀도, 또는 열역학적 불가능한 "
            "상태방정식 파라미터 조합이 해당됩니다. "
            "이러한 파라미터로는 물리적으로 유효한 강성 행렬을 구성할 수 없으므로 "
            "시뮬레이션이 즉시 종료됩니다."
        ),
        recommendation=(
            "1. 단위 시스템 점검 — 가장 흔한 원인은 단위 변환 오류. "
            "프로젝트 전체의 단위계를 통일하고 각 재료 물성값을 "
            "해당 단위에 맞게 변환했는지 확인\n"
            "2. 포아송 비율 확인 — 명시적 해석에서 ν = 0.5는 비압축성을 의미하며, "
            "수치적으로 처리 불가. 고무류는 0.495~0.499 사용\n"
            "3. 재료 카드 문서 비교 — LS-DYNA 매뉴얼에서 각 파라미터의 유효 범위와 "
            "부호 규약을 확인하고 재료 데이터 시트와 대조"
        ),
    ),

    # ===== Element Errors (10xxx) =====
    10133: ErrorInfo(
        code=10133,
        severity=Severity.CRITICAL,
        title="Solid element connectivity error",
        description=(
            "Solid 요소의 노드 연결 정보(connectivity)에 오류가 있습니다. "
            "요소의 노드 수가 요소 타입과 맞지 않거나, 노드 ID가 모델에 없거나, "
            "요소 노드들이 동일 좌표를 가져 체적이 0인 경우 발생합니다. "
            "연결 오류가 있는 요소는 강성 행렬을 계산할 수 없어 "
            "시뮬레이션 시작 시점에 에러가 발생합니다."
        ),
        recommendation=(
            "1. 메시 품질 검사 — 후처리기에서 연결 오류가 있는 요소를 검색하고 "
            "해당 요소의 노드 순서 확인\n"
            "2. 중복 노드 제거 — Merge/Equivalence 기능으로 공유면의 노드가 "
            "하나의 노드로 병합되어 있는지 확인\n"
            "3. 요소 타입 확인 — *ELEMENT_SOLID에서 8노드 hex, 4노드 tet, "
            "6노드 penta 등 노드 수가 올바른지 확인"
        ),
    ),
    10246: ErrorInfo(
        code=10246,
        severity=Severity.CRITICAL,
        title="Solid element excessive distortion",
        description=(
            "Solid 요소가 허용 한계를 초과하는 왜곡(distortion)을 보입니다. "
            "Jacobian det(J)이 초기값 대비 특정 비율(EDGMIN 설정)보다 작아졌을 때 발생합니다. "
            "extreme distortion에서는 shape function이 더 이상 유효하지 않아 "
            "응력 계산 결과를 신뢰할 수 없으며, 계속 진행하면 negative volume이나 "
            "NaN이 발생합니다."
        ),
        recommendation=(
            "1. 요소 침식 추가 — *MAT_ADD_EROSION으로 과도 변형 전에 요소 제거\n"
            "2. ERODE=1 활성화 — *CONTROL_TIMESTEP에서 dt < TSMIN인 요소 자동 삭제\n"
            "3. 메시 리파인먼트 — 과도 변형 영역을 더 세밀하게 메싱하여 "
            "변형이 분산되도록 유도\n"
            "4. 고차 요소 사용 검토 — 4노드 tet에서 10노드 tet(ELFORM=10, 13)으로 "
            "전환하면 큰 변형에서 더 안정적"
        ),
    ),
    10305: ErrorInfo(
        code=10305,
        severity=Severity.CRITICAL,
        title="Zero-volume solid element detected",
        description=(
            "체적이 0에 가까운 Solid 요소가 감지되었습니다. "
            "초기 메시 생성 오류(노드가 동일 위치에 중복)나 "
            "매우 심한 압축에 의해 요소 체적이 0으로 수렴할 때 발생합니다. "
            "체적이 0이면 밀도 ρ_current = m/V → ∞가 되어 "
            "응력 계산(p = EOS(V/V0, e))이 불가능해집니다."
        ),
        recommendation=(
            "1. 초기 메시 검사 — 메시 생성 직후 zero-volume 요소 검색. "
            "후처리기의 'Check Mesh' 또는 'Element Quality' 기능 활용\n"
            "2. 중복 노드 병합 — 같은 좌표에 있는 노드를 merge하여 "
            "체적이 있는 유효한 요소로 수정\n"
            "3. 침식 설정 추가 — *MAT_ADD_EROSION의 MNEPS(음의 최소 소성 변형률) 또는 "
            "MXEPS로 과도 압축 요소 자동 제거"
        ),
    ),

    # ===== SPG Errors (11xxx) =====
    11507: ErrorInfo(
        code=11507,
        severity=Severity.CRITICAL,
        title="SPG particle stretch parameter error",
        description=(
            "SPG(Smoothed Particle Galerkin) 입자의 신장(stretch) 파라미터가 "
            "유효 범위를 벗어났습니다. "
            "SPG는 메시 없이 Galerkin 방법을 입자 기반으로 구현한 방법으로, "
            "각 입자의 변형을 stretch tensor F로 추적합니다. "
            "det(F) ≤ 0이 되면(물리적으로 불가능한 부피 반전) SPG 계산이 불가능해집니다. "
            "과도한 인장 파괴, 충격 단편화, 또는 초기 파라미터 설정 오류에서 발생합니다."
        ),
        recommendation=(
            "1. SPG 파라미터 검토 — *SECTION_SPG의 SPHKERN, IRANK 등 "
            "SPG 제어 파라미터가 올바르게 설정되어 있는지 확인\n"
            "2. 파괴 기준 추가 — *MAT_ADD_EROSION으로 과도 변형 입자 제거. "
            "SPG에서는 stretch가 특정 임계값을 초과하면 입자를 분리\n"
            "3. 초기 입자 배치 검증 — 입자 간격과 영향 반경(Kernel radius)이 "
            "적절하게 설정되어 있는지 확인"
        ),
    ),

    # ===== Implicit Solver Errors (60xxx) =====
    60004: ErrorInfo(
        code=60004,
        severity=Severity.CRITICAL,
        title="Implicit solver: stiffness matrix is singular",
        description=(
            "암시적 솔버의 전역 강성 행렬 [K]가 특이(singular)하여 "
            "선형 방정식 [K]{u} = {F}의 고유한 해가 존재하지 않습니다. "
            "det[K] = 0인 경우는: (1) 자유 운동(mechanism)이 존재하여 "
            "구조물이 구속 없이 이동 가능한 방향이 있음, "
            "(2) 경계조건이 부족하여 강체 운동이 허용됨, "
            "(3) 국부적 메커니즘(unstable element connectivity), "
            "(4) 좌굴 하중 도달 시 [K_T] = 0. "
            "명시적 해석에서는 문제가 없던 모델도 암시적 해석에서는 "
            "경계조건이 더 엄격하게 요구됩니다."
        ),
        recommendation=(
            "1. 경계조건 충분성 확인 — 모든 강체 운동(6 DOF: 3 평행이동 + 3 회전)이 "
            "구속되어 있는지 확인. 대칭 조건이라면 적절한 SPC 추가\n"
            "2. 연결 오류 탐색 — 메시에서 unconnected node나 isolated element가 "
            "없는지 검사\n"
            "3. 좌굴 하중 확인 — 압축 지배 문제에서 좌굴이 발생하면 [K_T]가 "
            "0이 됨. 초기 불완전형(imperfection)을 추가하거나 "
            "아크 길이 법(arc-length method) 사용\n"
            "4. 하중 증분 감소 — 첫 번째 증분에서 발생하면 초기 강성 문제이므로 "
            "DT0를 줄이고 NSOLVR(솔버 타입) 변경 시도"
        ),
    ),
    60303: ErrorInfo(
        code=60303,
        severity=Severity.CRITICAL,
        title="Implicit solver: line search failed",
        description=(
            "암시적 솔버의 선 탐색(line search) 알고리즘이 실패했습니다. "
            "Newton-Raphson 반복에서 ΔU_n이 계산되면, line search는 "
            "α × ΔU_n 방향으로 에너지 내적 g(α) = R(U+α×ΔU)·ΔU = 0이 되는 "
            "최적 스텝 크기 α를 찾습니다. "
            "g(α) = 0을 만족하는 α를 (0, 1] 내에서 찾지 못하면 라인 서치 실패이며, "
            "이는 현재 방향 ΔU_n이 해로 수렴하는 방향이 아님을 의미합니다. "
            "하중 증분이 너무 크거나, 강성 행렬이 비정확하거나, "
            "접촉 상태가 반복적으로 변할 때 발생합니다."
        ),
        recommendation=(
            "1. 하중 증분 대폭 감소 — *CONTROL_IMPLICIT_SOLUTION의 DT0를 "
            "현재의 1/5~1/10으로 줄임\n"
            "2. *CONTROL_IMPLICIT_AUTO 사용 — 자동 타임스텝 제어를 활성화하면 "
            "수렴 실패 시 자동으로 스텝 크기 감소\n"
            "3. 접촉 안정화 — 접촉 타입을 AUTOMATIC으로 변경하고 SOFT=1/2 시도. "
            "접촉 상태 진동이 원인인 경우 stabilization coefficient 추가\n"
            "4. NSOLVR=12(BFGS) 시도 — 수치 접선 강성 대신 BFGS 업데이트를 "
            "사용하면 일부 비선형 문제에서 더 강건한 수렴"
        ),
    ),
    60315: ErrorInfo(
        code=60315,
        severity=Severity.CRITICAL,
        title="Implicit solver: Newton-Raphson diverged",
        description=(
            "암시적 솔버의 Newton-Raphson 반복이 발산(diverge)했습니다. "
            "각 반복에서 잔류력 |R_n| = |F_ext - F_int|가 수렴 기준 "
            "ε_r = RTOL × |F_ext|보다 감소하지 않고 오히려 증가했습니다. "
            "발산 원인: (1) 하중 증분이 너무 커 강성 행렬이 해 근방에서 "
            "크게 달라짐(강한 비선형), (2) 접촉 상태가 반복마다 역전되는 chattering, "
            "(3) 좌굴 또는 스냅-스루(snap-through) 근처의 불안정 경로, "
            "(4) 강성 행렬 계산 오류(재료 접선 강성의 부정확성)."
        ),
        recommendation=(
            "1. 하중 증분 크게 감소 — DTMIN까지 DT0를 줄여도 발산하면 "
            "모델의 근본적인 불안정성(좌굴, 메커니즘)을 의심\n"
            "2. 호 길이 법(Arc-length method) 도입 — *CONTROL_IMPLICIT_SOLUTION에서 "
            "NSOLVR=6~8로 설정하면 snap-through를 추적할 수 있음\n"
            "3. 초기 불완전형 추가 — 좌굴이 원인이면 모드 형태의 "
            "기하학적 불완전형을 추가하여 경로 선택을 유도\n"
            "4. 명시적 해석으로 전환 검토 — 대변형/대회전이 지배적이면 "
            "명시적 해석이 더 적합할 수 있음"
        ),
    ),

    # ===== SPH/Particle Errors (70xxx) =====
    70021: ErrorInfo(
        code=70021,
        severity=Severity.CRITICAL,
        title="SPH particle interaction error",
        description=(
            "SPH(Smoothed Particle Hydrodynamics) 입자 간 상호작용 계산에서 "
            "오류가 발생했습니다. "
            "SPH에서 물리량 A(x_i) = Σ_j m_j/ρ_j × A_j × W(|x_i-x_j|, h)로 계산되는데, "
            "이웃 입자 수가 극히 적거나(h가 너무 작음), 입자가 분리되어 "
            "smoothing length h 내에 이웃이 없으면 계산이 불안정해집니다. "
            "또한 입자 밀도가 0에 접근하거나 압력 계산에서 발산이 발생할 수 있습니다."
        ),
        recommendation=(
            "1. Smoothing length 검토 — *SECTION_SPH의 CSLH(smoothing length 계수)를 "
            "기본값(1.2~1.5) 범위로 조정. 너무 작으면 이웃 부족, 너무 크면 과도한 평활화\n"
            "2. 입자 간격 균일화 — 초기 입자 배치를 규칙적인 격자 형태로 구성하고 "
            "국부적인 밀집/희박 영역 제거\n"
            "3. Renormalization — SPH의 커널 보정(renormalized SPH, RSPH)을 사용하면 "
            "경계 근처에서의 계산 정확도가 향상됨\n"
            "4. SPG로 전환 검토 — 고체 재료의 파단 해석에는 SPH보다 SPG가 "
            "더 안정적일 수 있음"
        ),
    ),

    # ===== Contact Warnings — 새로 추가 (50xxx) =====
    50134: ErrorInfo(
        code=50134,
        severity=Severity.WARNING,
        title="Tied contact: slave node projected to edge/corner",
        description=(
            "Warning 50134: Tied contact에서 slave 노드가 master segment의 내부가 아닌 "
            "가장자리(edge) 또는 모서리(corner)에 투영되었습니다. "
            "이 경우 구속 조건이 불안정하여 인터페이스 노드의 거동이 비정상적일 수 있습니다. "
            "경계 투영은 tied contact 알고리즘에서 허용 범위 바깥 노드를 "
            "가장 가까운 경계점에 강제 투영할 때 발생합니다. "
            "주요 원인: slave/master 메시 불일치, master surface가 너무 작거나, "
            "초기 형상에서 slave 노드가 master 경계 근방에 위치."
        ),
        recommendation=(
            "1. 메시 일치 확인 — slave/master 파트 경계면의 메시 크기 일치도 향상. "
            "특히 모서리 근방에서 노드 위치 조정\n"
            "2. Master surface 확장 — master segment가 slave 노드를 완전히 포함하도록 "
            "범위 확장 또는 *CONTACT_TIED_... 의 SLDTHK/MSHTHK 파라미터 조정\n"
            "3. SOFT=2(penalty-based tied) 사용 — 경계 투영 문제가 심각하면 "
            "projection 기반에서 penalty 기반으로 전환"
        ),
    ),

    # ===== Contact Warnings (40xxx) — 새로 추가 =====
    40534: ErrorInfo(
        code=40534,
        severity=Severity.WARNING,
        title="Contact: slave node velocity exceeds limit after release",
        description=(
            "Warning 40534: 접촉 해제(release) 후 slave 노드의 속도가 허용 한계를 초과했습니다. "
            "접촉 충돌 후 두 표면이 분리될 때 penalty force가 급격히 0으로 떨어지며 "
            "에너지가 노드 속도로 변환됩니다. 이 과정에서 수치적으로 과도한 반발 속도가 "
            "발생하면 시뮬레이션 불안정의 전조가 될 수 있습니다."
        ),
        recommendation=(
            "1. Contact damping 추가 — *CONTACT의 VDC(viscous damping) 파라미터로 "
            "접촉 해제 시 속도 감소. VDC=20~40 권장\n"
            "2. Penalty stiffness 감소 — SLSFAC를 낮춰 접촉력 크기 완화\n"
            "3. 재료 물성 확인 — 고속 충격에서 strain rate 의존 재료 사용 권장"
        ),
    ),
    40540: ErrorInfo(
        code=40540,
        severity=Severity.WARNING,
        title="Contact: node deletion due to extreme penetration",
        description=(
            "Warning 40540: 과도한 관통(extreme penetration)으로 인해 접촉 노드가 삭제되었습니다. "
            "접촉 관통이 요소 크기보다 훨씬 크면 penalty force 계산이 불안정해지고, "
            "LS-DYNA는 해당 노드를 접촉 알고리즘에서 제거합니다. "
            "이는 접촉 안정성보다 시뮬레이션 지속을 우선할 때의 임시방편입니다. "
            "요소 파괴(erosion) 없이 발생하면 물리적으로 부정확한 결과를 의미합니다."
        ),
        recommendation=(
            "1. 초기 관통 제거 — *CONTACT의 IGNORE=2로 자동 초기 관통 해소. "
            "모델 형상을 재검토하여 겹치는 파트 수정\n"
            "2. 타임스텝 감소 — TSSFAC를 줄여 큰 관통이 발생하기 전에 접촉력 적용\n"
            "3. Eroding contact 사용 — 대변형이 예상되는 경우 *CONTACT_ERODING으로 "
            "요소 삭제와 연계하여 관통 방지"
        ),
    ),
    40565: ErrorInfo(
        code=40565,
        severity=Severity.WARNING,
        title="Contact: segment normal inconsistency",
        description=(
            "Warning 40565: 접촉 세그먼트의 법선 방향이 일관되지 않습니다. "
            "접촉 알고리즘은 세그먼트 법선을 사용하여 관통 방향을 결정하는데, "
            "법선이 잘못된 방향을 가리키면 접촉력이 반대 방향으로 작용하거나 "
            "관통 감지에 실패합니다. 주요 원인: 요소 연결성(connectivity)이 "
            "일관되지 않거나 메시 생성 시 법선 방향이 반전된 경우."
        ),
        recommendation=(
            "1. 메시 법선 확인 — 프리프로세서에서 모든 쉘/솔리드 요소의 "
            "법선 방향 시각화 및 수정\n"
            "2. *CONTACT에서 SSID/MSID 방향 확인 — slave/master 정의 시 "
            "접촉 면이 서로 마주보는지 확인\n"
            "3. AUTO_SINGLE_SURFACE 사용 — 법선 방향 자동 처리 접촉 타입으로 전환"
        ),
    ),
    40864: ErrorInfo(
        code=40864,
        severity=Severity.WARNING,
        title="Contact: beam-to-beam contact initialization warning",
        description=(
            "Warning 40864: 빔-빔(beam-to-beam) 접촉 초기화 중 경고가 발생했습니다. "
            "빔 요소 간 접촉은 선-선(line-to-line) 검색 알고리즘을 사용하며, "
            "빔의 방향, 반지름 정의, 또는 인접 빔의 초기 근접도에 따라 "
            "초기화 문제가 발생할 수 있습니다."
        ),
        recommendation=(
            "1. 빔 단면 반지름 확인 — *SECTION_BEAM에서 반지름(D1, D2)이 "
            "올바르게 정의되어 있는지 확인. 너무 큰 반지름은 초기 접촉을 유발\n"
            "2. 접촉 검색 범위 조정 — *CONTACT_BEAM_EDGE의 SFAC 파라미터로 "
            "접촉 거리 배율 조정\n"
            "3. 초기 간격 확인 — 빔 간 초기 거리가 접촉 두께보다 작지 않은지 확인"
        ),
    ),

    # ===== Initialization Warnings (30xxx) — 새로 추가 =====
    30060: ErrorInfo(
        code=30060,
        severity=Severity.WARNING,
        title="Part initialization: section/material mismatch",
        description=(
            "Warning 30060: 파트 초기화 중 section과 material 정의 간 불일치가 감지되었습니다. "
            "LS-DYNA에서 파트는 *PART 카드로 section ID, material ID, hourglass ID를 "
            "연결하는데, 이 중 하나가 정의되지 않았거나 다른 요소 타입과 호환되지 않으면 "
            "경고가 발생합니다. 예: shell section에 solid material 적용."
        ),
        recommendation=(
            "1. *PART 카드 점검 — SID(section), MID(material) 가 올바른 ID를 "
            "참조하는지 확인\n"
            "2. 요소 타입 일치 — 쉘 요소는 shell section, 솔리드는 solid section 사용\n"
            "3. *SECTION_*/MAT_* 존재 확인 — 참조된 ID가 실제로 정의되어 있는지 검토"
        ),
    ),
    30210: ErrorInfo(
        code=30210,
        severity=Severity.WARNING,
        title="Constraint: SPC node not found in model",
        description=(
            "Warning 30210: *BOUNDARY_SPC에서 참조한 노드 ID가 모델에 존재하지 않습니다. "
            "이 경우 해당 경계 조건이 적용되지 않아 구조가 예상과 다르게 거동할 수 있습니다. "
            "특히 rigid body motion이 허용되거나 암묵적 해석에서 singular matrix가 발생할 수 있습니다."
        ),
        recommendation=(
            "1. 노드 ID 확인 — *BOUNDARY_SPC 또는 *BOUNDARY_PRESCRIBED_MOTION에서 "
            "참조하는 NID가 *NODE 섹션에 정의되어 있는지 확인\n"
            "2. 단위계 일치 — 다른 파일에서 include할 때 노드 ID 충돌 여부 확인\n"
            "3. 프리프로세서에서 경계 조건 시각화 — 의도한 노드에 SPC가 적용되는지 확인"
        ),
    ),
    30364: ErrorInfo(
        code=30364,
        severity=Severity.WARNING,
        title="Rigid body: extra node not found",
        description=(
            "Warning 30364: *CONSTRAINED_EXTRA_NODES_SET 또는 유사 카드에서 "
            "참조한 노드가 모델에 없거나 이미 다른 rigid body에 속해 있습니다. "
            "rigid body에 extra node를 추가하면 그 노드는 rigid body의 운동에 따라 "
            "구속되는데, 잘못된 참조는 구속이 적용되지 않습니다."
        ),
        recommendation=(
            "1. *CONSTRAINED_EXTRA_NODES에서 NID/NSID 확인\n"
            "2. 동일 노드가 여러 rigid body에 중복 정의되지 않았는지 확인\n"
            "3. 파트 ID와 노드 ID가 같은 단위계/ID 범위를 사용하는지 확인"
        ),
    ),

    # ===== Curve/Table Warnings (21xxx) — 새로 추가 =====
    21287: ErrorInfo(
        code=21287,
        severity=Severity.WARNING,
        title="Curve: ordinate value out of expected range",
        description=(
            "Warning 21287: 재료/접촉 커브의 종좌표(y값)가 예상 범위를 벗어났습니다. "
            "LS-DYNA는 특정 커브 타입(응력-변형률, 하중-변위 등)에서 "
            "물리적으로 합리적인 값 범위를 내부적으로 점검합니다. "
            "범위를 벗어난 값은 재료 비물리적 거동이나 수치 불안정의 원인이 됩니다."
        ),
        recommendation=(
            "1. 커브 단위 확인 — 응력은 [Pa] 또는 [MPa], 변형률은 무차원인지 확인. "
            "단위계 혼용으로 발생하는 경우가 많음\n"
            "2. 커브 형상 점검 — 재료 소프트닝 구간에서 음의 기울기(negative stiffness)가 "
            "있으면 수치 불안정 유발 가능\n"
            "3. *DEFINE_CURVE 포인트 순서 확인 — 종좌표가 단조 증가인지 확인"
        ),
    ),

    # ===== Material Warnings (20xxx) — 새로 추가 =====
    20661: ErrorInfo(
        code=20661,
        severity=Severity.WARNING,
        title="Material: negative pressure detected (tension cutoff)",
        description=(
            "Warning 20661: 재료에서 음의 압력(인장 상태)이 감지되어 tension cutoff가 적용되었습니다. "
            "유체, 발포체, 고무류 재료에서 인장 상태에서의 압력이 cutoff 값을 초과하면 "
            "LS-DYNA가 압력을 cutoff 값으로 제한합니다. "
            "이는 공동화(cavitation) 방지나 재료 물성의 한계를 표현합니다."
        ),
        recommendation=(
            "1. Tension cutoff 값 확인 — *EOS_* 또는 *MAT_*에서 PMIN/TENSCUT 파라미터 검토. "
            "너무 작은 cutoff는 비물리적 에너지 해방을 일으킴\n"
            "2. 음의 압력 영역 시각화 — d3plot에서 pressure 필드를 확인하여 "
            "cavitation 위치 파악\n"
            "3. ALE/EFG 사용 — 극단적 변형에서 인장 불안정이 지속되면 "
            "mesh-free 방법 고려"
        ),
    ),
    20471: ErrorInfo(
        code=20471,
        severity=Severity.WARNING,
        title="Material: strain rate exceeds tabulated range",
        description=(
            "Warning 20471: 현재 변형률 속도(strain rate)가 재료 커브에 정의된 최대 범위를 초과했습니다. "
            "변형률 속도 의존 재료(*MAT_024 등)는 다양한 변형률 속도에서의 "
            "응력-변형률 커브를 테이블로 정의하는데, 실제 변형률 속도가 이 범위를 "
            "벗어나면 외삽(extrapolation)이 적용되어 결과가 부정확해집니다."
        ),
        recommendation=(
            "1. 변형률 속도 커브 범위 확장 — 시뮬레이션에서 발생하는 최대 변형률 속도를 "
            "사전 분석하고, 해당 범위까지 재료 데이터 확장\n"
            "2. 로그 스케일 커브 — 변형률 속도가 10^0~10^4/s 범위라면 "
            "로그 스케일로 커브 정의 권장\n"
            "3. Cowper-Symonds 모델 사용 — 고속 충격에서 해석적 변형률 속도 모델로 "
            "외삽 문제 회피"
        ),
    ),

    # ===== Material/Section Errors (20xxx) — 새로 추가 =====
    20385: ErrorInfo(
        code=20385,
        severity=Severity.CRITICAL,
        title="Material type incompatible with element formulation",
        description=(
            "Error 20385: 파트에 지정된 재료 타입이 해당 요소 공식(element formulation)과 "
            "호환되지 않습니다. 예를 들어, thick shell (formulation 2)에 지원되지 않는 "
            "재료 모델(*MAT_063 등)을 적용하면 이 오류가 발생합니다. "
            "LS-DYNA의 각 요소 공식은 특정 재료 모델만 지원하며, "
            "미지원 조합은 초기화 단계에서 시뮬레이션을 중단시킵니다."
        ),
        recommendation=(
            "1. 재료-요소 호환성 확인 — LS-DYNA 매뉴얼에서 해당 MAT 타입이 "
            "지원하는 ELFORM 목록 확인. 예: *MAT_063(Crushable Foam)은 "
            "solid 전용이며 thick shell에서 사용 불가\n"
            "2. 요소 공식 변경 — *SECTION_TSHELL의 ELFORM을 재료가 지원하는 형식으로 변경\n"
            "3. 재료 모델 변경 — thick shell 지원 재료(*MAT_024, *MAT_058 등)로 교체"
        ),
    ),
    20430: ErrorInfo(
        code=20430,
        severity=Severity.CRITICAL,
        title="Hardening modulus exceeds Young's modulus (MAT_024)",
        description=(
            "Error 20430: *MAT_PIECEWISE_LINEAR_PLASTICITY(MAT_024)에서 경화 계수(ETAN)가 "
            "영 계수(E)보다 크거나 같습니다. 탄소성 재료에서 hardening modulus는 "
            "항복 후 접선 강성(tangent modulus)으로, 물리적으로 E보다 작아야 합니다. "
            "H = E × ETAN / (E - ETAN) 관계에서 ETAN ≥ E이면 H가 무한대 또는 음수가 되어 "
            "수치적으로 의미가 없습니다. 이는 재료 파라미터 입력 오류(단위 불일치)가 "
            "가장 흔한 원인입니다."
        ),
        recommendation=(
            "1. ETAN 값 확인 — ETAN은 항복 후 접선 기울기로, 반드시 E보다 작아야 함. "
            "일반적으로 ETAN = 0.001×E ~ 0.1×E 범위\n"
            "2. 단위계 확인 — E와 ETAN이 동일한 단위(Pa, MPa 등)인지 확인. "
            "mm-ton-s 단위에서 E=210000 MPa, ETAN=1000 MPa 등\n"
            "3. 응력-변형률 커브 사용 — ETAN 대신 *DEFINE_CURVE로 경화 곡선을 직접 정의하면 "
            "더 정확한 비선형 거동 표현 가능 (LCSS 필드 활용)"
        ),
    ),

    # ===== Contact Errors (40xxx) — 새로 추가 =====
    40024: ErrorInfo(
        code=40024,
        severity=Severity.CRITICAL,
        title="Contact: interface energy goes negative (contact instability)",
        description=(
            "Error 40024: 접촉 인터페이스 에너지가 음수로 전환되었습니다. "
            "접촉 에너지는 물리적으로 항상 비음수여야 하며, 음수 접촉 에너지는 "
            "접촉 알고리즘의 수치적 불안정을 나타냅니다. "
            "원인: 과도한 초기 관통, penalty stiffness가 너무 커 비물리적 반발력 발생, "
            "또는 접촉 타입과 메시 형태의 불일치."
        ),
        recommendation=(
            "1. Penalty stiffness 감소 — *CONTROL_CONTACT의 SLSFAC를 0.01~0.05로 낮춤. "
            "과도한 penalty가 에너지 발산의 주원인\n"
            "2. 초기 관통 제거 — IGNORE=2로 자동 초기 관통 해소\n"
            "3. SOFT=1(segment-based contact) 사용 — 양측 강성을 고려한 "
            "더 안정적인 penalty 계산. 에너지 보존에 유리\n"
            "4. 타임스텝 감소 — 충격 단계에서 TSSFAC를 줄여 접촉력 급증 방지"
        ),
    ),

    # ===== Contact Warnings (41xxx) — 새로 추가 =====
    41234: ErrorInfo(
        code=41234,
        severity=Severity.WARNING,
        title="Contact: rigid body contact slave node warning",
        description=(
            "Warning 41234: Rigid body와 deformable body 간 접촉에서 slave 노드 처리 경고입니다. "
            "Rigid body는 모든 노드가 강체 운동하므로 접촉 penalty가 rigid body 전체에 "
            "균등하게 분배됩니다. slave 노드 수가 너무 많거나 적으면 "
            "접촉력 분배가 비균형해질 수 있습니다."
        ),
        recommendation=(
            "1. Contact 타입 확인 — *CONTACT_AUTOMATIC_*가 rigid body에 적합한지 확인\n"
            "2. RBDOK 파라미터 설정 — rigid body 접촉에서 RBDOK=1로 설정하여 "
            "rigid body slave 노드 처리 방식 최적화\n"
            "3. Master/Slave 방향 확인 — rigid body가 master, deformable이 slave가 되도록 설정"
        ),
    ),
    41213: ErrorInfo(
        code=41213,
        severity=Severity.WARNING,
        title="Contact: self-contact node removed (penetration too deep)",
        description=(
            "Warning 41213: Self-contact에서 과도한 관통으로 노드가 접촉 처리에서 제거되었습니다. "
            "Shell 또는 solid 자기 접촉(*CONTACT_SINGLE_SURFACE)에서 "
            "관통 깊이가 임계값을 초과하면 해당 노드를 제거하여 "
            "더 이상의 수치 불안정을 방지합니다."
        ),
        recommendation=(
            "1. Automatic single surface contact 사용 — *CONTACT_AUTOMATIC_SINGLE_SURFACE는 "
            "자기 접촉에 더 robust한 알고리즘 사용\n"
            "2. 메시 크기 증가 — 접촉 문제가 발생한 영역의 요소를 세분화하여 관통 방지\n"
            "3. Thickness scaling — *CONTACT의 SST/MST 파라미터로 접촉 두께 조정"
        ),
    ),
    40515: ErrorInfo(
        code=40515,
        severity=Severity.WARNING,
        title="Contact: shell thickness offset causes initial penetration",
        description=(
            "Warning 40515: Shell 요소의 두께 오프셋으로 인해 초기 관통이 발생했습니다. "
            "Shell 요소는 중립면을 기준으로 두께 방향으로 오프셋을 적용하는데, "
            "이 오프셋이 인접 파트와 겹치면 시작부터 접촉 관통이 발생합니다."
        ),
        recommendation=(
            "1. Shell offset 옵션 확인 — *SECTION_SHELL의 OFFST 파라미터 또는 "
            "*CONTACT의 SSTHK/MSTHK로 두께 고려 방식 조정\n"
            "2. 모델 형상 수정 — 인접 파트 간 초기 간격을 shell 두께/2 이상으로 확보\n"
            "3. IGNORE=2 사용 — 초기 관통을 자동으로 해소하는 옵션 적용"
        ),
    ),

    # ===== License / System =====
    90001: ErrorInfo(
        code=90001,
        severity=Severity.CRITICAL,
        title="License error",
        description=(
            "LS-DYNA 라이선스를 획득할 수 없거나 만료되었습니다. "
            "LS-DYNA는 실행 시 라이선스 서버(FlexLM 또는 LSTC 자체 서버)에서 "
            "라이선스를 확인하며, 실행 중에도 주기적으로 검증합니다. "
            "라이선스 실패는 서버 연결 불가, 동시 사용자 초과, "
            "라이선스 파일 만료, 또는 환경 변수 미설정이 원인입니다."
        ),
        recommendation=(
            "1. 환경 변수 확인 — LSTC_LICENSE_SERVER 또는 LSTC_FILE이 "
            "올바르게 설정되어 있는지 확인\n"
            "2. 라이선스 서버 상태 확인 — lstc_qrun 명령으로 "
            "현재 라이선스 사용 현황 조회\n"
            "3. 네트워크 연결 — 라이선스 서버의 포트(기본 31010)가 "
            "방화벽에 의해 차단되어 있지 않은지 확인\n"
            "4. 라이선스 관리자에게 문의 — 동시 사용자 초과 또는 "
            "만료 여부 확인"
        ),
    ),
}


def lookup_error(code: int) -> ErrorInfo:
    """Look up a warning/error code. Returns generic info if code is unknown."""
    if code in ERROR_DATABASE:
        return ERROR_DATABASE[code]

    # Determine severity from code range
    if code < 20000:
        severity = Severity.CRITICAL
    elif code < 40000:
        severity = Severity.WARNING
    elif code < 50000:
        severity = Severity.WARNING
    elif code < 60000:
        severity = Severity.WARNING
    else:
        severity = Severity.INFO

    return ErrorInfo(
        code=code,
        severity=severity,
        title=f"Code {code}",
        description=f"Warning/Error code {code} (not in built-in database).",
        recommendation=(
            "Consult LS-DYNA documentation or LSTC support resources "
            f"for details on code {code}."
        ),
    )
