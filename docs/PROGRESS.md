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

## STAGE 5 — 시뮬레이션 하네스 (2026-06-11)

**산출물**
- `sim/core.py`: `SceneSpec`, `SimFrame`, `make_default_scene`, `GazeSimulator` (simulate_a/b/stream)
- `sim/__init__.py`: public API re-export
- `tests/test_sim.py`: 11개 테스트 (Ht 비교, Hs 비교, 범위 검증, CLI 단조성, stream, 연기 비교, e2e, 4-조건 표)
- `pyproject.toml`: mypy_path에 `"."` 추가, `packages = ["pharos", "sim"]`

**검증 게이트**
- [x] ruff check 통과
- [x] mypy strict 통과 (20 source files, 0 issues)
- [x] pytest 통과 (53 passed)
- [x] 4-조건 요약표 (A/B × 저/고 연기, seed=42):

| Scenario | Smoke | Hs | Ht | CLI |
|----------|-------|------|------|------|
| A | low | 5.4400 | **2.0915** | 0.7334 |
| B | low | 3.3240 | **1.9513** | 0.6159 |
| A | high | 5.4400 | **2.0915** | 0.7334 |
| B | high | 3.3240 | **1.9513** | 0.6159 |

Ht(B) < Ht(A) 양쪽 연기 조건에서 재현 가능하게 통과.

**주요 결정 사항**
- Scenario B 구조화 시선: 85% 확률 순환 전이(zone→zone) + Gaussian σ=35px 클러스터링
- seed 분리: simulate_a=seed, simulate_b=seed+1 (호출 순서 무관 재현성)
- 동공 피크: A=6.0mm (50% 확장, 고부하), B=5.0mm (25% 확장, 저부하)
- 산란: `clip(smoke_density + N(0, 0.03), 0, 1)` — 실제 Tyndall 센서 노이즈 모사

---

## STAGE 6 — 파이프라인 오케스트레이터 + IO 어댑터 + HudState (2026-06-11)

**산출물**
- `src/pharos/io/core.py`: `GazeSample`, `GazeSource`(ABC), `ReplayGazeSource`, `PupilSample`, `PupilSource`(ABC), `ReplayPupilSource`
- `src/pharos/io/__init__.py`: public API re-export
- `src/pharos/pipeline/core.py`: `HudState` (+ `to_dict()`), `PharosPipeline` (`tick()`, `can_tick()`)
- `src/pharos/pipeline/__init__.py`: public API re-export
- `tests/test_pipeline.py`: 12개 테스트

**검증 게이트**
- [x] ruff check 통과
- [x] mypy strict 통과 (13 source files, 0 issues)
- [x] pytest 통과 (65 passed, 53→65)
- [x] 주요 출력:

| 측정 | 값 |
|------|-----|
| pipeline Ht(A) | **2.0915** bits |
| pipeline Ht(B) | **1.9513** bits |
| mean density (low smoke) | 0.0963 |
| mean density (high smoke) | 0.7963 |

**주요 결정 사항**
- `GazeSource` / `PupilSource` ABC: `SensingSource`와 완전 대칭 구조 (read/has_data)
- 버퍼: `deque(maxlen=fixation_window/pupil_window)` — O(1) append, 자동 eviction
- cogload 부족 시 `0.0` 반환 — [0,1] 범위 유지
- `HudState.to_dict()`: `active_hazards` → `{id, kind, priority}` 최소화 (JSON 계약)
- `ranked_scores`: `list[tuple[float, str]]` — score + hazard_id만 (Hazard 전체 직렬화 불필요)
- e2e Ht 테스트: `fixation_window=200` 필요 — 작은 window에서 희소 전이 행렬로 A<B 역전 현상

---

## STAGE 7 — HUD 프론트엔드 (React + TypeScript + FastAPI) (2026-06-11)

**산출물**
- `hud/core.py`: `generate_replay(scene, scenario, n_frames)` → `list[dict]`
- `hud/server.py`: FastAPI (`/api/replay/{scenario}`, `/api/scene`), lifespan 패턴
- `hud/frontend/`: React 18 + TypeScript + Vite (SceneView, MetricsPanel, PriorityList, Controls)
- `tests/test_hud.py`: 13개 테스트

**검증 게이트**
- [x] ruff check 통과
- [x] mypy strict 통과 (16 source files, 0 issues)
- [x] pytest 통과 (78 passed, 65→78)
- [x] `tsc && vite build` 성공 (36 modules, 151 kB JS)
- [x] UI 렌더링 확인 (스크린샷):
  - 위험물 마커 올바른 위치 (victim=빨강, escape=초록, fire=주황)
  - Priority Queue 하이라이트 (victim 0.547 > escape 0.496)
  - Scenario A/B 토글, 재생 컨트롤, 타임라인 슬라이더

