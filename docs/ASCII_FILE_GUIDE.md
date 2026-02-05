# LS-DYNA ASCII 출력 파일 가이드

KooDynaErrorAnalyzer가 파싱하는 파일과 추가 분석 가능한 파일들의 정보를 정리합니다.

## 현재 파싱되는 주요 파일 (우선순위: 높음)

### 1. d3hsp (High Speed Printer Output)
**상태**: ✅ 완전 파싱
**내용**:
- Termination status (NORMAL/ERROR)
- Model statistics (nodes, elements, parts, contacts)
- Timestep control information
- Part definitions and properties
- Contact interface definitions
- Mass properties and inertia tensors
- Warning/error messages

**진단 활용**:
- 시뮬레이션 성공/실패 판단
- Timestep 제어 파트 식별
- 모델 구조 이해
- 경고/에러 패턴 분석

### 2. glstat (Global Statistics)
**상태**: ✅ 완전 파싱
**내용**:
- 시간별 에너지 변화 (kinetic, internal, total)
- Energy ratio (에너지 보존 검증)
- Timestep 변화
- 전체 시스템 momentum

**진단 활용**:
- 에너지 불안정성 감지 (ratio > 4.0 → CRITICAL)
- Timestep collapse 감지 (dt < 1e-11)
- 에너지 비정상 패턴 (음수 internal energy)

### 3. status.out (Simulation Status)
**상태**: ✅ 완전 파싱
**내용**:
- Cycle 진행률
- CPU time distribution (contact %, deformation %, etc.)
- 실시간 성능 메트릭

**진단 활용**:
- Contact CPU 비율 확인 (>40% → 접촉 최적화 필요)
- 성능 병목 식별

### 4. matsum (Material Summary)
**상태**: ✅ 완전 파싱
**내용**:
- 파트별/재질별 에너지 시계열 (internal, kinetic, hourglass)
- Eroded energy (파손 요소 에너지)
- Momentum (x, y, z)
- Rigid body velocity

**진단 활용**:
- 특정 파트의 에너지 이상 감지
- Hourglass energy 과다 파트 식별
- Erosion 발생 파트 추적

### 5. messag (Message File)
**상태**: ✅ 부분 파싱
**내용**:
- Negative volume 발생 요소 번호
- Constraint matrix NaN 오류
- Shooting nodes 경고
- 기타 runtime warning/error

**진단 활용**:
- 실패 원인 요소 식별
- k/dyn 파일과 매칭하여 문제 파트 특정

### 6. mes0000, mes0001, ... (MPP Message Files)
**상태**: ✅ 부분 파싱
**내용**:
- 각 프로세서별 message 내용 (MPP 병렬 계산 시)

**진단 활용**:
- MPP 실행 시 프로세서별 오류 추적

---

## 추가 분석 가능 파일 (우선순위: 중간)

### 7. elout (Element Time History)
**상태**: ❌ 미구현
**내용**:
- 특정 요소의 시간별 응력/변형률 (σ, ε)
- Effective plastic strain
- Damage/failure indicators (재료 모델에 따라)
- Element energy

**진단 가능 정보**:
- **요소별 응력 이력**: 파손 요소의 응력 집중 패턴 분석
- **Plastic strain 누적**: 영구 변형 발생 요소 추적
- **Failure criteria 도달 시점**: 파손 시작 시간 정확히 파악
- **응력 진동**: 수치 불안정성 감지 (고주파 oscillation)

**활용 시나리오**:
- Negative volume 발생 요소의 응력 이력 확인 → 과도한 압축/인장 확인
- 높은 plastic strain 요소 → 메시 리파인 필요 영역 식별

**파싱 난이도**: 중간 (ASCII 형식, 고정 컬럼, 여러 섹션)

---

### 8. nodout (Nodal Time History)
**상태**: ❌ 미구현
**내용**:
- 특정 노드의 변위 (dx, dy, dz)
- 속도 (vx, vy, vz)
- 가속도 (ax, ay, az)

**진단 가능 정보**:
- **Shooting nodes 추적**: 비정상적으로 큰 속도/변위 (|v| > 1000 m/s)
- **Constraint 검증**: 경계조건 노드의 변위가 0인지 확인
- **진동 패턴**: 고주파 진동 발생 노드 (수치 불안정)
- **충돌 검증**: 접촉 전후 속도 변화 확인

**활용 시나리오**:
- Constraint matrix NaN 오류 발생 시 → 관련 노드의 속도 이력 확인
- 에너지 폭주 시 → 최대 속도 노드 추적하여 원인 파악

**파싱 난이도**: 중간

---

### 9. bndout (Boundary Force Output)
**상태**: ❌ 미구현
**내용**:
- 경계조건 노드의 반력 (Fx, Fy, Fz, Mx, My, Mz)
- 시간별 반력 변화

**진단 가능 정보**:
- **Load path 검증**: 하중 전달 경로가 설계 의도와 일치하는지
- **Constraint 적절성**: 과도한 반력 → 경계조건 재검토 필요
- **충격 하중 크기**: 충돌 시 반력 peak 값

