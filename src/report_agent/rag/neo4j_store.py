"""Neo4j vector storage and graph-expanded retrieval."""

import asyncio
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from report_agent.config import Settings

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class RAGDocument:
    title: str
    source: str
    text: str


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    title: str
    source: str
    text: str
    context: str
    score: float


class Neo4jGraphStore:
    """Stores document chunks and retrieves vector matches with graph context."""

    def __init__(self, settings: Settings) -> None:
        if not settings.rag_configured:
            raise ValueError("GraphRAG is not configured; check REPORT_AGENT_RAG_* settings")
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:  # pragma: no cover - exercised by installation smoke tests
            raise RuntimeError(
                "Neo4j support is not installed. Run: uv sync --extra rag --extra dev"
            ) from exc
        self.settings = settings
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
        )
        self._validate_identifier(settings.rag_vector_index)
        self._validate_identifier(settings.neo4j_database)

    @staticmethod
    def _validate_identifier(value: str) -> None:
        if not _SAFE_IDENTIFIER.fullmatch(value):
            raise ValueError(f"Unsafe Neo4j identifier: {value!r}")

    async def close(self) -> None:
        await asyncio.to_thread(self._driver.close)

    async def verify_connectivity(self) -> None:
        await asyncio.to_thread(self._driver.verify_connectivity)

    async def ensure_schema(self, dimensions: int) -> None:
        query = (
            f"CREATE VECTOR INDEX {self.settings.rag_vector_index} IF NOT EXISTS "
            "FOR (chunk:RAGChunk) ON chunk.embedding "
            f"OPTIONS {{indexConfig: {{`vector.dimensions`: {dimensions}, "
            "`vector.similarity_function`: 'cosine'}}"
        )
        await asyncio.to_thread(self._execute_write, query, {})

    async def ingest(
        self,
        document: RAGDocument,
        chunks: Sequence[str],
        embeddings: Sequence[Sequence[float]],
    ) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("Chunk and embedding counts must match")
        if not chunks:
            return 0
        document_id = uuid4().hex
        rows = [
            {
                "id": f"{document_id}:{index}",
                "position": index,
                "text": text,
                "embedding": list(embedding),
            }
            for index, (text, embedding) in enumerate(zip(chunks, embeddings, strict=True))
        ]
        query = """
        MERGE (document:RAGDocument {id: $document_id})
        SET document.title = $title, document.source = $source
        WITH document
        UNWIND $rows AS row
        CREATE (chunk:RAGChunk {
            id: row.id, position: row.position, text: row.text, embedding: row.embedding
        })
        CREATE (document)-[:HAS_CHUNK]->(chunk)
        WITH chunk ORDER BY chunk.position
        WITH collect(chunk) AS chunks
        UNWIND CASE WHEN size(chunks) > 1
               THEN range(0, size(chunks) - 2) ELSE [] END AS index
        WITH chunks[index] AS current, chunks[index + 1] AS next
        CREATE (current)-[:NEXT]->(next)
        """
        await asyncio.to_thread(
            self._execute_write,
            query,
            {
                "document_id": document_id,
                "title": document.title,
                "source": document.source,
                "rows": rows,
            },
        )
        return len(rows)

    async def search(self, embedding: Sequence[float], top_k: int) -> list[RetrievedChunk]:
        graph_context = """
            OPTIONAL MATCH (previous:RAGChunk)-[:NEXT]->(node)
            OPTIONAL MATCH (node)-[:NEXT]->(next:RAGChunk)
            OPTIONAL MATCH (node)-[:MENTIONS]->(entity:RAGEntity)
        """
        context = graph_context if self.settings.rag_retrieval_mode == "hybrid" else ""

        projection = f"""
            MATCH (document:RAGDocument)-[:HAS_CHUNK]->(node)
            {context}
            RETURN node.id AS chunk_id, document.title AS title,
                   document.source AS source, node.text AS text, score,
                   {"previous.text" if context else "null"} AS previous_text,
                   {"next.text" if context else "null"} AS next_text,
                   {"collect(DISTINCT entity.name)" if context else "[]"} AS entities
            ORDER BY score DESC
        """
        search_query = f"""
            CYPHER 25
            MATCH (node:RAGChunk)
            SEARCH node IN (
                VECTOR INDEX {self.settings.rag_vector_index}
                FOR $embedding
                LIMIT $top_k
            ) SCORE AS score
            {projection}
        """
        legacy_query = f"""
            CALL db.index.vector.queryNodes($index_name, $top_k, $embedding)
            YIELD node, score
            {projection}
        """
        parameters = {
            "index_name": self.settings.rag_vector_index,
            "top_k": top_k,
            "embedding": list(embedding),
        }
        try:
            records = await asyncio.to_thread(self._execute_read, search_query, parameters)
        except Exception as exc:
            code = str(getattr(exc, "code", ""))
            if not code.startswith("Neo.ClientError.Statement"):
                raise
            records = await asyncio.to_thread(self._execute_read, legacy_query, parameters)
        return [self._to_chunk(record) for record in records]

    def _execute_write(self, query: str, parameters: dict[str, Any]) -> None:
        with self._driver.session(database=self.settings.neo4j_database) as session:
            session.run(query, parameters).consume()

    def _execute_read(self, query: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
        with self._driver.session(database=self.settings.neo4j_database) as session:
            return [record.data() for record in session.run(query, parameters)]

    @staticmethod
    def _to_chunk(record: dict[str, Any]) -> RetrievedChunk:
        context_parts = [record.get("previous_text"), record.get("text"), record.get("next_text")]
        context = "\n\n".join(str(part) for part in context_parts if part)
        entities = [str(item) for item in record.get("entities", []) if item]
        if entities:
            context += "\n\nRelated entities: " + ", ".join(entities)
        return RetrievedChunk(
            chunk_id=str(record["chunk_id"]),
            title=str(record.get("title") or "Internal knowledge"),
            source=str(record.get("source") or f"rag://chunk/{record['chunk_id']}"),
            text=str(record.get("text") or ""),
            context=context,
            score=max(0.0, min(1.0, float(record.get("score") or 0.0))),
        )


def chunk_text(text: str, *, size: int, overlap: int) -> list[str]:
    """Split text into stable character windows without dropping content."""

    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not normalized:
        return []
    if overlap >= size:
        raise ValueError("Chunk overlap must be smaller than chunk size")
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + size, len(normalized))
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = end - overlap
    return chunks


def load_document(path: Path) -> RAGDocument:
    """Load a UTF-8 text/Markdown file or a PDF when the RAG extra is installed."""

    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8")
    elif suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("PDF support requires: uv sync --extra rag") from exc
        reader = PdfReader(path)
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        raise ValueError("Supported document types: .txt, .md, .pdf")
    if not text.strip():
        raise ValueError(f"Document has no extractable text: {path}")
    return RAGDocument(title=path.stem, source=path.resolve().as_uri(), text=text)
