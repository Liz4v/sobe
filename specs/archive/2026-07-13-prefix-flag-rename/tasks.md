# Tasks: `-p/--prefix` rename (CLI 1.0 freeze, final item)

> Phase 2 output — implementation checklist.
> Each step is atomic: one file created, one migration, one component.
> Dependencies and parallelisation opportunities are documented in Architect.md.

### Layer: CLI (`src/sobe/main.py`)

- [x] Step 1: Rewire flag registration in `parse_args()` — add
  `-p/--prefix` (help: `set remote directory (usually a year)`) in the slot
  where `-y/--year` sits today; re-register `-y/--year` directly after it
  with help `deprecated alias for --prefix (removed in 2.0)`; make `--policy`
  long-only by dropping its `"-p"` string; reword `-l/--list` help from
  `list all files in the year` to `list all files in the prefix`. Add
  `import sys` to the module imports. Done when: `parse_args(["--help"])`
  output shows the new flag layout (manual check; asserted by tests in
  Step 5).
- [x] Step 2: Add the alias-consolidation block immediately after
  `parser.parse_args(argv)` and before the `num_arg_types` line: if
  `args.year is not None` — error out via `parser.error("--prefix and --year
  cannot be used at the same time")` when `args.prefix` is also not None
  (wording matches the existing `--list`/`--delete` conflict error);
  otherwise
  print exactly `warning: --year is deprecated, use --prefix; it will be
  removed in sobe 2.0` to `sys.stderr` and copy `args.year` into
  `args.prefix`. Done when: alias invocations behave identically to `--prefix`
  and the conflict errors with exit 2.
- [x] Step 3: Replace the `args.year` validation/normalization block,
  operating directly on `args.prefix` (the `--prefix` flag's own dest, no
  separate intermediate attribute) — default to current year when None;
  error message reworded to `--prefix requires files or --list to be
  specified`; then `args.prefix = args.prefix.lstrip("/")`; then apply the
  existing trailing-slash logic in place: `args.prefix = args.prefix if
  args.prefix == "" or args.prefix.endswith("/") else f"{args.prefix}/"`.
  Note this removes the old `year` -> `path` -> `prefix` two-hop shape
  entirely: `--prefix`'s argparse dest is already named `prefix`, so the raw
  input and the normalized output live in the same attribute throughout.
  Done when: `--prefix /2024` yields `args.prefix == "2024/"`, `--prefix /`
  and `--prefix //` yield `""`, and no line in `parse_args()` reads
  `args.year` after Step 2's block.

### Layer: Tests (`tests/test_main.py`)

- [x] Step 4: Migrate existing tests to the new surface — rename
  primary-semantics `TestParseArgs` tests from `--year` spellings and
  `args.year` assertions to `--prefix`/`args.prefix`. Two non-obvious cases:
  (a) after the change `args.year` is `None` unless the alias was typed, so
  tests that assert `args.year` equals the default/given value
  (`test_parse_args_default_year`, `test_parse_args_list_only`,
  `test_parse_args_list_with_year`, `test_parse_args_with_year_and_files`,
  `test_year_empty_string`, `test_year_subfolder*`) must assert
  `args.prefix` instead; (b) the tests that spell `--year` without
  asserting it (`test_parse_args_year_without_files_error`,
  `test_parse_args_policy_with_other_args_error`,
  `test_parse_args_policy_with_target_and_more_error`) migrate to `--prefix`
  so the frozen contract is tested through the primary flag. Watch the
  `prefix` (the `--prefix` flag's value, str) vs `paths` (existing local
  files, `list[Path]`) distinction throughout — both live in the same
  namespace, though the names are visually distinct enough that this is a
  lighter hazard than the old `path`/`paths` pairing would have been. Update
  `test_parse_args_policy_only` (add `args.prefix is None`); update
  `_mock_args` in `TestMain` to build the real namespace shape (`prefix=`
  kwarg holds the final normalized value directly, no separate raw field;
  `year=None`). Done when: full suite passes with no test still exercising
  primary semantics through the alias.
- [x] Step 5: Add new tests covering the contract — (a) `-y`/`--year` alias
  works everywhere `--prefix` does (upload-shape and `--list`) and emits the
  exact warning line on **stderr** (capsys: `err` contains it, `out` does
  not) exactly once; (b) `--prefix X --year Y` → SystemExit code 2, in both
  short/long spellings; (c) `-p` is `--prefix`: `parse_args(["-p", "2024",
  file])` sets `args.prefix == "2024/"`, and bare `sobe -p` → SystemExit 2;
  (d) `--policy` still works long-only and `-p file.txt` followed by no
  positionals hits the `--prefix requires files or --list` error; (e)
  leading-slash normalization: `/`, `//`, `/2024`, `//2024/`, and `-y /`
  (alias gets normalization + warning), plus `--prefix /` alone ->
  SystemExit 2 (truthy at the num-check, so it errors instead of printing
  help like `--prefix ''` alone does); (f) `--help` output contains the
  substrings `--prefix` and `deprecated alias for --prefix (removed in
  2.0)` — do NOT assert the joined form `-p, --prefix`: argparse only
  prints that layout on Python >= 3.13, while 3.11/3.12 print `-p PREFIX,
  --prefix PREFIX`, and the suite must pass on the full 3.11-3.14 matrix;
  (g) validation error wording names `--prefix`, asserted through both
  spellings: `--prefix 2024` with no files and `--year 2024` with no files
  (alias route) each exit 2 with a message naming `--prefix`. Done when:
  all Analyst.md edge-case rows have a matching test and the suite passes.

### Layer: Documentation

- [x] Step 6: Update `docs/usage.md` — retitle/reword the "different
  directory" section around `--prefix`; convert all `--year` examples to
  `--prefix`; replace the `--year ''` root example with `--prefix /` as the
  recommended root spelling (keep `''` mentioned as equivalent); update the
  `--remote-name` + prefix example and the `--list` examples; add a short
  deprecation note: `--year`/`-y` are deprecated aliases removed in sobe
  2.0, and `-p` no longer means `--policy`. Also note that leading slashes
  are now stripped, so object keys starting with `/` (a 0.x footgun) can no
  longer be created — and pre-existing ones can no longer be listed or
  deleted through sobe; removing them requires the AWS console or CLI.
  Keep the page ASCII-only. Done when: no `--year` example remains except
  in the deprecation note.
- [x] Step 7: Update `specs/1.0-release.md` — annotate item 3's `--prefix`
  decision and open question 1 as implemented via `specs/prefix-flag-rename/`,
  recording the settled 2.0 removal timeline and the leading-slash
  normalization. Done when: a reader of item 3 sees the work is shipped, not
  pending.
- [x] Step 8: Update `AGENTS.md` (CLAUDE.md symlinks to it) — in the
  Architecture section's CLI notes: `-p` belongs to `--prefix`, `--policy` is
  long-only, `-y/--year` are deprecated aliases (removed in 2.0); drop
  "`--year` naming" from the open-decisions example so the file stops
  advertising a resolved question. Done when: AGENTS.md matches the shipped
  flag surface.

### Layer: Verification

- [x] Step 9: Run the full gate — `uv run pytest` (coverage ≥95% enforced),
  `uv run ruff check`, `uv run ruff format --check`, and
  `grep -rnP '[^\x00-\x7F]' docs --include='*.md'` (must be empty). Done
  when: all four pass clean.
