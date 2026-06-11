# PHAROS — 단계별 진척 기록

## STAGE 0 — 하네스 셋업 (2026-06-11)

**산출물**
- `src/pharos/` src 레이아웃 + 6개 서브패키지 골격
- `pyproject.toml` (ruff, mypy, pytest, hatchling)
- `CLAUDE.md` (용어 사전, Definition of Done, 코딩 규약)
- `.pre-commit-config.yaml`
- `.claude/commands/verify.md` (/verify 슬래시 커맨드)
- `tests/test_placeholder.py`

**검증 게이트**
- [x] ruff check 통과
- [x] mypy 통과
- [x] pytest 통과 (placeholder 1건)
- [x] CLAUDE.md 용어 사전·DoD 존재
- [x] /verify 커맨드 동작

**주요 결정 사항**
- 빌드 백엔드: hatchling (pyproject.toml 표준)
- mypy strict 모드 활성화 (모든 단계에서 타입 안전성 보장)
- ruff가 lint + format 모두 담당 (black 별도 불필요)

---

## STAGE 1 — 시선 엔트로피 코어 (2026-06-11)

**산출물**
- `src/pharos/entropy/core.py`: `stationary_entropy`, `transition_entropy`, `_fixations_to_bin_ids`
- `src/pharos/entropy/__init__.py`: public API re-export
- `tests/test_entropy.py`: 8개 경계 케이스 테스트

**검증 게이트**
- [x] ruff check 통과
- [x] mypy strict 통과 (8 source files, 0 issues)
- [x] pytest 통과 (9 passed, 0 warnings)
- [x] 경계 케이스 실제 수치:
  - Hs (단일 빈): 0.0
  - Hs normalized (12-빈 균등): 1.000000
  - Hs normalized (랜덤 300점): 0.9946
  - Ht (A→B→A→B 결정론적): 0.0
  - Ht (랜덤 4-빈): 1.5264 bits (Hmax=1.5850)
  - Ht normalized (랜덤 300점): 0.9110

**주요 결정 사항**
- Hs 정규화: `Hmax = log2(total_possible_bins)` — 화면 전체 기준 최대 엔트로피
- Ht 정규화: `Hmax = log2(n_occupied_states - 1)` — 2 상태는 항상 결정론적이므로 0.0 반환
- 자기전이 제거: `mask = src != dst` 로 연속 동일-빈 전이를 전이 행렬에서 제외
- `np.bincount` + reshape 으로 전이 행렬 구성 (np.add.at 대신 타입 안전)
- `np.errstate(divide="ignore")` 로 np.where 양쪽 평가 시 log(0) 경고 억제

---

---

## STAGE 2 — 동공 기반 인지 부하 추정기 (2026-06-11)

**산출물**
- `src/pharos/cogload/core.py`: `preprocess_pupil`, `extract_features`, `cognitive_load_index`, `PupilFeatures`, `LoadWeights`
- `src/pharos/cogload/__init__.py`: public API re-export
- `tests/test_cogload.py`: 8개 합성 신호 테스트

**검증 게이트**
- [x] ruff check 통과
- [x] mypy strict 통과 (9 source files, 0 issues)
- [x] pytest 통과 (17 passed, 0 warnings)
- [x] 합성 신호별 cognitive_load_index 실제 수치:

| 조건 | pct_change | peak_dilation | peak_latency | CLI |
|------|-----------|--------------|-------------|-----|
| 평탄 (0% 변화) | 0.0% | 0.000 | 0.00s | **0.0000** |
| 쉬움 (10% 확장) | 10.0% | 0.400 | 1.95s | **0.2979** |
| 보통 (30% 확장) | 30.0% | 1.200 | 1.95s | **0.6779** |
| 어려움 (50% 확장) | 50.0% | 2.000 | 1.95s | **0.8779** |
| blink 포함 (전처리 후) | 50.0% | 2.000 | 1.95s | **0.8779** |

