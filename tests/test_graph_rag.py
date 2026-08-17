from pathlib import Path
from typing import Any

import pytest

from report_agent.agents.graph_rag import GraphRAGAgent, RAGFindings
from report_agent.config import Settings
from report_agent.models import OutlineSection
from report_agent.rag.neo4j_store import RetrievedChunk, chunk_text, load_document


class FakeStore:
    async def search(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        assert embedding == [0.1, 0.2]
        assert top_k == 3
        return [
            RetrievedChunk(
                chunk_id="doc:0",
                title="Internal handbook",
                source="rag://document/handbook",
                text="GraphRAG combines vector retrieval and graph traversal.",
                context="Previous. GraphRAG combines vector retrieval and graph traversal. Next.",
                score=0.91,
            )
        ]


class FakeClient:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        assert texts == ["How does retrieval work?"]
        return [[0.1, 0.2]]

    async def structured(self, schema: type[RAGFindings], **kwargs: Any) -> RAGFindings:
        assert schema is RAGFindings
        assert "UNTRUSTED_GRAPHRAG_CONTEXT" in kwargs["user"]
        return RAGFindings(findings=["Vector retrieval is expanded with graph context."])


@pytest.mark.asyncio
async def test_graph_rag_agent_returns_internal_sources() -> None:
    settings = Settings(rag_top_k=3)
    agent = GraphRAGAgent(settings, store=FakeStore(), client=FakeClient())  # type: ignore[arg-type]
    section = OutlineSection(
        title="Retrieval",
        description="Explain retrieval",
        research_questions=["How does retrieval work?"],
    )

    result = await agent.run(section)

    assert result.complete
    assert result.findings == ["Vector retrieval is expanded with graph context."]
    assert result.sources[0].origin == "rag"
    assert str(result.sources[0].url) == "rag://document/handbook"


def test_chunk_text_handles_overlap_and_single_chunk() -> None:
    assert chunk_text("short", size=10, overlap=2) == ["short"]
    assert chunk_text("abcdefghijk", size=6, overlap=2) == ["abcdef", "efghij", "ijk"]


def test_load_markdown_document(tmp_path: Path) -> None:
    path = tmp_path / "guide.md"
    path.write_text("# Guide\n\nGraphRAG content", encoding="utf-8")

    document = load_document(path)

    assert document.title == "guide"
    assert document.source.startswith("file://")
    assert "GraphRAG content" in document.text
