# /verify — PHAROS 검증 게이트

PHAROS 프로젝트의 세 가지 품질 게이트를 순서대로 실행하고 각 출력을 그대로 표시한다.

```bash
echo "=== [1/3] ruff check ===" && ruff check src/ tests/
echo "=== [2/3] mypy ===" && mypy src/
echo "=== [3/3] pytest ===" && pytest -q
```

하나라도 non-zero exit으로 종료되면 **GATE FAILED** 를 명시하고 어느 단계에서 실패했는지 표시한다.
세 단계 모두 exit 0으로 통과하면 **ALL GATES PASSED** 를 선언한다.

출력은 요약 없이 각 명령의 원문 출력을 그대로 첨부해야 한다.
