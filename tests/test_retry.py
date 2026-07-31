import pytest

from report_agent.retry import with_retry


@pytest.mark.asyncio
async def test_retry_eventually_succeeds() -> None:
    calls = 0

    async def flaky() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise RuntimeError("temporary")
        return "ok"

    result = await with_retry(flaky, attempts=3, base_delay_seconds=0.001)
    assert result == "ok"
    assert calls == 3