**주요 결정 사항**
- blink 탐지: `diameter <= 0 OR < 0.5 × global_median` → `np.interp`로 선형 보간
- 특징 통계: baseline/task 모두 median 기반 (단일 극단값에 강건)
- 가중치 기본값: w_pct=0.50, w_peak=0.30, w_latency=0.20 (합=1.0)
- 정규화 범위 기본값: 50%, 1mm, 5s (LoadWeights에 문서화)
- CLI = weighted_sum / w_sum → 가중치 합계 무관하게 [0,1] 보장

---

---

## STAGE 3 — 틴들 센싱 모듈 (2026-06-11)

**산출물**
- `src/pharos/sensing/core.py`: `ScatteringSample`, `CalibrationParams`, `SensingSource`(ABC), `ReplaySensingSource`, `scattering_to_density`, `density_to_visibility`
- `src/pharos/sensing/__init__.py`: public API re-export
- `tests/test_sensing.py`: 14개 테스트 (단조성 2종, 범위, 어댑터 교체)

**검증 게이트**
- [x] ruff check 통과
- [x] mypy strict 통과 (10 source files, 0 issues)
- [x] pytest 통과 (31 passed)
- [x] 산란값 시퀀스 → 농도·가시거리 실제 출력:

| scatter | density | visibility |
|---------|---------|-----------|
| 0.00 | 0.000 | 30.00 m |
| 0.11 | 0.111 | 21.50 m |
| 0.33 | 0.333 | 11.04 m |
| 0.56 | 0.556 | 5.67 m |
| 0.78 | 0.778 | 2.91 m |
| 1.00 | 1.000 | 1.49 m |

**주요 결정 사항**
- `SensingSource` ABC: `read() → ScatteringSample` + `has_data() → bool` (하드웨어 어댑터 계약)
- `ReplaySensingSource`: 소진 후 `read()` → `StopIteration`; 파이프라인은 `has_data()` 확인 후 호출
- 보정 모델: density = linear clip, visibility = Koschmieder 지수 감쇠 (V_max × e^{−kd})
- `zip(strict=False)` — ruff B905 준수 (STAGE 1·2 테스트에도 향후 적용)

---

---

## STAGE 4 — STOM 우선순위 점수화 + 큐 엔진 (2026-06-11)

**산출물**
- `src/pharos/priority/core.py`: `HazardKind`, `Hazard`, `ScoringContext`, `ScoringWeights`, `score()`, `PriorityQueueEngine`
- `src/pharos/priority/__init__.py`: public API re-export
- `tests/test_priority.py`: 11개 테스트 (점수 단위, 동적 재정렬, top-k 직렬화)

**검증 게이트**
- [x] ruff check 통과
- [x] mypy strict 통과 (11 source files, 0 issues)
- [x] pytest 통과 (42 passed)
- [x] 시나리오별 큐 스냅샷:

| hazard | BEFORE smoke | AFTER smoke(victim=0.99) |
|--------|-------------|--------------------------|
| victim | **0.5750** (1위) | 0.2334 (5위) |
| escape | 0.4950 (2위) | **0.4950 (1위)** |
| fire | 0.4350 (3위) | 0.4350 (2위) |
| struct | 0.3550 (4위) | 0.3550 (3위) |
| team | 0.2950 (5위) | 0.2950 (4위) |

**주요 결정 사항**
- `hazard_smoke_overrides: dict[str, float]` — per-hazard 연기 density로 방향별 시인성 하락 모델링
- `score = max(0, base) × max(0, 1 − smoke × visibility_sensitivity)` — 부하(difficulty) 도미넌트 시 0 클리핑 보장
- `PriorityQueueEngine.update()` 는 명시적 호출(매 틱); 내부 캐시 없음(단순성)
- `active_items()` ≤ top_k 보장 → HUD 직렬화 → 시선 전이 경로 단축

---

## Known Limitations / Next Steps

- STAGE 5: sim/ 에 합성 시뮬레이터 (장면·시선·동공·산란) 구현 예정
