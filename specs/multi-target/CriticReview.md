# Critic Review: Multiple Targets

> Phase 3 — Plan stress-test. Approved before coding begins.
> This review went through two rounds. Round 1 = self-critique.
> Round 2 = fresh-eyes adversarial pass by an independent agent.

## Round 2 (fresh-eyes) — findings

A second adversarial pass with a fresh context window (independent agent,
2026-07-12) found **0 additional blockers** and **4 warnings** that Round 1
missed. All have been applied. The agent also positively verified the Round 1
blockers against the code (B1's name collision is real at `config.py:26/10`),
executed the Architect template through `tomllib` (parses), confirmed no test
`patch()` target is orphaned by the migration, and confirmed the spec honors
the `specs/1.0-release.md` flag-letter reservations. Zero Round 2 blockers on
a 20-step spec is below the empirical baseline, but the verification evidence
is substantive rather than shallow — accepted.

### Round 2 Blockers (applied)

None found.

### Round 2 Warnings (applied)

| ID | Finding | Where fixed |
|----|---------|-------------|
| W1-r2 | Step 14's dependency claims were wrong on both files: Architect.md said "Steps 10 and 13" but `main.py` never imports `AWSConfig`; tasks.md said "10 and 11", omitting `tests/test_config.py`'s `isinstance` assertions (Step 7). | Architect.md Dependencies Between Steps; tasks.md Step 14 (now Steps 7, 10, 11). |
| W2-r2 | `docs/usage.md:17-23` quotes the first-run console output ("Created config file...") that Step 13 changes; Step 18's enumeration missed it. | tasks.md Step 18. |
| W3-r2 | `specs/1.0-release.md` item 2 (wizard) hardcodes the old schema — required CloudFront prompt, `[aws.session]`/`[aws.service]` sections, old placeholder-detection as trigger — leaving a companion spec with unimplementable acceptance criteria. Architect noted the coupling but assigned no task. | tasks.md new Step 19c (reconcile wording; do not resolve its open questions). |
| W4-r2 | `README.md:29` ("edit this file with your AWS bucket and CloudFront details"), `README.md:5` and `docs/index.md:5` (CloudFront as structurally required) become false; Step 19 limited itself to the TOML snippet and `docs/index.md` appeared in no step. | tasks.md Steps 18 (index.md) and 19 (README prose). |

### Round 2 Notes (applied unless stated)

| ID | Finding | Where fixed |
|----|---------|-------------|
| N1-r2 | `sobe -t ""` slips through truthiness-based checks: `num_arg_types` counts `""` as absent (help instead of error) and a truthy `select` implementation would silently fall to the default. | tasks.md Steps 12 (`is not None` checks) and 15 (test case). |
| N2-r2 | Per-file test runs before Step 16 fail the unconditional 95% coverage gate in pyproject addopts; implementers need `--no-cov` mid-sequence. | Architect.md Parallelisation note. |
| N3-r2 | Step 19b's validation grep missed the `[aws.session]`/`[aws.service]` mention its own prose says to fix. | tasks.md Step 19b (pattern extended). |
| N4-r2 | Round 1's scope-lens claim that URL normalization is "recorded in Analyst.md" was inaccurate — it is an Architect decision. | Corrected in the Round 1 section below (audit trail kept honest, original wording noted). |

### Round 2 overrode Round 1

No Round 1 fix was undone. N4-r2 corrected a misattribution in Round 1's
*audit text* (not a spec change): the scope-lens paragraph now attributes
URL normalization to the Architect.

### Round 2 Residual risks (couldn't be verified offline)

- "Everything boto3 session/service kwargs can be in TOML is scalar" is an
  overclaim — TOML also permits arrays and datetimes. The emitter's
  `ConfigError` fallback covers them, so the failure mode is a clean error,
  not corruption. To be confirmed during implementation (Step 4 tests).
- A hand-made config containing **both** `[aws]` and `[target.*]` tables is
  treated as new schema with `[aws]` silently ignored — now documented as
  intended in Architect.md (migration never produces such a file).

---

## Round 1 (self-critique) — findings

Reviewed against the actual code state (`src/sobe/*.py`, `tests/*.py`,
`docs/`, `README.md`, `CLAUDE.md`, `specs/1.0-release.md`) on 2026-07-12.

**Verdict: Needs revision — all findings below applied in the same session.**

### 🔴 Blockers (applied)

| ID | Lens | Finding | Where fixed |
|----|------|---------|-------------|
| B1 | Correctness | tasks.md Step 1 said the new model is added "beside the legacy classes", but the new `Config` NamedTuple shares its name with the legacy `Config` (`config.py:26`) — they cannot coexist. | Architect.md "Legacy-class retirement" paragraph; tasks.md Steps 1 and 14 (new `Config` replaces legacy in Step 1; only `AWSConfig` survives to Step 14). |
| B2 | Correctness / Data Integrity | Target-name regex allowed `.`, but `[target.a.b]` is a *nested* TOML table — a dotted name can never round-trip as a bare key and collides with sub-tables (`main.storage` vs `[target.main.storage]`). | Architect.md schema-decisions bullet; tasks.md Step 1. Regex is now `^[A-Za-z0-9_][A-Za-z0-9_-]*$`. |
| B3 | Data Integrity | Migration wrote the backup *before* emitting the new TOML; an emitter failure (non-scalar value) left a backup behind, so every later run hit the "backup exists" error — the user wedged by our own failure path. | Architect.md migration section (emit in memory first, then backup, then replace); tasks.md Step 5; wedge-free-failure test added to Step 9. |

### 🟡 Warnings (applied)

| ID | Lens | Finding | Where fixed |
|----|------|---------|-------------|
| W1 | Correctness | The TOML emitter needs basic-string escaping (backslash, quote, control chars) — URLs/paths can contain them. | Architect.md TOML-emission paragraph; tasks.md Step 4; round-trip test in Step 9. |
| W2 | Data Integrity | An unconfigured *new-schema* file (zero targets / all buckets placeholder) was to be overwritten by the template, destroying a user's partial multi-target edits — contradicts the never-destroy-user-data rule. Refines the Analyst edge-table shorthand ("same flow as missing config"); the rule outranks the shorthand. | Architect.md new "unconfigured new-schema file is never rewritten" bullet + resolved Risks entry; tasks.md Steps 1, 6, 9, 13, 16 (`MustEditConfig.created`). |
| W3 | Correctness | `main()` calls `load_config()` before `parse_args()`, so migration (and `ConfigError` aborts) fire even on `sobe --help` / `--version`. Accepted: matches today's wart, safe (backup kept), and the 1.0 wizard spec reorders parsing for good. No code change in this spec. | Architect.md Risks (accepted-risk entry). |
| W4 | Security | The non-scalar migration `ConfigError` must name the offending *key* only — values under `aws_session` may be secrets — and state the manual next step. | Architect.md migration step 1; tasks.md Step 4. |
| W5 | Completeness | `CLAUDE.md` architecture notes reference the old schema (`aws.bucket` placeholder check, `AWS(config.aws)` flow, `[aws.session]`/`[aws.service]`) — stale once this lands. Harden must not edit it; a coder step was added instead. | Architect.md Files to Modify; tasks.md new Step 19b. |
| W6 | Testing | Every existing `TestMain` test mocks `load_config` (must return the new `(config, None)` tuple) and builds a Namespace without `target` — silent breakage if Step 16 only *adds* tests. | tasks.md Step 16 (explicit rewrite of all existing mocks). |
| W7 | Security | `config.toml.bak` may contain AWS secret keys; create it with the original file's permission bits. | Architect.md migration step 2; tasks.md Steps 5 and 9. |

### 🟢 Notes

| ID | Lens | Finding | Decision |
|----|------|---------|----------|
| N1 | Correctness | Invalid TOML (`tomllib.TOMLDecodeError`) currently escapes as a traceback. Cheap to fold into the new `ConfigError` shape. | Applied — Architect.md Approach; tasks.md Step 6 + test in Step 9. |
| N2 | Architecture Fit | `AWS.config` attribute should become `AWS.target` when the class consumes a `Target`. | Not applied as a spec change — internal naming, Step 10's implementer picks it up naturally. |
| N3 | Completeness | `docs/api/*.md` are pure autodoc stubs (`automodule`) — verified they need no manual edits when class names change. | No action needed. |
| N4 | Architecture Fit | Architect flagged emitter-vs-`tomli-w` for the Critic. Endorsed the emitter: fixed layout, scalar-only, ~30 lines, and a new dependency needs a user-confirmation gate the feature doesn't warrant. Escaping risk covered by W1. | Applied — decision recorded in Architect.md. |

### Lenses with no findings

- **Parallelisation Safety**: file-lock groups in Architect.md verified against
  the step list — correct, including the "suite red until Step 16" note.
  Step 19b (CLAUDE.md) is independent of Steps 17–19 — safe in parallel.
- **Scope**: no creep found. The `-t` reassignment is recorded in Analyst.md
  and `specs/1.0-release.md`. URL normalization is an Architect-level
  decision, not an Analyst behaviour — justified as fixing silently-broken
  output, but the attribution originally written here ("recorded in
  Analyst.md") was wrong and was corrected by Round 2 (note N4-r2).