**활용 시나리오**:
- Drop test 시 바닥 반력 → 충격 강도 정량화
- 과도한 반력 발생 노드 → 구속 조건 완화 필요 판단

**파싱 난이도**: 중간

---

### 10. rcforc / secforc (Cross-Section Forces)
**상태**: ❌ 미구현
**내용**:
- 단면에서의 내력 (Fx, Fy, Fz, Mx, My, Mz)
- 단면 적분 응력

**진단 가능 정보**:
- **구조 부재 내력**: 보/기둥의 내력 이력
- **하중 분배**: 여러 단면 간 하중 분배 확인
- **좌굴/파손 전조**: 내력 급증 → 좌굴 시작점 감지

**활용 시나리오**:
- 복합 구조물에서 특정 부재가 과하중을 받는지 확인
- 설계 하중과 실제 내력 비교

**파싱 난이도**: 중간

---

### 11. nodfor (Nodal Force Output)
**상태**: ❌ 미구현
**내용**:
- 각 노드에 작용하는 힘 (contact, applied load, internal force)

**진단 가능 정보**:
- **Contact force 분포**: 접촉면에서 힘 집중 영역
- **Unbalanced force**: 수치 오차로 인한 불균형 힘
- **하중 이상**: 예상보다 큰 힘이 작용하는 노드

**활용 시나리오**:
- Contact penalty가 너무 큰지 확인 (contact force spike)
- 특정 노드에 과도한 힘 집중 → 메시 개선

**파싱 난이도**: 중간~높음 (복잡한 힘 분해)

---

## 추가 분석 가능 파일 (우선순위: 낮음)

### 12. rcforc (Resultant Contact Force)
**상태**: ❌ 미구현
**내용**:
- Contact interface별 합력

**진단 가능 정보**:
- 접촉면별 총 힘 크기
- 접촉 시작/종료 시점

**활용 시나리오**: 다수 접촉면 중 주요 접촉 식별

---

### 13. deforc (Discrete Element Force)
**상태**: ❌ 미구현
**내용**:
- Spring/damper 요소의 힘

---

### 14. swforc (Spot Weld Force)
**상태**: ❌ 미구현
**내용**:
- 스폿 용접 요소의 힘

---

### 15. sbtout (Seatbelt Output)
**상태**: ❌ 미구현
**내용**:
- 안전벨트 슬립/장력

---

### 16. jntforc (Joint Force Output)
**상태**: ❌ 미구현
**내용**:
- Joint element 힘/모멘트

---

### 17. abstat (Airbag Statistics)
**상태**: ❌ 미구현
**내용**:
- 에어백 압력/체적

---

## 구현 우선순위 제안

### Phase 1 (즉시 구현 추천)
1. **elout 파서**: 요소 응력/변형률 → 파손 원인 정량적 분석
2. **nodout 파서**: Shooting nodes 추적 → Constraint 오류 진단 개선

### Phase 2 (차기 구현)
3. **bndout 파서**: 반력 분석 → 경계조건 검증
4. **rcforc/secforc 파서**: 단면력 분석 → 구조 안전성 평가

### Phase 3 (선택적)
5. **nodfor 파서**: 노드 힘 분포 → 상세 접촉 분석
6. 나머지 특수 출력 파일들 (용도별 선택적 구현)

---

## 구현 시 고려사항

### 파일 크기 이슈
- elout, nodout: 시간 스텝 × 요소/노드 수 → **매우 큰 파일** (수 GB 가능)
- 전체 파싱 대신 **스트리밍 파싱** 필요
- 특정 시간 구간만 파싱하는 옵션 제공

### 선택적 출력
- 이 파일들은 *DATABASE_* 키워드로 활성화해야 생성됨
- 파일이 없으면 gracefully skip

### 진단 연계
- elout → failure_analysis.py에서 negative volume 요소의 응력 이력 표시
- nodout → diagnostics.py에서 shooting nodes 목록 출력
- bndout → 반력 이상 시 경고 생성

---

## 요약

**현재 파싱 가능**: d3hsp, glstat, status.out, matsum, messag (핵심 진단 커버 ~80%)

**추가 구현 시 얻을 수 있는 것**:
- **elout**: 요소별 응력/변형률 → 파손 메커니즘 이해 (정량적)
- **nodout**: Shooting nodes 추적 → Constraint 오류 명확화
- **bndout**: 반력 분석 → 경계조건 적절성 검증
- **rcforc/secforc**: 단면력 → 구조 부재 안전성
- **nodfor**: 노드 힘 → 접촉 힘 분포 상세 분석

**파싱 난이도 vs 진단 가치**:
- elout: 중간 난이도, **높은 가치** (요소 파손 직접 분석)
- nodout: 중간 난이도, **높은 가치** (shooting nodes 추적)
- bndout: 중간 난이도, 중간 가치 (구조 검증용)
- 나머지: 낮은 가치 (특수 목적)

**권장 다음 단계**: elout, nodout 파서 구현 → 진단 시스템을 정량적 레벨로 향상
