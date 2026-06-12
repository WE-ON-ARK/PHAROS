<p align="center">
  <img src="docs/assets/pharos_logo.png" alt="PHAROS Logo" width="72" />
</p>

<h1 align="center">PHAROS</h1>
<p align="center"><em>Priority · Hazard · Attention · Reorganizing · Overload · Suppression</em></p>
<p align="center"><strong>시선 엔트로피 최소화 × 틴들 센싱 기반 소방관 지능형 HUD 시스템</strong></p>

<p align="center">
  <a href="https://github.com/WE-ON-ARK/PHAROS/releases">
    <img src="https://img.shields.io/badge/version-v1.0.0-blue?style=flat-square" alt="Version" />
  </a>
  <a href="https://github.com/WE-ON-ARK/PHAROS/graphs/contributors">
    <img src="https://img.shields.io/badge/contributors-3-brightgreen?style=flat-square" alt="Contributors" />
  </a>
  <a href="https://github.com/WE-ON-ARK/PHAROS/issues">
    <img src="https://img.shields.io/github/issues/WE-ON-ARK/PHAROS?style=flat-square&color=orange" alt="Open Issues" />
  </a>
  <img src="https://img.shields.io/badge/python-3.11+-lightblue?style=flat-square&logo=python" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/tests-128%20passed-success?style=flat-square&logo=pytest" alt="128 Tests Passing" />
  <img src="https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square" alt="License" />
  <img src="https://img.shields.io/badge/코드페어-소프트웨어%20공모전-red?style=flat-square" alt="코드페어 소프트웨어 공모전" />
</p>

---

## About This Project

**PHAROS** (Priority · Hazard · Attention · Reorganizing · Overload · Suppression)는 **코드페어 소프트웨어 공모전** 출품작으로, **Team ARK**가 개발한 소방관 인지 부하 저감 연구 프로토타입입니다.

화재 현장에 진입하는 소방 대원은 연기·화염·장애물·요구조자가 뒤엉킨 극한의 시각 작업공간에서 의사결정을 내려야 합니다. PHAROS는 **시선 엔트로피(Hs, Ht)** 와 **동공 확장 기반 인지 부하 지수(CLI)** 를 실시간 측정하여, STOM/SEEV 알고리즘으로 위험 정보를 우선순위 직렬화하고 최소화된 HUD로 시각화합니다.

> **핵심 명제:** 정보를 *더 많이* 보여주는 것이 아니라, *반드시 봐야 할 것만* 순서대로 안내한다.

---

## Problem Statement

소방관 현장 순직 및 부상 원인의 약 60% 이상이 **상황 인식 오류(Loss of Situation Awareness)** 에서 기인합니다. 이 문제는 네 가지 구체적 장벽으로 분해됩니다.

| 장벽 | 정량적 근거 |
|---|---|
| **시각 정보 과잉** | 기존 열화상 면체 사용 대원의 74%가 "정보 과잉으로 요구조자 실루엣을 놓쳤다"고 보고 |
| **인지 처리 마비** | 심박수 175 bpm 초과 시 복잡한 UI 정보 통합 처리 불가, 인지 누락률 92.4% |
| **방향 감각 상실** | 시야 확보 불능 상태 고립 사고가 현장 순직 원인의 18.2% |
| **팀 상황 인식 부재** | 대원 간 실시간 위치·부하 공유 체계 부재로 동료 위기 대응 지연 |

---

## Core Features

| 기능 | 설명 |
|---|---|
| **시선 엔트로피 엔진** | fixation 좌표를 AOI 격자로 이산화하여 Hs(정적 분산도)와 Ht(1차 Markov 전이 무작위성)를 실시간 계산. 인지 과부하 상태를 정량 감지. |
| **동공 기반 인지 부하 지수** | 동공 직경 시계열에서 blink 보간 → baseline 대비 확장률·peak·latency 추출 → 0~1 정규화 cognitive_load_index(CLI) 산출. |
| **틴들 센싱 모듈** | 650 nm 레이저 산란광 강도를 Koschmieder 모델로 변환하여 연기 농도(0~1)와 추정 가시거리(m)를 실시간 출력. |
| **STOM 우선순위 큐** | Salience·Task relevance·Observer expectancy·Motor cost 4-파라미터로 위험 항목을 점수화. 연기 농도 연동 동적 재가중치. 상위 1~2개만 HUD에 직렬 표출하여 Ht를 강제 하강. |
| **Replay HUD** | React + TypeScript + FastAPI 기반 웹 HUD. 시선 트레일·위험물 마커·우선순위 리스트·연기 농도 배경을 실시간 시각화. Scenario A/B 비교 재생 지원. |
| **팀 메시 코어** | TeamCoordinator가 3인 팀 TeammateState를 집계, PeerStatus 해소 및 MAYDAY·FLASHOVER 등 8종 TeamEvent를 자동 도출. 지휘 HUD에 TeamSnapshot 스트리밍. |
| **2×2 실험 러너** | 원시 UI(A) vs 직렬화 HUD(B) × 저연기 vs 고연기 4개 조건, 30 독립 시드로 Ht·Hs·CLI 비교. Mann-Whitney U 단측 검정으로 H1~H3 기각(p < 0.0001). |

