from report_agent.models import FinalReport, ReportSection


def test_report_markdown() -> None:
    report = FinalReport(
        title="Test Report",
        executive_summary="Summary",
        sections=[ReportSection(title="Findings", content="Evidence")],
    )
    markdown = report.to_markdown()
    assert markdown.startswith("# Test Report")
    assert "## Executive Summary" in markdown
    assert "## Findings" in markdown
