# Architect: `-p/--prefix` rename (CLI 1.0 freeze, final item)

> Phase 2 — Design decisions. Approved before coding begins.
> Implementation checklist is in tasks.md.

## Approach

Everything lands in `parse_args()` in `src/sobe/main.py`; `main()` is untouched.
This fits the module split: `main.py` owns all CLI parsing and user-facing
output, and the rename is purely a CLI-surface change — `aws.py` and
`config.py` never see flag names, only the computed `args.prefix`.

Three coordinated changes inside `parse_args()`:

1. **Flag registration.** `-p/--prefix` is registered where `-y/--year` sits
   today (so it occupies the same slot in `--help` output), keeping the
   existing help text `"set remote directory (usually a year)"`. Immediately
   after it, `-y/--year` stays registered with help
   `"deprecated alias for --prefix (removed in 2.0)"`. `--policy` drops its
   `"-p"` string and becomes long-only. `-l/--list` help is reworded from
   `"list all files in the year"` to `"list all files in the prefix"` — it is
   user-facing text tied to the old flag's concept (Analyst: all such text
   moves to `--prefix` terms).

2. **Alias consolidation, immediately after `parser.parse_args(argv)`** and
   before the `num_arg_types` computation:

   ```python
   if args.year is not None:
       if args.prefix is not None:
           parser.error("--prefix and --year cannot be used at the same time")
       print("warning: --year is deprecated, use --prefix; it will be removed in sobe 2.0", file=sys.stderr)
       args.prefix = args.year
   ```

   (Conflict wording matches the existing `--list --delete` error's
   "cannot be used at the same time" pattern.)

   - `parser.error()` gives exit code 2, consistent with every other
     flag-combination error.
   - The warning goes through the module's flushing `print` partial with
     `file=sys.stderr` (the partial only pins `flush=True`, so `file=` passes
     through). This is the one message in the program that targets stderr;
     everything else keeps using stdout. Requires adding `import sys`.
   - The block runs exactly once per invocation, which satisfies the
     "at most one warning" rule with no extra state.
   - `args.year` is left in the namespace as the raw record of what the user
     typed; **`args.prefix` is the single canonical value** all downstream
     logic reads.

3. **Validation + normalization**, replacing the current `args.year` block
   and operating directly on `args.prefix`:

   ```python
   if args.prefix is None:
       args.prefix = str(datetime.date.today().year)
   elif not (args.files or args.list):
       parser.error("--prefix requires files or --list to be specified")
   args.prefix = args.prefix.lstrip("/")
   args.prefix = args.prefix if args.prefix == "" or args.prefix.endswith("/") else f"{args.prefix}/"
   ```

   Naming the flag `--prefix` means argparse's inferred dest (`prefix`)
   already matches the name of the derived S3-key value the old design
   computed separately as `args.path` -> `args.prefix`. That two-hop shape
   collapses: there is no more intermediate `path` attribute, just
   `args.prefix` read, validated, and overwritten in place. This also
   retires the one-letter `path`/`paths` hazard the `--path` design carried
   (see Round 2 critic finding R2-W2, superseded below) — `prefix` and
   `paths` are not a plausible typo pair.

   Leading-slash stripping happens after defaulting (the default year never
   has slashes, so one unconditional `lstrip("/")` covers every value) and
   before the existing trailing-slash logic, which is preserved verbatim.
   `--prefix /` and `--prefix //` therefore collapse to `""` (bucket root),
   `--prefix /2024` to `2024/`.

### Why `num_arg_types` stays safe (verified against every branch)

`num_arg_types = sum(map(bool, args.__dict__.values()))` now sees two extra
truthy candidates: `prefix` and (when the alias is used) the still-set `year`.
Audit of the only two consumers:

