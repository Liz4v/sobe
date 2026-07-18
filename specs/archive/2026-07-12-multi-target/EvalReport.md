# Eval Report: Multiple Targets

> Phase 5 — Post-implementation evaluation. Run after sdd-coder completes.
> Evaluator had no access to the coder's reasoning — fresh context only.
> Evaluated 2026-07-12 against Analyst.md + Architect.md + tasks.md, plus the
> user amendment recorded in status.json (empty `--target` treated as not
> given via truthiness, reversing the `is not None` wording of tasks.md
> steps 12/15).

## Computational Sensors

| Check | Result |
|-------|--------|
| Lint (`ruff check`) | ✅ 0 errors |
| Format (`ruff format --check`) | ✅ 10 files, all formatted |
| Tests (`pytest`) | ✅ 128 passed, 0 failed (131 after follow-up, below) |
| Coverage (gate 95%) | ✅ 99.22% (100% after follow-up, below) |
| Sphinx HTML build | ✅ build succeeded |
| Docs ASCII-only | ✅ no non-ASCII characters in `docs/**/*.md` |

(No frontend in this project; frontend sensors n/a.)

## Semantic Evaluation

| Criterion | Verdict | Detail |
|-----------|---------|--------|
| CONTRACT | ✅ | All Architect.md deliverables present and verified at line level: model + `Config.select` (`config.py`), emit-before-backup-before-`os.replace()` migration ordering (`config.py:293-312`), escaping TOML emitter (`config.py:202-269`), `AWS(Target)` with optional CloudFront client (`aws.py:20-22`), split two-statement policy (`aws.py:75-97`), `-t/--target` with `--content-type` long-only (`main.py:84-86`), display prefix (`main.py:52`), `MustEditConfig.created` branching (`main.py:23-28`), migration + invalidate-skip notices. |
| BEHAVIOUR | ✅ | Every bullet in Analyst.md "Behaviour" traces to specific code (selection rules `config.py:130-149`, no-URL bucket prefix at all output sites, cache-less invalidate skip + exit 0, per-target policy, migration flows, provider-type and bad-default errors). |
| EDGE CASES | ✅ | All rows of the edge-case table handled, including existing-backup `"xb"` failure (`config.py:298-304`), fail-before-write ordering, zero-targets unconfigured (`config.py:153`), both-`[aws]`-and-`[target.*]` treated as new schema (`config.py:274`), name-charset validation (`config.py:73-77`), duplicate buckets allowed. |
| TESTS | ⚠️ | Behaviors and errors broadly tested (steps 7-9, 11, 15-16 all represented), but 3 uncovered `config.py` branches and 1 untested design decision — see Findings. |
| PATTERNS | ✅ | Module boundaries hold (printing only in `main.py`, boto3 only in `aws.py`, config file I/O only in `config.py`); NamedTuple style; errors carry identifiers + next step; MyST ASCII docs; placeholders only, no secrets. |
| COVERAGE | ✅ | 99.22% ≥ 95% gate. |
| NO EXTRAS | ✅ | No flags, keys, or behaviors beyond the spec; `-p`/`--year` untouched as reserved. |

Amendment self-consistency: the `-t ""` reversal is implemented consistently —
truthiness in `Config.select` (`config.py:130`) and `parse_args`
(`main.py:94,105`) — and tested end-to-end
(`test_main.py:260-271`, `test_config.py:165-167`). Note that `tasks.md`
steps 12/15 still carry the pre-amendment `is not None` wording; the
amendment is recorded only in `status.json`.

## Findings

All findings are ⚠️ TESTS gaps (no ❌). Each cited line was verified by
reading the source, not just the coverage report.

1. ⚠️ TESTS — `src/sobe/config.py:79`: the `ConfigError` for a non-table
   `[target.<name>]` entry (e.g. `target.foo = "oops"` in TOML) is never
   exercised; no test constructs a target whose raw value is a non-dict.
2. ⚠️ TESTS — `src/sobe/config.py:91`: the `ConfigError` for a non-table
   `cache` value is never exercised; only the analogous
   `aws_session`/`aws_service` non-table case is tested
   (`tests/test_config.py:99-101`).
3. ⚠️ TESTS — `src/sobe/config.py:213`: the `\r` branch of the emitter's
   string escaping is untested; `test_escaping_round_trips_through_tomllib`
   (`tests/test_config.py:194-211`) covers `"`, `\`, `\t`, `\n`, and `\x01`
   but not carriage return, though Critic Round 1 W1 named control-character
   escaping explicitly.
4. ⚠️ TESTS — no test loads a config file containing **both** a top-level
   `[aws]` table and `[target.*]` tables to assert it parses as new schema
   with the stray `[aws]` ignored — a scenario Architect.md records as an
   intentional Critic Round 2 design decision. The behavior is implemented
   correctly (`config.py:274` + `config.py:118`) but unverified by tests.

## Verdict

- [x] **PASS** — all criteria ✅, ready to archive
- [ ] ~~**PARTIAL PASS** — only ⚠️ warnings, archive with known gaps noted~~
  (initial verdict, before the resolution below)
- [ ] **FAIL** — one or more ❌, specific items must go back to coder

## Resolution (2026-07-12, user-directed follow-up)

The user directed all four ⚠️ findings to be fixed. Tests added to
`tests/test_config.py`:

1. `test_non_table_target_error` — covers `config.py:79`.
2. `test_non_table_cache_error` — covers `config.py:91`.
3. `test_escaping_round_trips_through_tomllib` extended with `\r` in the
   round-trip string — covers `config.py:213`.
4. `test_both_aws_and_target_tables_is_new_schema` — asserts a file with
   both `[aws]` and `[target.*]` loads as new schema, the stray `[aws]` is
   ignored, no migration or backup occurs, and the file is untouched.

After the fixes: 131 tests pass, coverage 100.00%, ruff check and format
clean. All findings resolved; effective verdict **PASS**, ready to archive.
