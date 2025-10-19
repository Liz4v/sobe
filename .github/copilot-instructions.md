# Copilot Instructions for `sobe`

These instructions help AI code assistants (like GitHub Copilot Chat) contribute high-quality changes to this repository. They define expectations for style, testing, safety, and prompting.

## Project Snapshot
- Purpose: AWS-based drop box uploader.
- Runtime: Python >=3.11.
- Entrypoint: `sobe.main:main` (installed as `sobe` script).
- Key deps: `boto3`, `platformdirs`.
- Dev tooling: `pytest`, `pytest-cov`, `ruff`, `isort` (black profile).
- Test coverage gate: 95% (HTML report under `htmlcov/`).

## Commands
- Always use `uv` to run any Python code and python tools like `pytest`.

## Coding Conventions
- Use Python 3.11+ features (e.g. `typing.Self`, dataclasses, structural pattern matching) when they simplify code.
- Line length: 120 (Ruff config).
- Imports: follow `isort` + black profile grouping and ordering.
- Prefer small pure functions; keep AWS SDK calls isolated for testability.
- Raise precise exceptions; avoid catching broad `Exception` unless rethrowing with context.
- Avoid premature abstraction; first duplication is OK, second deserves a helper.

## Configuration Handling
- User config file lives at: `PlatformDirs("sobe").user_config_path / "config.toml"`.
- Never hardcode secrets; only placeholders like `example.com` are acceptable.
- If adding new config keys: (1) extend `DEFAULT_TEMPLATE`, (2) update `Config.from_dict`, (3) add tests for default + custom values, (4) document in README.

## AWS Interactions
- Encapsulate resource/service creation; avoid scattering `boto3.client` calls.
- Provide opt-in verification using `aws.service.verify` flag if adding network paths.
- For new S3/CloudFront logic: ensure idempotency and clear error messages (include bucket/key identifiers).

## Testing Expectations
- All new code must have tests under `tests/`.
- Use markers: `@pytest.mark.unit`, `@pytest.mark.integration` when appropriate.
- Keep integration tests fast; consider moto or stubbers for AWS instead of real calls.
- Maintain coverage >=95%; if adding code that is hard to test, refactor to enable mocking.

## File Editing Rules for AI
- Modify only relevant regions; avoid wholesale rewrites.
- Preserve existing public APIs unless explicitly versioning.
- After adding features, ensure docstring updates.
- Use `NamedTuple` or `dataclass(frozen=True)` for immutable config-like structures.

## Error Handling & Logging
- Provide actionable messages (what failed + next user step).
- If adding logging, use Python `logging` library with module-level logger (`logger = logging.getLogger(__name__)`).
- Avoid printing to stdout except for CLI user feedback in `main.py`.

## CLI Changes
- Keep `main.py` minimal; heavy logic should move to helpers in other modules.
- Support `--help` clarity: short flag names + descriptive help text.

## Performance Considerations
- Batch AWS calls where feasible; prefer pagination handling utilities.
- Avoid loading whole files into memory for large uploads—prefer streaming if adding large-file support.

## Security & Safety
- Never commit credentials or personal data.
- Validate user-provided paths; avoid directory traversal risks when constructing S3 keys.
- Sanitize or restrict bucket/key inputs (no leading '../').

## Adding Dependencies
- Prefer stdlib first.
- Justify any new dependency: must significantly reduce complexity.
- Pin with minimal version spec only if required (`pkg>=x.y.z`).
- Update `pyproject.toml` and consider lock strategy (uv).

## Git & PR Guidance
- Keep PRs focused; one logical change.
- Include rationale + before/after behavior in description.

## Review Checklist (AI or Human)
- [ ] Code passes `ruff` (style + lint).
- [ ] Tests added/updated and all pass.
- [ ] Coverage remains >=95%.
- [ ] No secrets or hardcoded sensitive values.
- [ ] README or docs updated if user-facing change.
- [ ] Errors and messages are clear.

## Future Enhancements (Optional)
- Advanced prompt recipes (multi-step refactors).
- Troubleshooting section (common AWS errors mapping).
- Guidelines for performance benchmarking.
- Structured changelog maintenance templates.

---
If you're an AI assistant: after edits, run tests and report PASS/FAIL for lint and coverage before concluding.
