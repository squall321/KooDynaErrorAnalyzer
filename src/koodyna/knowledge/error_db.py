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
