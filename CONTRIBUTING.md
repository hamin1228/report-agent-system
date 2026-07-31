# Contributing

## Local setup

```bash
uv sync --extra dev
cp .env.example .env
```

API keys are only required for manual E2E tests. Unit tests must not call paid services.

## Development workflow

1. Create a focused branch from `main`.
2. Add or update tests with the implementation.
3. Update `README.md` when behavior or configuration changes.
4. Run all quality checks.
5. Open a pull request using the repository template.

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/report_agent
uv run pytest -q
uv build
```

Never commit `.env`, API keys, private prompts, or files under `workspace/`.

