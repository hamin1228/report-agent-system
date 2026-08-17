# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Added

- Optional Neo4j GraphRAG agent with vector and graph-expanded hybrid retrieval
- Cypher 25 `SEARCH` with an automatic Neo4j 5.x vector procedure fallback
- TXT, Markdown, and PDF ingestion through the `rag-ingest` CLI command
- Parallel merging of web research and internal GraphRAG evidence
- Multi-agent outline, parallel research, writing, and evaluation workflow
- Interactive outline approval and explicit `generate` CLI command
- Tavily source relevance filtering and citation allowlisting
- API retry with exponential backoff and partial research failure handling
- Phase checkpoints and Markdown/JSON artifact persistence
- SSRF-aware fetching and prompt-injection boundaries
- GitHub Actions CI, Dependabot, contribution, and security documentation

### Fixed

- Corrected Neo4j vector index DDL and multi-chunk `NEXT` relationship creation
- Isolated unit tests from locally enabled GraphRAG environment settings

## [0.1.0] - 2026-07-31

- Initial production-oriented project structure
