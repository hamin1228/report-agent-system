from report_agent.agents.writer import WriterAgent
from report_agent.models import ReportSection, SectionResearch, Source


def test_unknown_citations_are_removed() -> None:
    research = SectionResearch(
        section_title="Architecture",
        sources=[Source(title="Official", url="https://example.com/official")],
    )
    section = ReportSection(
        title="Architecture",
        content="Content",
        citations=["https://example.com/official", "https://invented.example/claim"],
    )
    validated = WriterAgent._validate_section_citations(section, research)
    assert validated.citations == ["https://example.com/official"]
