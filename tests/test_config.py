import os
from pathlib import Path

import pytest

from report_agent.config import Settings, load_environment


def test_load_environment_without_overriding_existing_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "OPENAI_API_KEY=from-file\nTAVILY_API_KEY=from-file\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("OPENAI_API_KEY", "from-runtime")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    assert load_environment(env_file)
    assert os.environ["OPENAI_API_KEY"] == "from-runtime"
    assert os.environ["TAVILY_API_KEY"] == "from-file"


def test_rag_requires_enablement_and_credentials() -> None:
    disabled = Settings(
        rag_enabled=False,
        neo4j_uri="neo4j://localhost:7687",
        neo4j_password="secret",
    )
    configured = Settings(
        rag_enabled=True,
        neo4j_uri="neo4j://localhost:7687",
        neo4j_password="secret",
    )

    assert not disabled.rag_configured
    assert configured.rag_configured
