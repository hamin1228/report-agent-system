import pytest

from report_agent.tools.web import WebTools


def test_low_quality_sources_are_rejected() -> None:
    assert not WebTools._is_allowed_source("https://namu.wiki/example")
    assert not WebTools._is_allowed_source("https://en.wikipedia.org/wiki/Agent")
    assert WebTools._is_allowed_source("https://www.ibm.com/think/topics/ai-agents")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/admin",
        "http://127.0.0.1/private",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.1/internal",
        "file:///etc/passwd",
        "https://user:password@example.com/",
    ],
)
async def test_private_fetch_destinations_are_rejected(url: str) -> None:
    with pytest.raises(ValueError):
        await WebTools._validate_public_url(url)
