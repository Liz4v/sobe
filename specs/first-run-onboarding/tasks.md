# Tasks: First-Run Onboarding (Tutorial Pointer)

> Phase 2 output — implementation checklist.
> Each step is atomic: one file created, one migration, one component.
> Dependencies and parallelisation opportunities are documented in Architect.md.

### Layer: CLI (`src/sobe/main.py`)

- [ ] Step 1: Add a module-level `TUTORIAL_URL = "https://sobe.readthedocs.io/en/latest/tutorial.html"`
  constant near the top of `main.py` (next to the `write`/`print` partials). Extract the
  parser construction in `parse_args()` (the `ArgumentParser(...)` call plus every
  `add_argument`, moved verbatim — no definitions change) into a module-level
  `_build_parser() -> argparse.ArgumentParser`; `parse_args()` starts with
  `parser = _build_parser()`. In `parse_args()`, change the bare branch: after
  `num_arg_types` is computed, `if num_arg_types == 0:` set `args.bare = True` and
  `return args` immediately (no help print, no `SystemExit`); on the fall-through path
  set `args.bare = False` at that same point (only after the count is computed, so the
  new attribute can never affect `num_arg_types`). In `main()`, move `args = parse_args()`
  to be the first statement, ahead of the `try: config, migration = load_config()` block.
  In the `except MustEditConfig as err:` handler, keep the existing
  `if err.created: ... else: ...` branch and `print(err.path)`, then add one new line
  printing `f"Full setup tutorial: {TUTORIAL_URL}"` before `raise SystemExit(1) from err`.
  After the migration-notice block, add: `if args.bare: _build_parser().print_help();
  raise SystemExit(0)` — so bare invocation prints help only when the config phase
  succeeded, preserving today's first-run behavior (template + message + pointer, exit 1,
  when config is missing/unconfigured). Everything after that check
  (`config.select(args.target)` onward) is unchanged; the bare path never reaches it, so
  the early-returned Namespace (no `paths`, unnormalised prefix) is never consumed. Done
  when: `--help` and `--version` exit 0 without any `load_config` call reachable in the
  source (behavioral proof is Step 3's tests), bare `sobe` matches the First-Run Behavior
  Contract row for each config state, and both `MustEditConfig` branches print three
  lines total.

### Layer: CLI Tests (`tests/test_main.py`)

- [ ] Step 2: Update `test_bad_config_created` and `test_bad_config_existing_unconfigured`
  (in `TestMain`) to add `mock_print.assert_any_call("Full setup tutorial: https://sobe.readthedocs.io/en/latest/tutorial.html")`
  alongside the existing assertions. Add `bare=False` to the `Namespace` built by
  `TestMain._mock_args` — without it, every `TestMain` test dies on `args.bare` in the
  reordered `main()`. Update the two `TestParseArgs` tests that assert `parse_args`
  self-prints help on bare input — `test_parse_args_no_files_no_invalidate_prints_help`
  (`parse_args([])`) and `test_parse_args_empty_target_alone_prints_help`
  (`parse_args(["-t", ""])`): both now assert the call *returns* a Namespace with
  `args.bare is True` (no `SystemExit`, no help print); rename them accordingly (e.g.
  `..._returns_bare`). Also assert `args.bare is False` in one representative
  non-bare `TestParseArgs` case (e.g. the `--list` one). Fix the now-stale comment in
  `test_prefix_slash_alone_errors` (it calls `--prefix ''` alone a "frozen
  help-and-exit-0 quirk" — after Step 1 that invocation is bare, so its outcome is
  config-state-dependent; the test itself still passes unchanged). Done when: the suite
  passes against the Step 1 code and the updated assertions would fail against
  pre-Step-1 code.
- [ ] Step 3: Add a new test class (e.g. `TestMainArgsBeforeConfig`) that does **not**
  mock `parse_args` — only patches `sobe.main.load_config` (e.g. via
  `monkeypatch.setattr("sobe.main.load_config", ...)` or a local `@patch`) with a
  `Mock(...)` so `assert_not_called()` / return values / side effects can be set per
  case, and patches `sys.argv` (via `monkeypatch.setattr(sys, "argv", [...])`). Cases:
  (a) `["sobe", "--help"]` and (b) `["sobe", "--version"]` — `load_config` has
  `side_effect=AssertionError("load_config should not be called")`; assert `main()`
  raises `SystemExit` code `0` and `load_config.assert_not_called()`;
  (c) `["sobe", "--prefix", "2024"]` (invalid combo: --prefix without files/--list) —
  assert `SystemExit` code `2` and `load_config` never called, proving argument errors
  preempt config access (no template written on a fresh machine);
  (d) `["sobe"]` bare with `load_config` raising `MustEditConfig(Path(), created=True)` —
  assert `SystemExit` code `1` and (patching `sobe.main.print`) the created-message and
  tutorial-pointer lines are printed: bare invocation *does* enter the config phase;
  (e) `["sobe"]` bare with `load_config` returning `(make_config(), None)` — assert
  `SystemExit` code `0` and help was printed (assert via `capsys` "usage:" in stdout, or
  patch `sobe.main._build_parser`): bare + configured config still shows help. Done when:
  all five cases pass, and reverting Step 1's reordering or the bare-defer change would
  make at least one of them fail.

### Layer: Documentation

- [ ] Step 4: Create `docs/tutorial.md`, a full prose walkthrough fleshed out from
  [`TutorialOutline.md`](TutorialOutline.md) (same repo, under `specs/`) into a Sphinx
  page. Title `# Tutorial`. Convert each outline section into a `##` header in the same
  order: "Warnings (is Sobe for you?)", "Create an AWS account", "Create a bucket",
  "Create a CloudFront distribution", "Install sobe", "Create IAM (Identity and Access
  Management) access for sobe", "What will your domain be?", "Create an ACM Certificate",
  "Back to CloudFront". Expand each terse bullet into one or more full sentences a
  beginner can actually follow — explain *why* a step matters where the outline implies
  it (e.g. why a budget cap, why region matters, why the CNAME stays permanently) — while
  keeping every fact, warning, and placeholder value (bucket names, `E1111111111111`,
  `d2222222222222.cloudfront.net`, `files.example.com`, the ACM CNAME example) exactly as
  drafted and in the same order. Preserve the outline's first-person, opinionated voice
  ("I, the sole author of Sobe..."). Turn the `- Link.` bullet under "Create an AWS
  account" into a full sentence linking to `https://aws.amazon.com/`. Convert the two
  CNAME record lists into MyST pipe tables. Keep the `sobe --policy` instructions and the
  hover.com affiliate link unchanged. The Install section's "Run `sobe` once" bullet is
  accurate as written — bare `sobe` keeps its first-run behavior by design.
  Page must be ASCII-only (verify with the Step 10
  grep). Done when: the file exists, headers match the outline order 1:1, every outline
  fact/warning/value is present, and no section is just a bullet list copy-paste.
