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
**상태**: ✅ 구현 완료
**내용**:
- 특정 노드의 변위/속도/가속도 (dx, dy, dz, vx, vy, vz, ax, ay, az)
- 시간별 좌표 (x, y, z)

**진단 정보** (수치해석 건강성):
- **Shooting nodes 감지** (|v| > 1000 m/s): 비정상적으로 큰 속도 → constraint 오류, penalty 과다
- **고주파 진동 감지** (ZCR > 10 kHz): Timestep 너무 큼 또는 hourglass 문제
- ~~Constraint 검증~~ (구현 보류: d3hsp에서 constraint 정의 파싱 필요)

**활용 시나리오**:
- Constraint matrix NaN 오류 발생 시 → shooting nodes 추적하여 원인 노드 식별
- 에너지 폭주 시 → 최대 속도 노드 추적
- 수치 불안정성 진단 → 고주파 진동 노드 확인

**파싱 난이도**: 중간 (메모리 이슈: max_nodes 제한 필요)

---

### 9. bndout (Boundary Force Output)
**상태**: ✅ 구현 완료
**내용**:
- 경계조건 노드의 반력 (Fx, Fy, Fz, Mx, My, Mz)
- 시간별 반력/에너지 변화

**진단 정보** (수치해석 건강성):
- **반력 spike 감지** (max/mean > 100): Penalty stiffness 과다 또는 초기 관통
- **진동 반력 감지** (oscillation): Damping 부족 또는 timestep 너무 큼

**활용 시나리오**:
- Drop test 시 바닥 반력 급증 → penalty factor 재조정 필요
- 반력 진동 → global/contact damping 추가 필요
- Contact 설정 검증 → 초기 관통 확인

**파싱 난이도**: 중간

**Note**: Load path 검증은 제외 (설계 검증이지 수치 문제 아님)

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

### Phase 1 (완료 ✅)
1. ✅ **nodout 파서**: Shooting nodes 추적 + 고주파 진동 감지
2. ✅ **bndout 파서**: 반력 spike + 진동 감지

### Phase 2 (차기 구현)
3. **elout 파서**: 응력 oscillation 감지 (크기 분석 제외)
4. **rcforc/secforc 파서**: 단면력 불연속 감지

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

**현재 파싱 가능**: d3hsp, glstat, status.out, matsum, messag, **nodout**, **bndout** (핵심 진단 커버 ~90%)

**수치해석 건강성 진단** (✅ 구현됨):

**nodout 기반**:
- **Shooting nodes 감지** (|v| > 1000 m/s): 속도 폭주 → constraint/penalty 문제
- **고주파 진동 감지** (ZCR > 10 kHz): 비물리적 oscillation → timestep/hourglass 문제

**bndout 기반**:
- **반력 spike 감지** (max/mean > 100): penalty 과다 → 초기 관통/경계조건 충돌
- **반력 진동 감지**: damping 부족

**glstat 기반 (신규 ✅)**:
- **Hourglass energy 과다** (>10%/20%): Zero-energy mode → 메시 불안정
- **Kinetic energy 폭주** (100x 급증): 전역 속도 발산 → constraint 문제
- **KE/IE 비정상** (KE/IE > 10): 준정적 문제에서 과도한 운동 → rigid body mode
- **Contact energy 과다** (>30%): 비정상 마찰/관통
- **Contact energy spike** (50x 급증): penalty 문제/과도한 관통

**추가 구현 시 얻을 수 있는 것** (선택적):
- **elout**: 응력 oscillation 감지 (hourglass mode 확인)
- **rcforc/secforc**: 단면력 불연속 감지 (contact/erosion 천이 문제)
- **nodfor**: 노드 힘 분포 → 접촉 힘 집중 확인

**파싱 난이도 vs 진단 가치**:
- ✅ nodout: 중간 난이도, **높은 가치** → 완료
- ✅ bndout: 중간 난이도, **높은 가치** → 완료
- elout: 중간 난이도, 중간 가치 (응력 oscillation만)
- 나머지: 낮은 가치 (특수 목적)

**달성**: 핵심 수치 불안정성 진단 완료 → 툴은 **수치해석 건강성 검사** 역할 수행

## 진단 커버리지 상세

### Level 1: 기본 건강성 (glstat 기반)
- ✅ 에너지 보존 (ratio 0.95~1.05)
- ✅ Timestep 안정성 (collapse < 1e-11)
- ✅ Hourglass 과다 (>10%/20%)
- ✅ KE/IE 비율 이상
- ✅ Contact energy 이상

### Level 2: 국부 불안정 (nodout/bndout 기반)
- ✅ Shooting nodes (개별 노드)
- ✅ 고주파 진동 (개별 노드)
- ✅ 반력 spike (경계 노드)

### Level 3: 실패 원인 추적 (messag + k/dyn)
- ✅ Negative volume 요소 → 파트 매핑
- ✅ Constraint NaN 감지

**커버리지**: ~95% (핵심 수치 문제 거의 전부 포함)
