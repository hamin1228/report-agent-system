# Report Agent System

강의의 리포트 생성 멀티 에이전트 구조를 실무형 Python 패키지로 통합한 프로젝트입니다.

## 구현 상태

- [x] GitHub 배포용 프로젝트 뼈대
- [x] 환경변수 기반 설정과 LiteLLM 클라이언트
- [x] 에이전트 간 공유 데이터 모델
- [x] Outliner / Researcher / Search / Writer
- [x] 품질 평가 및 제한된 재시도
- [x] Orchestrator와 HITL 아웃라인 승인
- [x] Markdown·JSON 기반 단계별 결과 저장
- [x] 파일 경로 중심 컨텍스트 관리 기반
- [x] CLI 및 기본 단위 테스트
- [x] Python 컴파일 및 단위 테스트 통과
- [x] 검색 관련성·출처 품질 필터와 인용 URL 검증
- [x] API 재시도·부분 실패 처리·단계별 체크포인트
- [x] SSRF·리디렉션·응답 크기·콘텐츠 타입 방어
- [x] 프롬프트 인젝션 데이터 경계
- [x] GitHub Actions·Dependabot·이슈/PR 템플릿

## 목표 아키텍처

```text
User
  └─ ReportOrchestrator
       ├─ OutlinerAgent
       │    └─ OutlineEvaluator
       ├─ ResearcherWorkflow
       │    └─ SearchAgent × N (parallel)
       └─ WriterAgent
            ├─ SectionEvaluator
            └─ ReportEvaluator
```

## 동작 과정

1. `OutlinerAgent`가 요청을 구조화된 아웃라인으로 만듭니다.
2. Evaluator가 아웃라인을 검사하고 필요한 경우 제한 횟수만 재생성합니다.
3. CLI에서 사용자가 아웃라인을 승인하거나 한 번 수정할 수 있습니다.
4. `ResearcherWorkflow`가 섹션마다 `SearchAgent`를 제한된 동시성으로 실행합니다.
5. `WriterAgent`가 섹션을 병렬 작성하고 품질을 검사합니다.
6. `ReportOrchestrator`가 결과를 Markdown과 JSON으로 저장합니다.

CLI는 각 단계에서 `OUTLINE`, `APPROVAL`, `RESEARCH`, `WRITING`, `COMPLETE` 상태를
출력합니다. 외부 API가 일시적으로 실패하면 제한된 지수 백오프로 재시도하며,
특정 섹션의 리서치만 실패한 경우 나머지 섹션은 계속 처리합니다.

## 빠른 시작

