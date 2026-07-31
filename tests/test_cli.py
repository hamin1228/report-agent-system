from typer.testing import CliRunner

from report_agent.cli import app


def test_generate_is_an_explicit_subcommand() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "generate" in result.stdout
