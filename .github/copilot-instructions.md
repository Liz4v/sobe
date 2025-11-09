# Copilot Instructions for `sobe`

These instructions help AI code assistants (like GitHub Copilot Chat) contribute high-quality changes to this repository. They define expectations for style, testing, safety, and prompting.

## Project Snapshot
- Purpose: AWS-based drop box uploader.
- Runtime: Python >=3.11.
- Entrypoint: `sobe.main:main` (installed as `sobe` script).
- Key deps: `boto3`, `platformdirs`.
- Dev tooling: `pytest`, `pytest-cov`, `ruff`.
- Test coverage gate: 95% (HTML report under `htmlcov/`).

## Commands
- Run unit tests: `uv run pytest`
- Run code linter and formatter: `uv run ruff`
- Run individual python file: `uv run path/to/filename.py`
- Build Sphinx docs: `uv run --extra docs -m sphinx -b html docs docs/_build/html`
- Required parameters go at the end of the commands above.

## Coding Conventions
- Use Python 3.11+ features.
- Line length: 120 (Ruff config).
- Prefer small pure functions; keep AWS SDK calls isolated for testability.
- Avoid premature abstraction; first duplication is OK, second deserves a helper.

## Configuration Handling
- User config file lives at: `PlatformDirs("sobe").user_config_path / "config.toml"`.
- Never hardcode secrets; only placeholders like `example.com` are acceptable.
- If adding new config keys: (1) extend `DEFAULT_TEMPLATE`, (2) update `Config.from_dict`, (3) add tests for default + custom values, (4) document in README.

## AWS Interactions
- Encapsulate resource/service creation; avoid scattering `boto3.client` calls.
- Ensure idempotency and clear error messages (include bucket/key identifiers).

## Testing Expectations
- All new code must have tests under `tests/`.
- Use markers: `@pytest.mark.unit`, `@pytest.mark.integration` when appropriate.
- Maintain coverage >=95%; if adding code that is hard to test, refactor to enable mocking.

## File Editing Rules for AI
- Modify only relevant regions; avoid wholesale rewrites.
- Preserve existing public APIs unless explicitly versioning.
- After adding features, update Python docstrings and Sphinx docs. README.md should not be modified unless it contains false information.

## Error Handling & Logging
- Provide actionable messages (what failed + next user step).
- Avoid printing to stdout except for CLI user feedback in `main.py`.

## Adding Dependencies
- Prefer stdlib first. Confirm with supervisor before any new external dependency: must significantly reduce complexity.
- Use uv to add: `uv add package-name`.
