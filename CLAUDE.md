# PHAROS — 프로젝트 규약 문서

## 프로젝트 정의

**PHAROS** (Priority · Hazard · Attention · Reorganizing · Overload · Suppression)

소방관 화재 진입 시 시각 정보 과잉으로 인한 인지 부하를 측정하고,
시선 엔트로피가 낮아지는 방향으로 위험·과제를 우선순위 리스팅하여 HUD로 시각화하는 연구 프로토타입.

---

## 핵심 도메인 용어 사전

| 용어 | 정의 |
|------|------|
| **stationary gaze entropy (Hs)** | fixation 좌표를 격자 빈(AOI)으로 이산화한 뒤 각 빈의 점유 비율 p(i)로 계산한 Shannon 엔트로피. `Hs = -Σ p(i) log2 p(i)`. 시선이 넓게 흩어질수록 높다. |
| **transition gaze entropy (Ht)** | fixation 전이를 1차 Markov 행렬로 모델링한 조건부 엔트로피. `Ht = -Σ_i p(i) Σ_j p(j|i) log2 p(j|i)` (자기전이 제외). 시선 경로가 예측 불가능할수록 높다. |
| **cognitive load** | 동공 직경 시계열에서 추출한 부하 지표. baseline 대비 % 변화, peak dilation, peak latency를 0~1로 정규화·합산한 cognitive_load_index로 표현. |
| **STOM** | 항목 점수화 4-파라미터 모델: **S**alience(지각 현저성) · **T**ask relevance (priority, 생명 직결도) · **O**bserver expectancy(정보 기대 확률) · **M**otor cost (difficulty, 처리 부하). SEEV 모델의 화재 도메인 변형. |
| **Tyndall scattering** | 수십 nm 크기의 콜로이드성 그을음 입자에 의한 빛 산란 현상. 산란 강도 ∝ 입자 농도. 이 강도를 광센서로 읽어 연기 농도(0~1)와 추정 가시거리로 변환. |
| **fixation** | 시선이 특정 점 근방(< 2°)에 100ms 이상 머무는 상태. 짧은 saccade(고속 이동) 사이 정적 응시 구간. |
| **AOI (Area of Interest)** | 시선 이산화 단위. 화면을 `bin_size × bin_size` 픽셀 격자로 나눈 각 셀. 엔트로피 계산의 기본 상태 단위. |
| **saccade** | 한 fixation에서 다른 fixation으로 이동하는 고속 안구 운동. 전이 엔트로피 계산 시 전이 이벤트로 취급. |
| **HudState** | 파이프라인이 매 틱 출력하는 직렬화 가능 상태 객체. 활성 항목, 우선순위 큐, 부하 지표, 가시거리, 타임스탬프를 포함. HUD와의 JSON 계약. |

---

## Definition of Done

모든 단계가 완료로 인정받으려면 아래를 **명령 출력으로 증명**해야 한다.

1. **테스트 존재**: 모든 공개 함수에 대해 최소 1개 이상의 단위 테스트.
2. **ruff 통과**: `ruff check src/ tests/` exit 0.
3. **mypy 통과**: `mypy src/` exit 0.
4. **pytest 통과**: `pytest -q` exit 0, 새로운 경계 케이스 포함.
5. **출력 첨부**: "통과했습니다" 단언 불가. 실제 명령 출력을 그대로 제시.

---

## 코딩 규약

- **작은 커밋**: 기능 단위로 커밋. 여러 기능을 한 커밋에 묶지 말 것.
- **함수 단위 명확**: 한 함수는 한 가지 일. 이름으로 의도가 전달되어야 함.
- **하드웨어는 어댑터 뒤로**: 실제 아이트래커·광센서 코드는 추상 인터페이스 구현체로만 존재. 코어 로직은 인터페이스에만 의존.
- **주석은 WHY만**: 코드가 무엇을 하는지는 이름으로 전달. "왜 이렇게 했는지"만 주석으로 남김.
- **타입힌트 필수**: 모든 공개 함수에 입력·반환 타입 명시.
- **docstring 필수**: 공개 함수에 한 줄 이상 설명.
- **매직 넘버 금지**: 상수는 이름을 붙여 명시.

---

## 모듈 구조

```
src/pharos/
├── entropy/    # Hs(stationary), Ht(transition) 계산
├── cogload/    # 동공 → cognitive_load_index
├── sensing/    # 산란 강도 → 연기 농도 → 가시거리
├── priority/   # STOM 점수화 + PriorityQueueEngine
├── pipeline/   # PharosPipeline.tick() 오케스트레이터
└── io/         # GazeSource, PupilSource, SensingSource 어댑터 인터페이스
sim/            # 합성 장면·시선·동공·산란 시뮬레이터
eval/           # 2×2 실험 러너 + 통계 + 리포트
hud/            # 웹 기반 HUD 프론트엔드
tests/          # 단위·통합 테스트
```

---

## 진척 기록 규칙

- 각 단계(STAGE) 완료 시 `docs/PROGRESS.md`를 갱신한다.
- 형식: 날짜, 단계 번호, 산출물, 검증 게이트 통과 여부, 주요 결정 사항.
- 미해결 항목은 "Known limitations"에 명시.
