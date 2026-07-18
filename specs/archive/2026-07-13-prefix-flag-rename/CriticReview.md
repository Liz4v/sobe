# Critic Review: `-p/--prefix` rename (CLI 1.0 freeze, final item)

> Phase 3 — Plan stress-test. Approved before coding begins.
> This review went through two rounds. Round 1 = self-critique.
> Round 2 = fresh-eyes adversarial pass by an independent agent.

> **Post-review naming update (2026-07-13):** both review rounds below were
> conducted against a design named `-p/--path` with a two-hop
> `year -> args.path -> args.prefix` value flow. Before implementation began,
> the flag was renamed to `-p/--prefix`, which let the design collapse to a
> single `args.prefix` attribute (no intermediate `path` field) — see
> Architect.md's "Validation + normalization" section. This is a strict
> simplification, not a new design surface: it removes the `args.path` vs
> `args.paths` collision that Round 2 flagged as R2-W2 below rather than
> introducing a new one. Nothing else in either round's findings changed in
> substance. Quotes below of literal old text (e.g. `-p, --path`) are kept
> verbatim as an accurate historical record of what was reviewed at the time.

## Round 2 (fresh-eyes) — findings

A second adversarial pass by an independent agent with a fresh context
window (2026-07-13) found 0 additional blockers, 2 warnings, and 2 notes
that Round 1 missed. All four have been applied. The agent also
independently re-derived the `num_arg_types` audit against the real code
and confirmed it, and empirically verified the bare `-p` and ambiguous
`--p` behaviour on the local interpreter.

### Round 2 Blockers

None found.

### Round 2 Warnings (applied)

| ID | Finding | Where fixed |
|----|---------|-------------|
| R2-W1 | Step 4's migration enumeration omitted `test_parse_args_year_without_files_error` (spells `--year`, asserts neither `args.year` nor `--policy`, so it fell through both enumerated cases); relatedly, no Step 5 item covered the Analyst edge row "`--year 2024` with no files and no `--list`" through the alias. | tasks.md Step 4 case (b) now lists the test; Step 5(g) now asserts the requires-files error through both `--prefix` and `--year` spellings |
| R2-W2 | The one-letter `args.path` (new str) vs `args.paths` (existing `list[Path]`, main.py:130/63) collision was nowhere acknowledged — a prime typo/drift spot, especially in `_mock_args`. Also Architect.md's "`main()` consumes only `args.prefix` and flags" was inaccurate (it also reads `paths`, `remote_name`, `content_type`), though the no-change conclusion still holds. | Architect.md: corrected the `main()` consumption sentence + hazard note in "Data Model Changes"; tasks.md Step 4 warns about the distinction |

### Round 2 Notes (applied — both were cheap)

| ID | Finding | Where fixed |
|----|---------|-------------|
| R2-N1 | Conflict-error wording `"cannot be used together"` diverged from the existing parser pattern `"cannot be used at the same time"` (main.py:123). | Architect.md snippet + CLI contract row + tasks.md Step 2 now use `"--prefix and --year cannot be used at the same time"` |
| R2-N2 | Undocumented asymmetry: `--prefix ''` alone prints help and exits 0 (frozen quirk) while the newly recommended `--prefix /` alone errors with exit 2 (truthy at the flag count, falsy only after `lstrip`). Defensible but absent from the edge table. | Analyst.md edge table gained the row; tasks.md Step 5(e) tests it |

### Round 2 overrode Round 1

None — no Round 2 fix touched anything Round 1 changed.

### Round 2 assumptions verified TRUE (highlights)

- Every symbol/line the spec cites in main.py and test_main.py exists as
  quoted; no `patch("sobe.main....")` target is broken by the plan
  (TestMain patches `parse_args` wholesale).
- docs/usage.md content matches Step 6's inventory; Files-to-Modify is
  complete across README, docs/, docs/api/, `.github/`, and src/.