**주요 결정 사항**
- `generate_replay()` 각 HudState 딕셔너리에 `fixation` 필드 추가 (SceneView 시선 트레일용)
- FastAPI: `@app.on_event` → lifespan 컨텍스트 매니저 (deprecation 제거)
- Canvas에서 smoke_density를 배경 밝기로 반영 (연기 농도 시각화)
- `fixation_window=200` 사용 — 전체 200프레임 엔트로피 비교 정확도 보장

---

## STAGE 8 — 2×2 실험 러너 + 통계 + 리포트 (2026-06-12)

**산출물**
- `eval/runner.py`: `run_experiment(n_reps=30)` → `ExperimentResult` — 4 조건 × 30 독립 시드
- `eval/stats.py`: `analyse()` → `HypothesisResults` — Mann-Whitney U 단측 검정 (H1~H4)
- `eval/report.py`: `build_report()` → str — 마크다운 2×2 집계표 + 가설 표 + 결론
- `eval/__main__.py`: `python -m eval` 진입점
- `eval/__init__.py`: 전체 public API re-export
- `tests/test_eval.py`: 12개 테스트
- `pyproject.toml`: `scipy>=1.13` 추가, `packages = ["pharos", "sim", "hud", "eval"]`

**검증 게이트**
- [x] ruff check 통과
- [x] mypy strict 통과 (21 source files, 0 issues)
- [x] pytest 통과 (90 passed, 78→90)
- [x] `python -m eval` 리포트 출력:

| Scenario | Smoke | mean Hs | mean Ht | mean CLI | mean Visibility |
|----------|-------|--------:|--------:|---------:|----------------:|
| A | low | 5.4090 | 2.1140 | 0.3992 | 22.46 m |
| A | high | 5.4090 | 2.1140 | 0.3992 | 2.75 m |
| B | low | 3.3765 | 1.9060 | 0.2883 | 22.52 m |
| B | high | 3.3765 | 1.9060 | 0.2883 | 2.76 m |

| Hypothesis | U statistic | p-value | effect (r) | Rejected |
|------------|------------:|--------:|-----------:|----------|
| H1: Ht(B) < Ht(A) | 36.0 | 0.0000 | +0.9800 | YES ✓ |
| H2: Hs(B) < Hs(A) | 0.0 | 0.0000 | +1.0000 | YES ✓ |
| H3: CLI(B) < CLI(A) | 0.0 | 0.0000 | +1.0000 | YES ✓ |
| H4: Ht(A,hi) > Ht(A,lo) | 450.0 | 0.5030 | +0.0000 | NO |

**주요 결정 사항**
- per-frame 풀링 방식 대신 **per-rep 최종 프레임 값** 사용: fixation_window=n_frames인 rolling buffer는 초기 프레임에서 B(구조화)가 A(랜덤)보다 Ht가 더 높아지는 성장 교차 현상 발생 → 최종(수렴) 프레임만 추출하여 30 시드로 비교
- CLI: per-rep post-warmup mean (pupil 신호는 수렴이 빠르므로 평균 사용)
- H4 기각 불가 (p=0.50): 시뮬레이터가 연기 농도에 따라 시선을 변화시키지 않으므로 설계상 예상된 결과 (Known Limitation)

---

## STAGE 9 — 팀 메시 코디네이션 코어 (comms/) (2026-06-12)

**산출물**
- `src/pharos/comms/core.py`: `PeerStatus`·`EventKind` enum, `TeammateState`·`TeamEvent`·`PeerView`·`TeamSnapshot` dataclass, `derive_status()`, `TeamCoordinator`
- `src/pharos/comms/__init__.py`: public API re-export
- `tests/test_comms.py`: 17개 테스트
- `CLAUDE.md`: 용어사전 5종 추가(TeammateState/TeamEvent/PeerStatus/TeamCoordinator/TeamSnapshot), 모듈구조에 comms/ 추가

**검증 게이트**
- [x] ruff check 통과
- [x] mypy strict 통과 (23 source files, 0 issues)
- [x] pytest 통과 (107 passed, 90→107)
- [x] 상태 해소·이벤트 도출 동작:

| 입력 | 해소 상태 | 도출 이벤트 |
|------|----------|------------|
| CLI=0.8 | OVERLOAD | OVERLOAD_ALERT |
| self_reported=DISTRESS | DISTRESS | MAYDAY |
| 침묵 > 5s (heartbeat) | LOST | LOST_CONTACT |
| LOST → 신규 업데이트 | OK | RECOVERED |

