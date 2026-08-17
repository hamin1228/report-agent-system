"""Command-line interface for the report agent system."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Confirm, Prompt

from report_agent.config import Settings
from report_agent.llm import LLMClient
from report_agent.models import Outline
from report_agent.orchestrator import ReportOrchestrator
from report_agent.rag.neo4j_store import Neo4jGraphStore, chunk_text, load_document

app = typer.Typer(no_args_is_help=True, help="Generate researched reports with multiple agents.")
console = Console()


@app.callback()
def main() -> None:
    """Multi-agent report generation commands."""


async def _approve_outline(outline: Outline) -> tuple[bool, str]:
    lines = [f"# {outline.title}", "", outline.objective, ""]
    for index, section in enumerate(outline.sections, 1):
        lines.append(f"{index}. **{section.title}** — {section.description}")
    console.print(Markdown("\n".join(lines)))
    if Confirm.ask("이 아웃라인으로 진행할까요?", default=True):
        return True, ""
    return False, Prompt.ask("수정할 내용을 입력하세요")


async def _run(request: str, requirements: str, approve: bool) -> None:
    orchestrator = ReportOrchestrator(Settings())
    report = await orchestrator.run(
        request,
        requirements=requirements,
        approval_handler=_approve_outline if approve else None,
        progress_handler=lambda phase, message: console.print(
            f"[cyan][{phase.value.upper()}][/cyan] {message}"
        ),
    )
    console.print(Markdown(report.to_markdown()))
    if orchestrator.store:
        console.print(f"\n[green]Saved to {orchestrator.store.run_dir}[/green]")


@app.command()
def generate(
    request: str = typer.Argument(..., help="Report topic or request"),
    requirements: str = typer.Option("", "--requirements", "-r"),
    approve: bool = typer.Option(True, "--approve/--no-approve"),
) -> None:
    """Generate a report and save Markdown/JSON artifacts."""
    try:
        asyncio.run(_run(request, requirements, approve))
    except KeyboardInterrupt:
        raise typer.Exit(130) from None
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc


@app.command("rag-ingest")
def rag_ingest(
    path: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
) -> None:
    """Embed and ingest a text, Markdown, or PDF document into Neo4j GraphRAG."""

    async def ingest() -> tuple[int, str]:
        settings = Settings()
        if not settings.rag_configured:
            raise RuntimeError(
                "Set REPORT_AGENT_RAG_ENABLED=true and the REPORT_AGENT_NEO4J_* variables"
            )
        document = load_document(path)
        chunks = chunk_text(
            document.text,
            size=settings.rag_chunk_size,
            overlap=settings.rag_chunk_overlap,
        )
        embeddings = await LLMClient(settings).embed(chunks)
        store = Neo4jGraphStore(settings)
        try:
            await store.verify_connectivity()
            await store.ensure_schema(len(embeddings[0]))
            count = await store.ingest(document, chunks, embeddings)
        finally:
            await store.close()
        return count, document.title

    try:
        count, title = asyncio.run(ingest())
        console.print(f"[green]Ingested {count} chunks from {title}[/green]")
    except Exception as exc:
        console.print(f"[red]RAG ingestion failed: {exc}[/red]")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    app()