- **`num_arg_types == 0` (print help, exit 0):** reachable only when every
  value is falsy. Consolidation copies a falsy `""` to a falsy `""`, so the
  branch triggers in exactly the same cases as today — including the existing
  `sobe --year ''` (alone) quirk, which `sobe --prefix ''` now mirrors. That
  quirk is part of the frozen 0.x surface; do not "fix" it.
- **`--policy` check (`num_arg_types != 1 + bool(args.target)`):** any
  invocation where the alias double-counts (`year` truthy ⇒ `prefix` truthy
  ⇒ count inflated by 1) was already `> 1 + bool(target)` before inflation,
  so every accept/reject outcome is unchanged. `--policy --target x --year
  ''` (accepted today because `''` is falsy) stays accepted, now with a
  deprecation warning on stderr first — Analyst.md explicitly leaves warning
  emission on odd invocations non-contractual.

No other line reads `args.year`; `main()` consumes `args.prefix`,
`args.paths`, and per-file flags (`remote_name`, `content_type`, ...) —
none derived from the flag's *name* — so it needs no change. `args.prefix`
(str, the flag's own dest, holding the final normalized directory value)
and `args.paths` (`list[pathlib.Path]` of local files) share the namespace
but are not easily confused for each other at a glance.

### Deliberately not doing

- No `argparse.Action` subclass or `deprecated=` parameter (that argparse
  feature is 3.13+; the project supports 3.11).
- No change to `main()`, `aws.py`, `config.py`, or the config schema.
- No suppression of the warning on failing invocations — whatever order
  falls out of the consolidation-before-validation placement is acceptable
  per Analyst.md.

## CLI Contract (this feature's API)

| Invocation | Result |
|-----------|--------|
| `-p V` / `--prefix V` | Remote directory = V (post-normalization); identical semantics to old `--year V` |
| `-y V` / `--year V` | Same as `--prefix V` + one-line warning on stderr |
| `--prefix A --year B` (any spellings) | `parser.error` ("cannot be used at the same time"), exit 2 |
| `--prefix /…` (incl. via alias) | All leading slashes stripped; `/` and `//` mean bucket root |
| neither flag | Default = current year (unchanged) |
| `--policy` | Unchanged; `-p` no longer means policy |
| `sobe -p` (no value) | argparse `expected one argument`, exit 2 |
| `--help` | `-p/--prefix` primary; `-y/--year` listed as "deprecated alias for --prefix (removed in 2.0)" |
| Validation errors naming the flag | Say `--prefix` (e.g. `--prefix requires files or --list to be specified`) |

Warning text (exact): `warning: --year is deprecated, use --prefix; it will be removed in sobe 2.0`

## Data Model Changes

No schema changes. No config changes. `argparse.Namespace`'s `prefix`
attribute (the `--prefix`/`-y` flag's own dest) now holds the value
directly — raw input, then overwritten in place with the normalized S3-key
prefix — rather than being derived from a separate `path` field as in the
earlier `--path` design. Retained raw `year` sits alongside it, unused by
downstream logic. Do not confuse `prefix` with the namespace's pre-existing
`paths` (local files as `list[pathlib.Path]`).

## Files to Create

None.

## Files to Modify

| File | Change |
|------|--------|
| `src/sobe/main.py` | `parse_args()`: flag registration, alias consolidation + warning, validation/normalization; add `import sys` |
| `tests/test_main.py` | Migrate primary-semantics tests from `--year` to `--prefix`; update `_mock_args` namespace; add alias/warning/conflict/normalization/help tests |
| `docs/usage.md` | Examples move to `--prefix`; `--prefix /` documented as recommended root spelling; deprecation note for `--year` |
| `specs/1.0-release.md` | Item 3 / open question 1 annotated as implemented (incl. 2.0 removal timeline) |
| `AGENTS.md` | CLI notes: `-p` belongs to `--prefix`, `--policy` long-only, `-y/--year` deprecated aliases; drop `--year` naming from the open-decisions example (`CLAUDE.md` is a symlink to it — one file) |

## Dependencies Between Steps

- Steps 1–3 are sequential edits to the same function (`parse_args`); the
  code only compiles-and-passes as a set. Step 2 depends on Step 1 (needs
  `args.prefix` to exist), Step 3 on Step 2 (reads consolidated `args.prefix`).
- Steps 4–5 (tests) depend on Steps 1–3 being complete — the suite must run
  against the finished flag surface.
- Step 5 depends on Step 4 (same file; Step 4 also fixes `_mock_args`, which
  Step 5's additions reuse).
- Steps 6–8 (docs/spec bookkeeping) have no code dependency but should state
  the final shipped behavior, so schedule after 1–3.
- Step 9 (full gate: pytest + coverage + ruff + ASCII check) depends on all
  previous steps.

## Parallelisation Opportunities

- **File locks:** `src/sobe/main.py` (Steps 1–3), `tests/test_main.py`
  (Steps 4–5) — each group strictly sequential within itself.
- Steps 6, 7, 8 touch three distinct files and are mutually independent —
  safe to run in parallel with each other, and with Steps 4–5.
- Steps 1–3 vs 4–5: different files, but 4–5 are meaningless before 1–3
  land; do not parallelise across that boundary.

## Risks & Open Questions

Known risks Phase 3 (Critic) should scrutinise:

- **`num_arg_types` audit above is the load-bearing claim.** It was checked
  by hand against both consumer branches; the Critic should independently
  re-derive it, especially the alias double-count and empty-string cases.
- **Warning-before-help quirk:** `sobe -y ''` (alone) emits the deprecation
  warning and then prints help / exits 0. Deemed acceptable
  (non-contractual), but confirm it doesn't confuse the help-path tests that
  assert `print_help` behavior.
- **stderr via the print partial:** relies on `functools.partial(print,
  flush=True)` forwarding `file=`. True for CPython's `print`; a test must
  capture stderr (capsys) to prove routing, not just message content.
- **Help-output test brittleness:** the "deprecated alias" help-text test
  should assert a substring (e.g. `deprecated alias for --prefix`), not the
  full formatted help. In particular it must NOT assert the joined
  `-p, --prefix` layout: argparse only prints that on Python >= 3.13
  (3.11/3.12 print `-p PREFIX, --prefix PREFIX`), and the suite runs on a
  3.11-3.14 matrix per `specs/1.0-release.md` item 1.
- **Legacy leading-slash keys become CLI-unreachable:** in 0.x,
  `-y /2024 --delete f.txt` could delete an accidental `/2024/f.txt` key;
  after normalization no sobe invocation can address such keys. Deliberate
  (Analyst drops representability), but the docs deprecation note must tell
  users to clean surviving footgun keys with the AWS console/CLI.
- **Existing tests asserting `args.year`:** `test_parse_args_policy_only`
  asserts `args.year is None` — still true, but every migrated test must
  switch its semantic assertions to `args.prefix`.
- **`_mock_args` in `TestMain`** must mirror the real namespace (`prefix=`
  holds the final normalized value directly, `year=None`) or `main()`-level
  tests drift from reality.

No open questions — all decisions were resolved in Analyst.md.

## Rollback

Single-surface change confined to `parse_args()` plus docs/spec text; no
data, schema, or config migration. Revert order: `git revert` of the
implementation commit(s) restores the 0.x surface wholesale — no partial
revert is meaningful, since code and tests only pass as a set.

## Architect Checklist

- [x] Approach fits existing project patterns (all parsing/output in `main.py`; stdout discipline kept, stderr exception isolated)
- [x] API contract defined before any code (CLI contract table above)
- [x] Schema changes identified (explicitly none)
- [x] Auth and ownership checks included in plan (n/a — local CLI, no auth surface changes)
- [x] No step requires modifying multiple unrelated files
- [x] Parallelisation opportunities and file locks declared
- [x] Notification/event needs considered for mutations affecting live state (n/a — no live-state mutations; the one new message is the stderr warning, specified above)
