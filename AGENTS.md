# Agent Instructions

This file provides guidance to AI coding agents when working with code in this repository.

## Project

`sobe` is a CLI tool (Python ≥3.11, managed with uv) that uploads files to an AWS S3 bucket served publicly through CloudFront — a classic "drop box". Files default to a directory named after the current year. Entry point: `sobe.main:main`.

## Commands

- Run tests: `uv run pytest` (coverage gate: 95%, enforced via `--cov-fail-under` in pyproject; HTML report in `htmlcov/`)
- Run a single test: `uv run pytest tests/test_main.py::test_name`
- Lint: `uv run ruff check` — Format: `uv run ruff format` (line length 120)
- Type check: `uv run ty check` (must pass clean; enforced in CI)
- Run a python file: `uv run path/to/file.py`
- Build Sphinx docs: `uv run --extra docs -m sphinx -b html docs docs/_build/html`
- Validate the docs PDF build locally (LaTeX toolchain via nix; plain `texliveMedium` lacks `fncychap`): `uv run --extra docs -m sphinx -b latex docs docs/_build/latex && nix-shell -p "texlive.combine { inherit (texlive) scheme-medium latexmk fncychap tabulary varwidth framed wrapfig upquote capt-of needspace titlesec; }" --run "make -C docs/_build/latex all-pdf"`
- Add a dependency: `uv add package-name` — but prefer stdlib; a new external dependency must significantly reduce complexity and be confirmed with the user first.

## Architecture

Three modules in `src/sobe/`, with a deliberate separation:

- `main.py` — CLI only: argument parsing/validation (`parse_args`) and all user-facing output. This is the only module that prints to stdout. Note it shadows `print`/defines `write` as flushing partials at module top.
- `aws.py` — all AWS interaction, encapsulated in the `AWS` class (S3 upload/delete/list, CloudFront invalidation, IAM policy generation). Keep boto3 calls isolated here; don't scatter `boto3.client(...)` elsewhere. `AWS` consumes one `Target`; the CloudFront client exists only when the target has a cache. `invalidate_cache()` is a generator that yields status while polling.
- `config.py` — TOML config handling. Config lives at `PlatformDirs("sobe").user_config_path / "config.toml"`. The schema is multi-target: `[target.<name>]` tables (each with required `storage`, optional `url`/`cache`, per-target `aws_session`/`aws_service` boto3 kwargs) plus a top-level `default` key; `Config.select()` implements the selection rules. `load_config()` returns `(Config, Migration | None)` and auto-migrates old single-`[aws]`-table files in place (backup at `config.toml.bak`, never overwritten). When the file is missing it writes `DEFAULT_TEMPLATE` and raises `MustEditConfig(created=True)`; when the file exists but is unconfigured (zero targets, or every bucket still the placeholder `example-bucket`) it raises `MustEditConfig(created=False)` without touching the file. Validation/selection failures raise `ConfigError`; `main()` catches both, prints, and exits 1.

Flow: `main()` parses args → loads config → prints migration notice if any → bare invocation prints help and exits 0 only after the config phase succeeds → `config.select(args.target)` → constructs `AWS(target)` → dispatches on flags (`--policy`, `--list`, upload/`--delete`, then optional `--invalidate`, skipped with a notice on cache-less targets).

The flag-combination validation in `parse_args()` is intricate (which flags require/exclude files, `--remote-name` single-file rule, `-t/--target` requiring an operation but combining with `--policy`, etc.) — read it before touching CLI behavior. `-t` belongs to `--target`; `--content-type` is long-only. `-p` belongs to `--prefix`; `--policy` is long-only. `-y`/`--year` are deprecated aliases for `--prefix` (removed in 2.0). An empty-string option value is deliberately equivalent to the flag being absent. Since 1.0, the CLI surface is a compatibility contract (see `specs/1.0-release.md`, audit notes under item 3): flags, config file format, and exit codes (0 success/help, 1 config problems or missing local files, 2 usage errors) are stable within a major version.

## Conventions

- When adding a config key: extend `DEFAULT_TEMPLATE`, update the relevant `from_dict`, add tests for default + custom values, document it.
- All new code needs tests in `tests/`; markers available: `unit`, `integration`, `slow` (strict markers enabled). If code is hard to test, refactor for mockability rather than lowering coverage.
- Error messages should include identifiers (bucket/key) and the user's next step.
- Preserve existing public APIs and CLI flags unless explicitly versioning — since 1.0 they are a compatibility contract; breaking changes ship only in a major bump.
- Add an entry to `CHANGELOG.md` (Keep a Changelog format) for every user-visible change.
- Update docstrings and Sphinx docs (`docs/`) after adding features. Don't modify README.md unless it contains false information.
- Doc pages are Markdown (MyST) — use fenced directives (```` ```{toctree} ````) and `{class}`/`{ref}` roles, not reST. Docstrings stay reST for autodoc.
- Keep doc pages ASCII-only: Read the Docs builds a PDF (`formats: all` in `.readthedocs.yaml`) with pdflatex, which dies on characters like `≥`. Check with `grep -rnP '[^\x00-\x7F]' docs --include='*.md'`.
- Never hardcode secrets; placeholders like `example.com` only.

## Releases

CI (`.github/workflows/test.yaml`) runs on PRs and pushes to `main`: pytest on Python 3.11-3.14 (all blocking, coverage gate applies) plus ruff check/format and ty. Publishing is tag-driven via `.github/workflows/pypi.yaml` (PyPI trusted publishing); `.github/scripts/validate_version.py` enforces that the git tag matches the pyproject version — literally, so pre-release tags must use the PEP 440 canonical spelling (`1.0.0rc1`).

Docs are hosted on Read the Docs (`.readthedocs.yaml`): each push to `main` rebuilds `latest` via webhook, installing the package fresh with `pip install .[docs]`, so docs dependencies come from the `docs` extra in pyproject.
