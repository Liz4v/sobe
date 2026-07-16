# Architect: First-Run Onboarding (Tutorial Pointer)

> Phase 2 — Design decisions. Approved before coding begins.
> Implementation checklist is in tasks.md.

## Approach

Two independent, small changes, exactly matching Delta.md's ADDED/MODIFIED sections:

1. **Reorder `main()`** in [src/sobe/main.py](../../src/sobe/main.py) so `args = parse_args()`
   runs first, before the `load_config()` try/except block. `--help` and `--version`
   already `raise SystemExit(0)` inside argparse, so once parsing runs first, those two
   never reach `load_config()`. Bare invocation (`num_arg_types == 0`) is different by
   design: it must keep today's first-run behavior, so `parse_args()` no longer prints
   help and exits there. Instead it sets `args.bare = True` and returns early, skipping
   the rest of validation (set the attribute only after `num_arg_types` is computed, so
   the new key can never perturb that count; all other paths set `args.bare = False` at
   the same point). `main()` then runs the config phase as today — `MustEditConfig` /
   `ConfigError` handling, migration notice — and only afterwards checks
   `if args.bare: _build_parser().print_help(); raise SystemExit(0)`. To make that help
   print possible outside `parse_args()`, the parser construction block (the
   `ArgumentParser(...)` + `add_argument` calls, verbatim) moves into a module-level
   helper `_build_parser() -> argparse.ArgumentParser` that `parse_args()` also uses —
   a pure extraction, no argument definitions change. Everything downstream of
   `load_config()` (`config.select(args.target)`, `AWS(target)`, flag dispatch) is
   untouched and still reads `args`; the bare path exits before ever reaching
   `config.select`, so the early-returned Namespace (which lacks `paths` and prefix
   normalisation) is never consumed.

2. **Add a tutorial pointer** to both `MustEditConfig` branches. A new module-level
   constant `TUTORIAL_URL` in `main.py` (the module that owns all user-facing output,
   per AGENTS.md) holds the Read the Docs URL. One extra `print()` call, shared by both
   branches (identical text either way — only the first line differs by `err.created`),
   runs immediately after the existing `print(err.path)`.

This fits the existing module split: `main.py` is the only place CLI text is printed, so
the new constant and message line belong there, not in `config.py`. `config.py`'s
`MustEditConfig(path, created)` signature is unchanged, per Analyst.md's explicit
constraint — `main.py` decides what to print, `config.py` only decides *whether* to raise.

A new Sphinx page, `docs/tutorial.md`, becomes the tutorial's home and is the target of
`TUTORIAL_URL`. Its content is fleshed out from
[`TutorialOutline.md`](TutorialOutline.md) into a real prose walkthrough: each outline
section becomes a `##` header in the same order, and each terse bullet becomes one or
more explanatory sentences — enough for a beginner to actually follow the step, not just
a heading with a fragment under it. The outline's first-person voice ("I, the sole author
of Sobe...") carries over into the page; this is a personal, opinionated tutorial, not
generic reference prose. Every fact, warning, placeholder value (bucket names, example
IDs like `E1111111111111`, the `files.example.com` CNAME example), and the affiliate link
stays exactly as drafted — only the terseness changes, not the substance or order. The
two CNAME record lists become MyST pipe tables (confirmed working:
`myst_parser.parsers.mdit.py` calls `.enable("table")` unconditionally, no
`myst_enable_extensions` change needed in `docs/conf.py`).

### Why not more

Per Analyst.md's Excluded list, no wizard code, no input validation/prompting, no live
AWS calls, no `--policy` auto-print, and no changes to `DEFAULT_TEMPLATE`,
`is_unconfigured()`, or `Target`/`Config.from_dict()`. This plan touches exactly the two
`MustEditConfig` print branches and `main()`'s statement order — nothing else in
`main.py`'s control flow changes.

## First-Run Behavior Contract

