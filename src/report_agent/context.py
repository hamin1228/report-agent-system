"""Simple context compaction helpers for persisted artifacts."""

import json
from pathlib import Path
from typing import Any


class ContextManager:
    """Loads full artifacts only when needed and provides compact summaries otherwise."""

    @staticmethod
    def artifact_summary(path: Path) -> str:
        data: Any = json.loads(path.read_text("utf-8"))
        if path.name == "outline.json":
            return f"Outline '{data['title']}' with {len(data['sections'])} sections at {path}"
        if path.name == "research.json":
            source_count = sum(len(item.get("sources", [])) for item in data.values())
            return f"Research for {len(data)} sections with {source_count} source entries at {path}"
        if path.name == "report.json":
            return f"Report '{data['title']}' with {len(data['sections'])} sections at {path}"
        return f"Artifact at {path}"

    @staticmethod
    def read_artifact(path: Path) -> Any:
        return json.loads(path.read_text("utf-8"))