Python 3.11 이상과 [uv](https://docs.astral.sh/uv/) 사용을 권장합니다.

```bash
git clone <YOUR_REPOSITORY_URL>
cd agent
uv sync --locked --extra dev
cp .env.example .env
```

`.env`에 사용할 LLM 공급자의 API 키와 Tavily 키를 입력합니다.

```dotenv
OPENAI_API_KEY=...
TAVILY_API_KEY=...
REPORT_AGENT_MODEL=openai/gpt-4.1-mini
REPORT_AGENT_EVALUATOR_MODEL=openai/gpt-4.1-mini
REPORT_AGENT_MAX_API_RETRIES=3
REPORT_AGENT_MINIMUM_SOURCE_SCORE=0.45
```

애플리케이션 시작 시 `.env`가 자동으로 로드됩니다. 이미 셸이나 배포 환경에 설정된
환경변수가 있으면 해당 값이 우선하며 `.env`가 덮어쓰지 않습니다.

보고서 생성:

```bash
uv run report-agent generate "2026년 AI 에이전트 시장과 기술 동향"
```

추가 요구사항 전달:

```bash
uv run report-agent generate \
  "기업용 AI 에이전트 도입 전략" \
  --requirements "CTO 대상, 한국어, 보안과 ROI 중심"
```

대화형 아웃라인 승인을 생략하려면 다음 옵션을 사용합니다.

```bash
uv run report-agent generate "AI 에이전트 동향" --no-approve
```

실행 결과는 `workspace/run-<timestamp>-<id>/`에 저장됩니다.

```text
outline.json
research.json
report.json
report.md
state.json
```

## 테스트와 품질 검사

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src/report_agent
uv build
```

커밋 전 자동 검사를 사용하려면:

```bash
pre-commit install
pre-commit run --all-files
```

현재 `0.1.0` 구현 검증 결과:

- Ruff lint: 통과
- Ruff format: 통과
- mypy strict: 15개 소스 파일 통과
- pytest: 14개 테스트 통과
- 패키지 wheel·source distribution 빌드: 통과

실제 LLM·Tavily 호출을 사용하는 E2E 검증은 API 비용이 발생하므로 자동 테스트에서 제외합니다.

## 프로젝트 구조

```text
src/report_agent/
├── agents/
│   ├── outliner.py       # 아웃라인 생성
│   ├── researcher.py     # 병렬 검색 워크플로우
│   └── writer.py         # 섹션 및 최종 보고서 작성
├── tools/web.py          # Tavily 검색과 HTTP fetch
├── config.py             # 환경변수 설정
├── context.py            # 파일 기반 컨텍스트 조회
├── evaluators.py         # LLM 품질 게이트
├── llm.py                # LiteLLM 호출 래퍼
├── models.py             # 공유 데이터 계약
├── orchestrator.py       # 전체 워크플로우
├── storage.py            # 실행 결과 저장
└── cli.py                # CLI
```

## 설계 원칙

- 각 에이전트는 하나의 책임만 가집니다.
- 에이전트 간 데이터는 Pydantic 모델로 검증합니다.
- 검색 에이전트는 섹션 단위로 병렬 실행하되 동시성 상한을 둡니다.
- Tavily 관련성 점수와 도메인 정책으로 낮은 품질의 검색 결과를 제외합니다.
- Writer가 제출한 인용은 실제 섹션 리서치에 포함된 URL만 허용합니다.
- 품질 평가 재시도에는 상한을 두어 비용 폭증과 무한 루프를 방지합니다.
- 전체 산출물을 상위 에이전트 대화에 넣지 않고 파일로 저장합니다.
- 단계별 `state.json`을 저장하여 실패 원인과 마지막 성공 상태를 보존합니다.
- API 키와 실행 결과는 Git에 포함하지 않습니다.

## 보안

- Fetch는 HTTP(S) 공개 주소만 허용하며 localhost, 사설·예약·링크 로컬 IP를 차단합니다.
- DNS 결과와 리디렉션 목적지를 매번 다시 검증합니다.
- 응답 크기, 콘텐츠 타입, 리디렉션 횟수에 상한을 둡니다.
- 검색 결과와 외부 문서는 신뢰할 수 없는 데이터로 구분하여 내부 명령을 따르지 않습니다.
- 실제 운영에서는 `.env` 대신 클라우드 Secret Manager 사용을 권장합니다.

취약점 제보 및 배포 보안 점검은 [SECURITY.md](SECURITY.md)를 참고하세요.

## GitHub 자동 검사

`main` Push와 Pull Request에서 다음 검사를 자동 실행합니다.

```text
uv sync --locked
→ Ruff lint/format
→ mypy strict
→ pytest
→ wheel/sdist build
```

기여 방법은 [CONTRIBUTING.md](CONTRIBUTING.md), 변경 이력은
[CHANGELOG.md](CHANGELOG.md)를 참고하세요.

## 제한 사항

- 웹 검색은 현재 Tavily API를 사용합니다.
- 웹페이지 전문 파싱은 기본 HTTP fetch만 제공하며 사이트별 본문 정제는 향후 과제입니다.
- 외부 정보의 정확성과 라이선스는 보고서 배포 전에 사람이 최종 검토해야 합니다.

## 보안

- API 키는 저장소에 커밋하지 않습니다.
- `.env.example`을 `.env`로 복사한 뒤 로컬에서만 값을 입력합니다.
- 에이전트가 생성한 결과는 기본적으로 `workspace/`에 저장되며 Git에서 제외됩니다.

## 라이선스

[MIT](LICENSE)