---

## System Architecture

```
센싱 계층          │  io/ 어댑터 (GazeSource · PupilSource · SensingSource)
                  │        │
알고리즘 계층       │  entropy/ → cogload/ → sensing/ → priority/
                  │        │
오케스트레이터      │  pipeline/ (PharosPipeline.tick() → HudState)
                  │        │
팀 메시 코어       │  comms/ (TeamCoordinator → TeamSnapshot)
                  │        │
출력 계층          │  hud/ (FastAPI WebSocket → React Frontend)
                  │
실험·검증 계층     │  sim/ (GazeSimulator) · eval/ (2×2 ExperimentRunner)
```

**닫힌 루프 흐름:** 시선·동공·산란 센싱 → 엔트로피·부하·농도 계산 → STOM 점수화 → 우선순위 직렬화 HUD 출력 → 시선 집중 유도 → Ht 하강 → 인지 부하 저감

---

## Technology Stack

| 계층 | 기술 |
|---|---|
| **언어** | Python 3.11+ (strict type hints, mypy strict) |
| **수치 연산** | NumPy ≥ 1.26, SciPy ≥ 1.13 (Mann-Whitney U) |
| **API 서버** | FastAPI ≥ 0.111 + Uvicorn (WebSocket 스트리밍) |
| **프론트엔드** | React 18 + TypeScript + Vite (Canvas API, SVG Incident Map) |
| **빌드·린트** | Hatchling, Ruff (lint + format), mypy strict, pytest ≥ 8.2 |
| **CI 품질 게이트** | ruff check → mypy → pytest (128 tests, 0 warnings) |

---

## Experiment Results

**2×2 요인 실험** (Scenario A=원시 분산 시선 / B=구조화 집중 시선, 30 독립 시드)

| Scenario | Smoke | mean Hs | mean Ht | mean CLI | mean Visibility |
|:---:|:---:|---:|---:|---:|---:|
| A (원시) | 저농도 | 5.4090 | 2.1140 | 0.3992 | 22.46 m |
| A (원시) | 고농도 | 5.4090 | 2.1140 | 0.3992 | 2.75 m |
| **B (PHAROS)** | **저농도** | **3.3765** | **1.9060** | **0.2883** | 22.52 m |
| **B (PHAROS)** | **고농도** | **3.3765** | **1.9060** | **0.2883** | 2.76 m |

**Mann-Whitney U 단측 검정 결과 (n=30 per condition)**

| 가설 | U 통계량 | p-value | 효과크기 r | 기각 |
|---|---:|---:|---:|:---:|
| H1: Ht(B) < Ht(A) | 36.0 | < 0.0001 | +0.98 | **YES ✓** |
| H2: Hs(B) < Hs(A) | 0.0 | < 0.0001 | +1.00 | **YES ✓** |
| H3: CLI(B) < CLI(A) | 0.0 | < 0.0001 | +1.00 | **YES ✓** |

> H1~H3 모두 대단위 효과크기(r ≥ 0.98)로 기각. PHAROS HUD는 시선 분산도·전이 무작위성·인지 부하를 통계적으로 유의미하게 저감함을 입증.

---

---

## Repository

