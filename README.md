# Report Agent System

웹 리서치와 Neo4j GraphRAG를 결합한 실무형 멀티 에이전트 보고서 생성 시스템입니다.

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
- [x] 선택형 Neo4j Vector + Graph RAG 전문 에이전트
- [x] 웹 검색과 내부 GraphRAG 검색의 병렬 병합
- [x] TXT·Markdown·PDF 문서 적재 CLI
- [x] Neo4j Aura 연결·Vector Index·문서 적재·검색 E2E 검증

## 목표 아키텍처

```text
User
  └─ ReportOrchestrator
       ├─ OutlinerAgent
       │    └─ OutlineEvaluator
       ├─ ResearcherWorkflow
       │    ├─ SearchAgent × N (parallel)
       │    └─ GraphRAGAgent × N (optional, parallel)
       └─ WriterAgent
            ├─ SectionEvaluator
            └─ ReportEvaluator
```

## 동작 과정

1. `OutlinerAgent`가 요청을 구조화된 아웃라인으로 만듭니다.
2. Evaluator가 아웃라인을 검사하고 필요한 경우 제한 횟수만 재생성합니다.
3. CLI에서 사용자가 아웃라인을 승인하거나 한 번 수정할 수 있습니다.
4. `ResearcherWorkflow`가 섹션마다 `SearchAgent`를 제한된 동시성으로 실행합니다.
5. GraphRAG가 활성화되면 `GraphRAGAgent`가 Neo4j 내부 지식을 함께 검색하고 결과를 병합합니다.
6. `WriterAgent`가 섹션을 병렬 작성하고 품질을 검사합니다.
7. `ReportOrchestrator`가 결과를 Markdown과 JSON으로 저장합니다.

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

## Neo4j GraphRAG 사용

GraphRAG는 선택 기능입니다. 사용하지 않으면 기존 Tavily 웹 검색만 실행됩니다. 설치:

```bash
uv sync --locked --extra dev --extra rag
```

`.env`에 Neo4j 연결 정보를 추가합니다. 실제 비밀번호는 Git에 커밋하지 마세요.

```dotenv
REPORT_AGENT_RAG_ENABLED=true
REPORT_AGENT_NEO4J_URI=neo4j+s://YOUR_INSTANCE.databases.neo4j.io
REPORT_AGENT_NEO4J_USERNAME=neo4j
REPORT_AGENT_NEO4J_PASSWORD=...
REPORT_AGENT_NEO4J_DATABASE=neo4j
REPORT_AGENT_RAG_EMBEDDING_MODEL=openai/text-embedding-3-small
REPORT_AGENT_RAG_RETRIEVAL_MODE=hybrid
```

TXT, Markdown 또는 PDF를 임베딩하고 Neo4j에 적재합니다.

```bash
uv run report-agent rag-ingest ./documents/handbook.pdf
```

이후 일반 보고서 명령을 실행하면 각 섹션에서 웹 검색과 GraphRAG 검색을 병렬 수행합니다.
`vector` 모드는 일치 청크만 반환하고, 기본 `hybrid` 모드는 앞뒤 청크와 연결된
`RAGEntity` 노드까지 문맥에 포함합니다. 외부에서 엔티티 관계를 추가할 때는
`(RAGChunk)-[:MENTIONS]->(RAGEntity)` 형태를 사용합니다.

벡터 검색은 최신 Neo4j에서 Cypher 25 `SEARCH` 구문을 우선 사용합니다. `SEARCH`를
지원하지 않는 Neo4j 5.x 서버에서는 `db.index.vector.queryNodes` 프로시저로 자동
대체하여 강의 환경과 최신 Aura 환경을 모두 지원합니다.

보안을 위해 에이전트가 생성한 임의 Cypher는 실행하지 않습니다. 검색은 읽기 전용 정적
Cypher로 제한하며, 운영 Neo4j 계정에도 최소 권한을 적용하는 것을 권장합니다.

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
- mypy strict: 19개 소스 파일 통과
- pytest: 18개 테스트 통과
- 패키지 wheel·source distribution 빌드: 통과
- Neo4j Aura Vector Index 및 웹 + GraphRAG 보고서 생성 수동 E2E: 통과

실제 LLM·Tavily·Neo4j 호출을 사용하는 E2E 검증은 API 비용이 발생하므로 자동 CI에서는
제외하며, 배포 전 수동 검증 항목으로 관리합니다.

## 프로젝트 구조

```text
src/report_agent/
├── agents/
│   ├── outliner.py       # 아웃라인 생성
│   ├── graph_rag.py      # Neo4j GraphRAG 전문 에이전트
│   ├── researcher.py     # 병렬 검색 워크플로우
│   └── writer.py         # 섹션 및 최종 보고서 작성
├── rag/
│   └── neo4j_store.py    # 문서 적재, Vector Index, 그래프 확장 검색
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
- GraphRAG는 Neo4j 5.x Vector Index와 임베딩 API가 필요합니다.
- 기본 적재기는 문서 청크와 순서 관계를 생성하며, 도메인 엔티티 관계는 별도 추출·적재가 필요합니다.

## 보안

- API 키는 저장소에 커밋하지 않습니다.
- `.env.example`을 `.env`로 복사한 뒤 로컬에서만 값을 입력합니다.
- 에이전트가 생성한 결과는 기본적으로 `workspace/`에 저장되며 Git에서 제외됩니다.

## 라이선스

[MIT](LICENSE)