**주요 결정 사항**
- **순수·동기 코어**: 전송(WebSocket)·async 일절 없음 → strict 게이트로 완전 검증. 모든 선행 단계(entropy/cogload/sensing/priority)가 순수 코어였던 패턴 유지. WebSocket 허브(STAGE 10)가 이 코어를 감쌈
- **상태 해소 우선순위**: 침묵>timeout → LOST가 최우선(자가보고 MAYDAY보다도). 이유: 통신 두절 시 마지막 자가보고와 무관하게 "대원을 잃었다"는 사실이 지배적
- **이벤트 중복 억제**: 상태 *전이* 시에만 이벤트 발생. 과부하 지속 중 매 틱 재경보 방지
- **이중 경로 상태**: OK/OVERLOAD/LOST는 코디네이터 도출, DISTRESS/DOWN은 대원 자가보고(수동 MAYDAY) 허용
- **토폴로지 = 허브앤스포크**: 지휘소가 집계·재배포 (P2P 메시 대비 단순, 실제 incident command와 일치)
- **위치 = 별도 incident-map 좌표(m)**: 시선(800×600 화면)과 분리한 물리적 위치 → 대원 상호 모니터링용
- 이벤트 피드는 `deque(maxlen=50)` 링버퍼

---

## STAGE 10 — 팀 전송 + 멀티노드 시뮬 + 지휘 HUD (2026-06-12)

**산출물**
- `sim/team.py`: `TeamMemberSpec`, `TeamSimulator`, `make_default_team` — 3인 팀(alpha/bravo/charlie) 웨이포인트 순찰 + 독립 PharosPipeline per 대원
- `hud/server.py` 확장: `/ws/live?scenario&fps` (단일노드), `/ws/team?fps` (TeamSnapshot 스트림)
- `hud/frontend/src/hooks/useTeamWS.ts`: WS → `TeamSnapshot` 상태 훅
- `hud/frontend/src/components/TeamMap.tsx`: SVG 500×400 incident map (50×40m), 상태색 대원 점·글로우
- `hud/frontend/src/components/EventFeed.tsx`: 최신순 10건, 8종 이벤트 색상 배지
- `hud/frontend/src/App.tsx` 확장: "Replay" / "Team Live" 모드 탭
- `hud/frontend/vite.config.ts`: `/ws` 프록시 추가 (WS → localhost:8000)
- `tests/test_team_sim.py`: 10개 테스트
- `tests/test_ws.py`: 11개 테스트

**검증 게이트**
- [x] ruff check 통과
- [x] mypy strict 통과 (26 source files, 0 issues)
- [x] pytest 통과 (128 passed, 107→128)
- [x] `tsc && vite build` 성공 (39 modules, 156.64 kB)
- [x] UI 렌더링 확인 (스크린샷):
  - **Replay 모드**: 위험물 마커·우선순위 큐·재생 컨트롤 정상 동작
  - **Team Live 모드**: alpha/bravo/charlie 3인 상태카드(CLI%·visibility·OK 배지), EventFeed, Incident Map SVG 대원 점 표시, 헤더 `Team Live · t=4.7s` 녹색
- [x] WebSocket `/ws/team` 실 응답 확인: `{timestamp, peers[3], recent_events}`, 첫 피어 `alpha ok`

**주요 결정 사항**
- **허브앤스포크 WebSocket**: FastAPI가 사전 계산된 200 프레임 TeamSnapshot을 `asyncio.sleep(1/fps)` 속도로 스트리밍. 실시간 다중 클라이언트 대신 미리 시뮬레이션된 결과 재생 (프로토타입 단계 단순화)
- **TeamSimulator 위치**: 웨이포인트 사이 선형 보간 + 사이클릭 랩 (거리 기반), 속도 1m/s, 3인 서로 다른 순찰 경로 (south wing / east wing / entrance)
- **fixation_window=n_frames**: 전체 프레임 크기로 설정해 희소 전이 행렬 아티팩트 방지 (STAGE 8 결정 사항 계승)
- **Vite `/ws` 프록시**: 브라우저에서 `ws://localhost:8000` 직접 연결 대신 동일 오리진 프록시 경유 → CORS 이슈 없음
- **AppMode 탭**: "replay" (기존 단일노드 재생) | "team" (팀 라이브) 전환 가능, 기존 Replay 기능 완전 보존

---

## Known Limitations

- H4(연기→Ht 증가) 검증 불가: 현재 GazeSimulator가 smoke_density에 따라 시선 패턴을 변경하지 않음 → 실제 실험에서만 검증 가능
- 단일 장면 고정 (victim/escape/fire 3개 hazard): 다양한 장면 구성에 대한 일반화 미검증
- WebSocket 스트리밍은 사전 계산된 재생 방식 — 실시간 다중 클라이언트 팬아웃(실전 배포)은 미구현
- FLASHOVER_WARNING·STRUCTURAL_COLLAPSE·NEW_VICTIM·EVACUATE 이벤트는 enum 정의만 존재 — 자동 탐지 트리거는 미구현(수동/외부 주입 가정)