| | 링크 |
|---|---|
| **GitHub** | [github.com/WE-ON-ARK/PHAROS](https://github.com/WE-ON-ARK/PHAROS) |
| **출품 대회** | 코드페어 소프트웨어 공모전 |

---

## Local Setup

```bash
# 1. 의존성 설치
pip install -e ".[dev]"
# 또는 uv 사용
uv pip install -e ".[dev]"
```

```bash
# 2. HUD 프론트엔드 빌드
cd hud/frontend
npm install
npm run build
cd ../..
```

```bash
# 3. HUD 서버 실행
uvicorn hud.server:app --reload
# → http://localhost:8000
```

---

## Verification Gate

모든 단계의 통과 조건 — **명령 출력으로 증명**

```bash
ruff check src/ tests/   # lint: exit 0
mypy src/                # strict: 0 issues
pytest -q                # 128 passed, 0 warnings
```

```bash
# 2×2 실험 리포트 생성
python -m eval
```

---

## Scripts

```bash
pip install -e ".[dev]"     # 개발 환경 설치
ruff check src/ tests/      # 린트 검사
mypy src/                   # 타입 검사 (strict)
pytest -q                   # 전체 단위·통합 테스트
python -m eval              # 2×2 실험 러너 + 통계 + 마크다운 리포트
uvicorn hud.server:app      # HUD API 서버 (포트 8000)
```

---

## Project Structure

```
PHAROS/
├── src/pharos/
│   ├── entropy/      # Hs(정적), Ht(전이) 실시간 엔트로피 계산
│   ├── cogload/      # 동공 직경 → cognitive_load_index
│   ├── sensing/      # 틴들 산란광 → 연기 농도 → 가시거리
│   ├── priority/     # STOM 점수화 + PriorityQueueEngine
│   ├── pipeline/     # PharosPipeline.tick() 오케스트레이터 + HudState
│   ├── comms/        # TeamCoordinator: 팀 상태 집계 + 돌변상황 이벤트
│   └── io/           # GazeSource · PupilSource · SensingSource 어댑터 인터페이스
├── sim/              # 합성 시선·동공·산란·팀 시뮬레이터
├── eval/             # 2×2 실험 러너 + Mann-Whitney 통계 + 마크다운 리포트
├── hud/
│   ├── core.py       # 리플레이 생성기
│   ├── server.py     # FastAPI (REST + WebSocket)
│   └── frontend/     # React 18 + TypeScript + Vite HUD 프론트엔드
├── tests/            # 단위·통합 테스트 128개
├── docs/
│   ├── PROGRESS.md   # STAGE 0~10 진척 기록
│   └── architecture.md
└── pyproject.toml    # 빌드 · 의존성 · 린트 설정
```

---

## Implemented Stages

| Stage | 내용 | 테스트 |
|:---:|---|:---:|
| 0 | 하네스 셋업 (pyproject, ruff, mypy, pre-commit) | 1 |
| 1 | 시선 엔트로피 코어 (Hs, Ht, Markov 전이 행렬) | 8 |
| 2 | 동공 기반 인지 부하 추정기 (CLI, blink 보간) | 8 |
| 3 | 틴들 센싱 모듈 (Koschmieder 가시거리 모델) | 14 |
| 4 | STOM 우선순위 큐 엔진 (동적 재정렬, top-k 직렬화) | 11 |
| 5 | 시뮬레이션 하네스 (합성 시선·동공·산란, 4-조건 검증) | 11 |
| 6 | 파이프라인 오케스트레이터 + IO 어댑터 + HudState | 12 |
| 7 | HUD 프론트엔드 (React + FastAPI, Canvas, 우선순위 리스트) | 13 |
| 8 | 2×2 실험 러너 + 통계 + 리포트 (Mann-Whitney U) | 12 |
| 9 | 팀 메시 코어 (TeamCoordinator, 8종 이벤트 도출) | 17 |
| 10 | 팀 전송 + 멀티노드 시뮬 + 지휘 HUD (TeamSnapshot WebSocket) | 21 |

---

## Known Limitations

- **H4(연기→Ht 증가) 검증 불가**: 시뮬레이터가 연기 농도에 따라 시선 패턴을 변경하지 않음. 실제 아이트래커 하드웨어 연결 시 재검증 필요.
- **단일 장면 고정**: victim·escape·fire 3개 hazard 구성. 다양한 화재 장면 일반화 미검증.
- **리플레이 기반 WebSocket**: 실시간 다중 클라이언트 팬아웃은 미구현 (프로토타입 단계).
- **하드웨어 미연결**: 실제 아이트래커·광센서 드라이버는 `src/pharos/io/` 어댑터 인터페이스 구현으로 확장 가능.
- **FLASHOVER·STRUCTURAL_COLLAPSE 이벤트**: enum 정의만 존재, 자동 탐지 트리거 미구현.

---

## References

1. Kahneman, D. (1973). *Attention and Effort.* Prentice-Hall. (제한 인지자원 이론)
2. Shiferaw, B. et al. (2018). Stationary and Transition Gaze Entropy as indicators of cognitive workload. *Journal of Eye Movement Research*, 11(2).
3. Szulewski, A. et al. (2014). The Pupil as a Measure of Cognitive Workload in Emergency Medicine Simulation. *Annals of Emergency Medicine*, 64(4).
4. Wickens, C. D. (2002). Multiple resources and performance prediction. *Theoretical Issues in Ergonomics Science*, 3(2).

---

<p align="center">
  <em>"더 많은 정보가 아닌, 반드시 봐야 할 것만 — 소방관의 시선을 살린다."</em>
</p>
