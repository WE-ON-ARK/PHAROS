# PHAROS — 프로젝트 소개 사이트

> 이 브랜치(`pharos_site`)는 **소개 웹사이트 전용**입니다.
> PHAROS 본체 소스코드(Python 엔진 · React HUD · 테스트)는 [`main`](https://github.com/WE-ON-ARK/PHAROS/tree/main) 브랜치에 있습니다.

**PHAROS**: 소방관 인지부하 저감을 위한 시선 엔트로피 최소화 및 틴들 센싱 기반 지능형 HUD 시스템
TEAM ARK · 대전대신고등학교 · 제8회 한국코드페어 소프트웨어 공모전

---

## 구성

```
index.html      한 페이지 소개 사이트 (문제 → 해법 → 시뮬레이터 → 알고리즘 → 하드웨어 → 검증 → 비교 → 로드맵 → 팀)
styles.css      전체 스타일 (모바일 우선 반응형, 다크 + 블루프린트 라이트 섹션)
app.js          내비게이션 · 스크롤 리빌 · 적응 엔진 시뮬레이터
assets/         로고(SVG), 헬멧 설계도, Fusion 360 렌더
.nojekyll       GitHub Pages의 Jekyll 처리 비활성화
```

빌드 도구·의존성이 없는 **정적 사이트**입니다. `index.html`을 브라우저로 열면 그대로 동작합니다.

로컬에서 확인할 때:

```bash
python -m http.server 5500
```

## 적응 엔진 시뮬레이터

`#demo` 섹션의 시뮬레이터는 PHAROS 코어와 동일한 수식을 사용합니다.

| 항목 | 수식 | 상수 |
|---|---|---|
| 가시거리 역산 | `V = V_max · e^(−kρ)` | `V_max = 30 m`, `k = 3.0` |
| 시각 전달 가치 | `V_i = max(0, B_i · (1 − λρ_i))` | `λ = 0.6` |
| 대체 채널 가중 | `A_i = B_i·λρ_i + μ·CLI + ν·R_i` | `μ = 0.25`, `ν = 0.10` |
| 표시 개수 | `K = 2 → 1` | `CLI > 0.45` |
| 모드 전환 | NORMAL / FOCUSED / EMERGENCY | `V_F < 10 m` / `V_F < 3 m` |

`Stage 4 재현` 프리셋(ρ_R = 0.99)은 작품설명서의 Stage 4 실측 결과
— 요구조자 점수 `0.5750 → 0.2334`, 5위 강등, 나머지 방향 점수 보존 — 를 그대로 재현합니다.

## GitHub Pages 배포

**방법 A — 브랜치 배포 (권장, 설정 한 번이면 끝)**

1. 저장소 → **Settings** → **Pages**
2. Source: `Deploy from a branch`
3. Branch: **`pharos_site`** / **`/ (root)`** → Save
4. 1~2분 뒤 `https://we-on-ark.github.io/PHAROS/` 에 게시됩니다.

**방법 B — GitHub Actions 배포**

Source를 `GitHub Actions`로 설정하면 `.github/workflows/deploy-pages.yml`이
`pharos_site` 브랜치에 push될 때마다 자동으로 배포합니다.

## 모바일 대응

- 뷰포트 375 px부터 검증한 모바일 우선 레이아웃
- 햄버거 메뉴, 터치 친화적 슬라이더(썸 18 px), 가로 스크롤 테이블
- `clamp()` 기반 유동 타이포그래피, `100svh` 히어로 (모바일 주소창 대응)
- `prefers-reduced-motion` 존중 — 모션 최소화 설정 시 애니메이션 비활성화

## 자료 출처

작품 요약서 · 작품 설명서 · 발표자료(TEAM ARK, 2026)의 내용과 실측 데이터를 근거로 작성했습니다.
헬멧 설계도와 3D 모델 이미지는 작품 설명서에 수록된 원본(Fusion 360)을 웹용으로 최적화한 것입니다.