| Invocation | Config file state | `load_config()` reached? | Printed (in order) | Exit code |
|---|---|---|---|---|
| `--help` | any | No | argparse help | 0 |
| `--version` | any | No | `sobe <version>` | 0 |
| bare `sobe` | missing | Yes | "Created config file..." / path / `Full setup tutorial: <TUTORIAL_URL>` | 1 |
| bare `sobe` | exists, unconfigured | Yes | "...is not configured yet..." / path / `Full setup tutorial: <TUTORIAL_URL>` | 1 |
| bare `sobe` | exists, configured | Yes | argparse help (after migration notice, if any) | 0 |
| upload/list/delete/etc. | missing | Yes | "Created config file..." / path / `Full setup tutorial: <TUTORIAL_URL>` | 1 |
| upload/list/delete/etc. | exists, unconfigured | Yes | "...is not configured yet..." / path / `Full setup tutorial: <TUTORIAL_URL>` | 1 |
| upload/list/delete/etc. | exists, configured | Yes | unchanged today's behavior | varies |
| upload/list/delete/etc. | old schema, real values | Yes | migration notice, then normal flow | varies |
| upload of a nonexistent local file | any (incl. missing) | No | "The following files do not exist" + list | 1 |
| invalid flag combination / unknown flag | any (incl. missing) | No | argparse usage error (stderr) | 2 |

`TUTORIAL_URL = "https://sobe.readthedocs.io/en/latest/tutorial.html"` — matches the
existing RTD URL pattern already used in `README.md` (`.../en/latest/usage.html#...`).

Exact message text:

```
Created config file at the path below. You must edit it before use.
<path>
Full setup tutorial: https://sobe.readthedocs.io/en/latest/tutorial.html
```

```
The config file at the path below is not configured yet. You must edit it before use.
<path>
Full setup tutorial: https://sobe.readthedocs.io/en/latest/tutorial.html
```

## Data Model Changes

No schema changes. No config changes. No new CLI flags. One new synthesized
`argparse.Namespace` attribute, `bare` (set by `parse_args()` after `num_arg_types` is
computed, same precedent as the existing synthesized `paths`); no new attributes come
from argparse itself.

## Files to Create

| File | Purpose |
|------|---------|
| `docs/tutorial.md` | New Sphinx/MyST page: full onboarding walkthrough, transcribed from `TutorialOutline.md`. Target of `TUTORIAL_URL`. |

## Files to Modify

| File | Change |
|------|--------|
| `src/sobe/main.py` | Move `args = parse_args()` above the `load_config()` try/except in `main()`; extract `_build_parser()`; bare invocation sets `args.bare` and defers help until after the config phase; add `TUTORIAL_URL` constant; add the shared tutorial-pointer `print()` line in the `MustEditConfig` handler. |
| `tests/test_main.py` | Update `test_bad_config_created` / `test_bad_config_existing_unconfigured` to assert the new tutorial-pointer print; add `bare=False` to `TestMain._mock_args`; update the two tests that assert `parse_args` self-prints help on bare input; add tests proving `--help`/`--version` never call `load_config()` and that bare `sobe` runs the config phase then help. |
| `docs/index.md` | Add `tutorial` as the first entry in the existing "User Guide" toctree. |
| `docs/usage.md` | Update the Installation first-run transcript (command stays `$ sobe` — bare first run is retained) to show all three printed lines; add a one-line cross-reference to the new Tutorial page. |
| `docs/configuration.md` | Opening sentence gains a parenthetical: `--help`/`--version` answer without reading or creating the config; "Unconfigured configs" section: mention the tutorial pointer now included in the printed message. |
| `AGENTS.md` | Update the "Flow:" sentence in Architecture — `parse_args()` now runs before `load_config()`, and bare invocation prints help only after the config phase. |
| `specs/1.0-release.md` | Annotate item 2 as resolved via `specs/first-run-onboarding/`. |

## Dependencies Between Steps

- Tasks 2–3 (tests) depend on Task 1 (`main.py`) — they assert its exact output and
  call sequence.
