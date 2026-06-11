# PHAROS

**P**riority · **H**azard · **A**ttention · **R**eorganizing · **O**verload · **S**uppression

소방관 화재 진입 시 시각 정보 과잉으로 인한 인지 부하를 측정하고,
시선 엔트로피가 낮아지는 방향으로 위험·과제를 우선순위 리스팅하여 HUD로 시각화하는 연구 프로토타입.

## 설치

```bash
pip install -e ".[dev]"
# 또는
uv pip install -e ".[dev]"
```

## 실행 (STAGE 9 완성 후)

```bash
python -m pharos.demo
```

## 검증

```bash
ruff check src/ tests/
mypy src/
pytest -q
```

## 아키텍처

상세 내용은 [CLAUDE.md](CLAUDE.md) 및 [docs/](docs/) 참조.

## 한계 및 확장 지점

- 현재 구현은 합성 데이터 기반. 실 하드웨어(아이트래커, 광센서) 연결은 `src/pharos/io/` 어댑터 구현으로 확장.
- HUD는 리플레이 모드 기준. 실시간 WebSocket 연결은 STAGE 9 이후 계획.
