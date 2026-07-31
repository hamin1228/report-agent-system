"""Run-scoped artifact persistence."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from report_agent.models import FinalReport, Outline, SectionResearch, WorkflowState


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        self.run_dir = root / f"run-{timestamp}-{uuid4().hex[:8]}"
        self.run_dir.mkdir(parents=True, exist_ok=False)

    def _write_json(self, name: str, payload: Any) -> Path:
        path = self.run_dir / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), "utf-8")
        return path

    def save_outline(self, outline: Outline) -> Path:
        return self._write_json("outline.json", outline.model_dump(mode="json"))

    def save_research(self, research: dict[str, SectionResearch]) -> Path:
        return self._write_json(
            "research.json",
            {name: item.model_dump(mode="json") for name, item in research.items()},
        )

    def save_report(self, report: FinalReport) -> tuple[Path, Path]:
        json_path = self._write_json("report.json", report.model_dump(mode="json"))
        markdown_path = self.run_dir / "report.md"
        markdown_path.write_text(report.to_markdown(), "utf-8")
        return markdown_path, json_path

    def save_state(self, state: WorkflowState) -> Path:
        """Persist a resumable workflow checkpoint after each phase."""

        return self._write_json("state.json", state.model_dump(mode="json"))
