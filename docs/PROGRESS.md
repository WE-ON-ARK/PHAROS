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

## Known Limitations / Next Steps

- STAGE 2: cogload/ 에 동공 기반 인지 부하 추정기 구현 예정
