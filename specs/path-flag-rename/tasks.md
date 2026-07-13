# Tasks: `-p/--path` rename (CLI 1.0 freeze, final item)

> Phase 2 output — implementation checklist.
> Each step is atomic: one file created, one migration, one component.
> Dependencies and parallelisation opportunities are documented in Architect.md.

### Layer: CLI (`src/sobe/main.py`)

- [ ] Step 1: Rewire flag registration in `parse_args()` — add
  `-p/--path` (help: `set remote directory (usually a year)`) in the slot
  where `-y/--year` sits today; re-register `-y/--year` directly after it
  with help `deprecated alias for --path (removed in 2.0)`; make `--policy`
  long-only by dropping its `"-p"` string; reword `-l/--list` help from
  `list all files in the year` to `list all files in the path`. Add
  `import sys` to the module imports. Done when: `parse_args(["--help"])`
  output shows the new flag layout (manual check; asserted by tests in
  Step 5).
- [ ] Step 2: Add the alias-consolidation block immediately after
  `parser.parse_args(argv)` and before the `num_arg_types` line: if
  `args.year is not None` — error out via `parser.error("--path and --year
  cannot be used at the same time")` when `args.path` is also not None
  (wording matches the existing `--list`/`--delete` conflict error);
  otherwise
  print exactly `warning: --year is deprecated, use --path; it will be
  removed in sobe 2.0` to `sys.stderr` and copy `args.year` into
  `args.path`. Done when: alias invocations behave identically to `--path`
  and the conflict errors with exit 2.
- [ ] Step 3: Replace the `args.year` validation/normalization block with the
  `args.path` version — default to current year when None; error message
  reworded to `--path requires files or --list to be specified`; then
  `args.path = args.path.lstrip("/")`; then compute `args.prefix` from
  `args.path` with the existing trailing-slash logic unchanged. Done when:
  `--path /2024` yields prefix `2024/`, `--path /` and `--path //` yield
  `""`, and no line in `parse_args()` reads `args.year` after Step 2's block.

### Layer: Tests (`tests/test_main.py`)

- [ ] Step 4: Migrate existing tests to the new surface — rename
  primary-semantics `TestParseArgs` tests from `--year` spellings and
  `args.year` assertions to `--path`/`args.path` (keeping `prefix`
  assertions). Two non-obvious cases: (a) after the change `args.year` is
  `None` unless the alias was typed, so tests that assert `args.year`
  equals the default/given value (`test_parse_args_default_year`,
  `test_parse_args_list_only`, `test_parse_args_list_with_year`,
  `test_parse_args_with_year_and_files`, `test_year_empty_string`,
  `test_year_subfolder*`) must assert `args.path` instead; (b) the tests
  that spell `--year` without asserting it
  (`test_parse_args_year_without_files_error`,
  `test_parse_args_policy_with_other_args_error`,
  `test_parse_args_policy_with_target_and_more_error`) migrate to `--path`
  so the frozen contract is tested through the primary flag. Watch the
  one-letter `path` (new str) vs `paths` (existing `list[Path]`)
  distinction throughout — both live in the same namespace. Update
  `test_parse_args_policy_only` (add `args.path is None`); update
  `_mock_args` in `TestMain` to build the real namespace shape (`path=`
  kwarg canonical, `year=None`, `prefix` derived from `path`). Done when:
  full suite passes with no test still exercising primary semantics
  through the alias.
- [ ] Step 5: Add new tests covering the contract — (a) `-y`/`--year` alias
  works everywhere `--path` does (upload-shape and `--list`) and emits the
  exact warning line on **stderr** (capsys: `err` contains it, `out` does
  not) exactly once; (b) `--path X --year Y` → SystemExit code 2, in both
  short/long spellings; (c) `-p` is `--path`: `parse_args(["-p", "2024",
  file])` sets `args.path`, and bare `sobe -p` → SystemExit 2; (d) `--policy`
  still works long-only and `-p file.txt` followed by no positionals hits
  the `--path requires files or --list` error; (e) leading-slash
  normalization: `/`, `//`, `/2024`, `//2024/`, and `-y /` (alias gets
  normalization + warning), plus `--path /` alone -> SystemExit 2 (truthy
  at the num-check, so it errors instead of printing help like `--path ''`
  alone does); (f) `--help` output contains the substrings
  `--path` and `deprecated alias for --path (removed in 2.0)` — do NOT
  assert the joined form `-p, --path`: argparse only prints that layout on
  Python >= 3.13, while 3.11/3.12 print `-p PATH, --path PATH`, and the
  suite must pass on the full 3.11-3.14 matrix; (g) validation error
  wording names `--path`, asserted through both spellings: `--path 2024`
  with no files and `--year 2024` with no files (alias route) each exit 2
  with a message naming `--path`. Done when: all Analyst.md edge-case rows
  have a matching test and the suite passes.

### Layer: Documentation

- [ ] Step 6: Update `docs/usage.md` — retitle/reword the "different
  directory" section around `--path`; convert all `--year` examples to
  `--path`; replace the `--year ''` root example with `--path /` as the
  recommended root spelling (keep `''` mentioned as equivalent); update the
  `--remote-name` + prefix example and the `--list` examples; add a short
  deprecation note: `--year`/`-y` are deprecated aliases removed in sobe
  2.0, and `-p` no longer means `--policy`. Also note that leading slashes
  are now stripped, so object keys starting with `/` (a 0.x footgun) can no
  longer be created — and pre-existing ones can no longer be listed or
  deleted through sobe; removing them requires the AWS console or CLI.
  Keep the page ASCII-only. Done when: no `--year` example remains except
  in the deprecation note.
- [ ] Step 7: Update `specs/1.0-release.md` — annotate item 3's `--path`
  decision and open question 1 as implemented via `specs/path-flag-rename/`,
  recording the settled 2.0 removal timeline and the leading-slash
  normalization. Done when: a reader of item 3 sees the work is shipped, not
  pending.
- [ ] Step 8: Update `AGENTS.md` (CLAUDE.md symlinks to it) — in the
  Architecture section's CLI notes: `-p` belongs to `--path`, `--policy` is
  long-only, `-y/--year` are deprecated aliases (removed in 2.0); drop
  "`--year` naming" from the open-decisions example so the file stops
  advertising a resolved question. Done when: AGENTS.md matches the shipped
  flag surface.

### Layer: Verification

- [ ] Step 9: Run the full gate — `uv run pytest` (coverage ≥95% enforced),
  `uv run ruff check`, `uv run ruff format --check`, and
  `grep -rnP '[^\x00-\x7F]' docs --include='*.md'` (must be empty). Done
  when: all four pass clean.
