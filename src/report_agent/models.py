"""Shared domain models passed between agents."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import AnyUrl, BaseModel, Field


class WorkflowPhase(StrEnum):
    CLARIFY = "clarify"
    OUTLINE = "outline"
    APPROVAL = "approval"
    RESEARCH = "research"
    WRITING = "writing"
    COMPLETE = "complete"
    FAILED = "failed"


class OutlineSection(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    research_questions: list[str] = Field(default_factory=list)


class Outline(BaseModel):
    title: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    sections: list[OutlineSection] = Field(min_length=2)


class Source(BaseModel):
    title: str
    url: AnyUrl
    snippet: str = ""
    content: str = ""
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    origin: str = "web"
    accessed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SectionResearch(BaseModel):
    section_title: str
    findings: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    complete: bool = False
    error: str = ""


class ReportSection(BaseModel):
    title: str
    content: str
    citations: list[str] = Field(default_factory=list)


class FinalReport(BaseModel):
    title: str
    executive_summary: str
    sections: list[ReportSection]
    references: list[Source] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", "", "## Executive Summary", "", self.executive_summary]
        for section in self.sections:
            lines.extend(["", f"## {section.title}", "", section.content])
        if self.references:
            lines.extend(["", "## References", ""])
            seen: set[str] = set()
            for source in self.references:
                url = str(source.url)
                if url not in seen:
                    seen.add(url)
                    lines.append(f"- [{source.title}]({url})")
        return "\n".join(lines).strip() + "\n"


class WorkflowState(BaseModel):
    request: str
    requirements: str = ""
    phase: WorkflowPhase = WorkflowPhase.CLARIFY
    outline: Outline | None = None
    research: dict[str, SectionResearch] = Field(default_factory=dict)
    report: FinalReport | None = None
    errors: list[str] = Field(default_factory=list)
