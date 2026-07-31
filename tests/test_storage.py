from pathlib import Path

from report_agent.models import (
    FinalReport,
    Outline,
    OutlineSection,
    ReportSection,
    WorkflowState,
)
from report_agent.storage import ArtifactStore


def test_artifact_store(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    outline = Outline(
        title="AI",
        objective="Explain AI",
        sections=[
            OutlineSection(title="Past", description="History"),
            OutlineSection(title="Future", description="Outlook"),
        ],
    )
    assert store.save_outline(outline).exists()
    report = FinalReport(
        title="AI",
        executive_summary="Summary",
        sections=[ReportSection(title="Past", content="Content")],
    )
    markdown, data = store.save_report(report)
    assert markdown.exists()
    assert data.exists()
    assert store.save_state(WorkflowState(request="Test")).exists()