- No contradiction with `specs/1.0-release.md` or the archived
  multi-target spec — the latter explicitly reserved `-p`/`--path` (the
  archive predates this spec's later `--prefix` rename and is frozen text)
  for this promotion (archive/2026-07-12-multi-target/Architect.md:254).
- No project-rule violations (stdout discipline exception sanctioned,
  ruff 120, coverage, markers, no `warnings.filterwarnings` interaction).

### Round 2 residual risks (couldn't be verified offline)

- Behaviour on 3.11/3.12/3.14 was reasoned from documented argparse
  changes, not executed — only 3.13 is installed locally. The 1.0 CI
  matrix (release spec item 1) is the backstop.

---

## Round 1 (self-critique) — findings

Scope class: Medium (light pass, all eight lenses touched). Verdict:
**Needs revision** — 1 blocker, 3 warnings, 3 notes; all applied or
explicitly dispatched below.

### Blockers

| ID | Lens | Finding | Where fixed |
|----|------|---------|-------------|
| R1-B1 | Testing | tasks.md Step 5(f) told the coder to assert the substring `-p, --path` in `--help` output. That joined layout is Python >= 3.13 argparse formatting; 3.11/3.12 print `-p PATH, --path PATH`. The 1.0 release spec (item 1) adds a 3.11-3.14 CI matrix, where the test would fail. | tasks.md Step 5(f) rewritten to assert version-agnostic substrings; matching risk bullet added to Architect.md "Risks" |

### Warnings

| ID | Lens | Finding | Where fixed |
|----|------|---------|-------------|
| R1-W1 | Completeness | `-l/--list` help text `"list all files in the year"` (main.py:87) is user-facing text tied to the old flag's concept; neither spec file updated it. | tasks.md Step 1 + Architect.md Approach item 1: reword to `"list all files in the path"` |
| R1-W2 | Data integrity / Docs | Leading-slash stripping makes legacy footgun keys (e.g. `/2024/f.txt` created by 0.x) unreachable through sobe — in 0.x `-y /2024 --delete f.txt` could delete them; in 1.0 nothing can. Deliberate, but the cleanup-path loss was undocumented. | tasks.md Step 6 (docs note: clean legacy keys via AWS console/CLI); Architect.md Risks bullet |
| R1-W3 | Testing | Step 4's migration list was generic; two non-obvious cases needed calling out: (a) post-change `args.year` is `None` unless the alias was typed, so six tests asserting `args.year` values must move to `args.path`; (b) the two policy-combination tests spelling `--year` should migrate to `--prefix` to test the frozen contract through the primary flag. | tasks.md Step 4 enumerates both cases with test names |

### Notes

| ID | Finding | Disposition |
|----|---------|-------------|
| R1-N1 | argparse abbreviation `--p` was unambiguous for `--policy` in 0.x; adding `--prefix` makes it ambiguous (argparse errors). Abbreviations are undocumented surface. | Accepted, no action |
| R1-N2 | Rollback strategy was undocumented. | Applied — "Rollback" section added to Architect.md (cheap) |
| R1-N3 | `sobe --year X --version` exits inside argparse before the consolidation block, so no deprecation warning is emitted. Non-contractual per Analyst.md. | Accepted, no action |

### Load-bearing claims independently re-derived (verified TRUE)

- **`num_arg_types` audit** (Architect flagged this for scrutiny): re-derived
  against both consumer branches with the real namespace
  (`target, year, path, content_type, list, delete, invalidate, policy,
  remote_name, files`). Help-at-zero: consolidation copies falsy to falsy,
  so `--prefix ''` alone mirrors the existing `--year ''` help quirk; no new
  reachability. `--policy` count check: alias double-count only inflates
  invocations already rejected; `--policy --target x --year ''` stays
  accepted (both values falsy) with a stderr warning — explicitly
  non-contractual per Analyst.md. Holds.
- **stderr via print partial:** `print = functools.partial(print, flush=True)`
  pins only `flush`; `file=sys.stderr` passes through. `import sys` is
  genuinely absent from main.py today. capsys captures it because
  `sys.stderr` is resolved at call time.
- **Files-to-Modify list is complete for flag mentions:** README.md contains
  no `--year`/`-p`/`--policy` references; `docs/configuration.md`,
  `docs/index.md` clean; `docs/api/cli.md` is autodoc-only (module docstring
  names no flags); `AGENTS.md` line 29 mention covered by Step 8;
  `specs/1.0-release.md` covered by Step 7. No `specs/STATE.md` exists in
  this repo.
- **Warning line length** fits ruff's 120-char limit at its indentation.
- Edge-case rows in Analyst.md each map to a Step 5 test group.