- [ ] Step 5: In `docs/index.md`, add `tutorial` as the first entry in the existing
  ```` ```{toctree} ```` block captioned "User Guide" (before `usage`, `configuration`).
  Done when: `docs/tutorial.md` is reachable from the built index page's left nav, first
  under "User Guide".
- [ ] Step 6: In `docs/usage.md`, update the Installation section's first-run transcript
  (the existing `$ sobe` block stays `$ sobe` — bare first run is retained) to show all
  three printed lines from Step 1's exact message text (path stays the placeholder
  `/home/user/.config/sobe/config.toml`). Add one sentence pointing to the new page, e.g.
  "For a full walkthrough including AWS account, bucket, and CloudFront setup, see the
  [Tutorial](tutorial.md)." placed near the top of Installation, before or after the
  transcript. Done when: the transcript matches Step 1's actual bare-`sobe` output with
  no config present, and a Tutorial cross-reference exists.
- [ ] Step 7: In `docs/configuration.md`: (a) add a short parenthetical to the opening
  sentence ("The first time you invoke the tool, it will create a default configuration
  file...") noting that `--help` and `--version` are the exception — they answer without
  reading or creating the config file; (b) in the "Unconfigured configs" section, add a
  clause noting the printed message also includes a pointer to the onboarding tutorial
  (link to `tutorial.md`). Keep the rest of that section's wording intact. Done when:
  both spots accurately reflect Step 1's behavior and output. (README.md needs no change:
  its "On first run, sobe will create its config file" sentence stays true with bare
  first run retained, and the project rule forbids README edits unless content is false.)

### Layer: Project Bookkeeping

- [ ] Step 8: In `AGENTS.md`, update the "Flow:" sentence in the Architecture section:
  `main()` now parses args first, then loads config (reversing the current
  "loads config ... then parses args" order), and bare invocation prints help only after
  the config phase succeeds; keep the rest of the sentence (`config.select` ->
  `AWS(target)` -> flag dispatch) unchanged. Done when: the sentence matches Step 1's
  actual call order.
- [ ] Step 9: In `specs/1.0-release.md`, annotate item 2 ("First-run experience:
  interactive setup wizard") as resolved — narrower tutorial-pointer approach shipped via
  `specs/first-run-onboarding/`, wizard rejected, matching the annotation style used for
  item 3 in the archived `prefix-flag-rename` spec. Also annotate open question 4
  (auto-printing `--policy` output on first run) as resolved "no — deferred; `--policy`
  stays a manual, documented follow-up step" per this spec's Analyst.md. The annotation
  must explicitly supersede item 2's "**Decision (resolved 2026-07-11):** replace
  write-and-exit with an interactive first-run wizard" line and note that its
  wizard-specific acceptance criteria (TTY prompts, non-TTY "no file is created") no
  longer apply — the template-write behavior is retained. Leave the `main.py:20-28`
  line-link in item 2's Problem paragraph as-is (it describes the historical bug; line
  numbers going stale in an annotated-resolved item is acceptable). Done when: a reader
  of item 2 sees the work is shipped, not pending, understands the wizard idea was
  deliberately dropped, and open question 4 is marked resolved.

### Layer: Verification

- [ ] Step 10: Run the full gate: `uv run pytest` (coverage >=95% enforced), `uv run ruff
  check`, `uv run ruff format --check`, `grep -rnP '[^\x00-\x7F]' docs --include='*.md'`
  (must be empty), and `uv run --extra docs -m sphinx -b html docs docs/_build/html` —
  eyeball the build output for new warnings (e.g. broken toctree entry, bad `tutorial.md`
  cross-reference) since the build command has no `-W` fail-on-warning flag. Also run the
  PDF validation from AGENTS.md (LaTeX build + `nix-shell ... make -C docs/_build/latex
  all-pdf` — exact command in AGENTS.md "Commands"): Read the Docs builds `formats: all`
  with pdflatex, and `tutorial.md` introduces pipe tables with long unbreakable tokens
  (the ACM CNAME values), the likeliest new page to break or overflow the PDF build.
  Done when: all six checks pass clean with no new warnings attributable to this feature.