- Task 5 (`docs/index.md` toctree entry) depends on Task 4 (`docs/tutorial.md` must
  exist — Sphinx's toctree resolves file paths at build time).
- Tasks 6–8 (`usage.md`, `configuration.md`, `AGENTS.md`) each quote the exact message
  text or call order from Task 1 and so depend on it; they do not depend on each other
  or on Tasks 4–5.
- Task 9 (`specs/1.0-release.md` annotation) has no code dependency.
- Task 10 (full verification gate) depends on everything above.

## Parallelisation Opportunities

- **File locks:** `src/sobe/main.py` (Task 1) is standalone. `tests/test_main.py`
  (Tasks 2–3) is a single-file lock, sequential within itself.
- Task 4 (`docs/tutorial.md`, new file) has no dependency on Task 1 and can start
  immediately, in parallel with Tasks 1–3.
- Task 5 must wait for Task 4 (same reasoning as above) but is a different file, so it
  doesn't block or get blocked by Tasks 1–3.
- Once Task 1 lands, Tasks 6, 7, and 8 touch three distinct files
  (`usage.md`, `configuration.md`, `AGENTS.md`) and are mutually independent — safe to
  run in parallel with each other and with Tasks 4–5.
- Task 9 (`specs/1.0-release.md`) is independent of everything and can run at any point.
- Task 10 is strictly last.

## Risks & Open Questions

Known risks Phase 3 (Critic) should scrutinise:

- **[Superseded 2026-07-15, user decision] Bare-`sobe` first run is retained.** Harden
  Round 1 had corrected the docs/outline away from "run `sobe` once" because the
  original design made bare invocation exit 0 without touching config. The user then
  decided bare `sobe` should keep today's first-run behavior, so the design gained the
  `args.bare` flag + `_build_parser()` extraction, and all those doc corrections were
  reverted — "run `sobe` once" is accurate again. See CriticReview.md's post-harden
  scope-change section for the full audit trail.

- **"- Link." placeholder in TutorialOutline.md's "Create an AWS account" section.**
  The outline has a bare bullet reading `- Link.` where an AWS sign-up hyperlink
  clearly belongs. Since fleshing out prose is now explicitly in scope (Analyst.md
  updated), this resolves straightforwardly as `[Create an AWS account](https://aws.amazon.com/)`
  woven into a full sentence, same as every other bullet gets expanded. No longer a
  boundary case — noted here only so the Coder doesn't skip it as "just a placeholder."
- **`TUTORIAL_URL` slug and page location are a Phase 2 judgment call**, per Analyst.md's
  explicit deferral ("exact URL/path decided in Phase 2/Architect"). `docs/tutorial.md` ->
  `.../en/latest/tutorial.html`, placed first in the existing "User Guide" toctree
  alongside `usage`/`configuration`. Critic should sanity-check this reads naturally
  and that no RTD-side redirect/override in `.readthedocs.yaml` or `conf.py`
  contradicts the inferred URL pattern (there is none today).
- **Reordering `parse_args()` before `load_config()`** changes which failure a
  malformed invocation surfaces first (e.g., an unknown flag now always errors via
  `parser.error()`, exit 2, even when the config file is also broken) — this matches
  Analyst.md's intent but Critic should grep `tests/test_main.py` for any test that
  implicitly assumed `load_config()` ran before argument errors could surface (none
  found in this pass, since `TestMain` always mocks `parse_args` directly, but worth an
  independent check).
- **Sphinx build cleanliness.** `nitpicky = True` is set in `conf.py`, and
  `.readthedocs.yaml` builds `formats: all` (PDF via pdflatex). Neither the HTML nor
  LaTeX build commands in AGENTS.md pass `-W` (fail-on-warning), so a broken toctree
  entry or bad cross-reference would only show as a build-log warning, not a failing
  command. Task 10 must include an actual `-b html` build and eyeball the output for new
  warnings introduced by `docs/tutorial.md` / `docs/index.md`, matching existing project
  practice (no `-W` precedent to follow here).

## Rollback

Two independent surfaces, neither touching persisted state or schemas. Revert order:
`git revert` of the implementation commit(s) restores today's `main()` order and message
text wholesale; `docs/tutorial.md` and its toctree entry can be reverted independently of
`main.py` since nothing at runtime depends on the doc page existing (a dead `TUTORIAL_URL`
link degrades gracefully — it's just printed text).

## Architect Checklist

- [x] Approach fits existing project patterns (all parsing/output stays in `main.py`;
      `config.py`/`aws.py` untouched)
- [x] API contract defined before any code (First-Run Behavior Contract table above)
- [x] Schema changes identified (explicitly none)
- [x] Auth and ownership checks included in plan (n/a — local CLI, no auth surface)
- [x] No step requires modifying multiple unrelated files
- [x] Parallelisation opportunities and file locks declared
- [x] Notification/event needs considered for mutations affecting live state (n/a — no
      live-state mutations; the one new message is the tutorial-pointer print line,
      specified above)
