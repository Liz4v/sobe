# Architect: Multiple Targets

> Phase 2 — Design decisions. Approved before coding begins.
> Implementation checklist is in tasks.md.
>
> **Terminology** (user decision, 2026-07-12): the product term is **target**
> — in the CLI flag, the config file, the Python model, error messages, and
> docs. The Phase 1 files and the spec directory (formerly
> `multi-destination`, originally worded with "destination") were renamed to
> match.

## Approach

The change is confined to the existing three-module layout — no new modules:

- `config.py` gains the new schema model, target selection, old-schema
  detection, and one-time migration. It remains the only module that touches
  the config file.
- `aws.py`'s `AWS` class is re-pointed from `AWSConfig` to a `Target`
  and learns to live without a cache. All boto3 usage stays here.
- `main.py` gains the `--target` selector, the migration notice, the
  URL-or-bucket display prefix, and the invalidate-skip notice. It remains
  the only module that prints.

All configuration-validation and selection failures are expressed as a single
new exception, `ConfigError(message)`, raised in `config.py` and caught in
`main()`, which prints the message and exits 1. This keeps the module
boundary (no printing outside `main.py`) while giving every error path the
same shape. `MustEditConfig` keeps its current role (first-run flow),
unchanged, so the planned setup wizard (1.0 spec item 2) still has its
trigger.

### New TOML schema

```toml
# sobe configuration

# Target used when --target is not given.
default = "main"

[target.main]
url = "https://example.com/"          # optional

[target.main.storage]                 # required
type = "aws_s3"                       # required; only "aws_s3" accepted for now
bucket = "example-bucket"             # required

[target.main.cache]                   # optional
type = "aws_cloudfront"               # required inside cache; only "aws_cloudfront"
distribution = "E1111111111111"       # required inside cache

[target.main.aws_session]             # optional; boto3 Session kwargs
# region_name = "..."
# profile_name = "..."
# aws_access_key_id = "..."
# aws_secret_access_key = "..."

[target.main.aws_service]             # optional; client/resource kwargs
# verify = true
```

Decisions embedded in this shape:

- **`[target.<name>]` table, singular** — reads naturally in TOML and
  makes the name a first-class key. Names are validated against
  `^[A-Za-z0-9_][A-Za-z0-9_-]*$` (safe on any shell, cannot be mistaken for
  a flag, round-trips as a bare TOML key). Dots are deliberately excluded:
  in TOML, `[target.a.b]` is a *nested table*, so a dotted name could never
  round-trip and would collide with the sub-tables (`main.storage` vs
  `[target.main.storage]`). Violations raise `ConfigError` stating the
  allowed format.
- **`aws_session`/`aws_service` live at the target level**, not inside
  `storage`/`cache`, per the Analyst resolution ("session/service settings
  are per target"). One boto3 Session per target serves both S3
  and CloudFront, exactly as today. The `aws_` prefix namespaces them to the
  provider family: a future non-AWS provider adds its own prefixed tables
  (and its own `type` values) without touching these — purely additive.
- **Provider `type` values are prefixed with the provider family**
  (`aws_s3`, `aws_cloudfront`), matching the `aws_session`/`aws_service`
  naming, so every AWS-specific key in the schema is visibly `aws_*`.
- **`type` is required** in `storage` and `cache` (no implicit default).
  An omitted discriminator would silently change meaning if a future default
  ever changed; requiring it keeps provider addition purely additive.
  Unsupported values raise `ConfigError` naming the target, the key,
  the offending value, and the supported values.
- **`url` is normalized** to end with `/` on load (today an unslashed URL
  silently produces broken output).
- **Unconfigured test** (wizard/first-run trigger, replacing today's
  `bucket == "example-bucket"` check): the config is unconfigured when it
  defines **zero targets** or when **every** defined target's
  storage bucket is still `example-bucket`. For the shipped template
  (one target) this is behaviorally identical to today.
- **An unconfigured *new-schema* file is never rewritten** (Critic Round 1,
  W2): the template is written only when the file is missing or holds the
  old-schema placeholder. A hand-edited new-schema file whose buckets are
  all still `example-bucket` may contain real work (target names, URLs) —
  overwriting it would violate the never-destroy-user-data rule. Instead,
  `MustEditConfig` gains a `created: bool` attribute so `main()` can print
  "created it, go edit" vs "it exists but is unconfigured, go edit". This
  refines the Analyst edge-table shorthand ("same flow as missing config");
  the data-preservation rule outranks it.

### Python model (config.py)

All `NamedTuple`s, matching the existing style:

```python
class StorageConfig(NamedTuple):   # type ("aws_s3"), bucket
class CacheConfig(NamedTuple):     # type ("aws_cloudfront"), distribution
class Target(NamedTuple):          # name, storage, url|None, cache|None, aws_session, aws_service
class Migration(NamedTuple):       # path, backup  (both Path; for main's notice)
class Config(NamedTuple):          # targets: dict[str, Target], default: str|None
    def select(self, name: str | None) -> Target: ...
class ConfigError(Exception):      # message printed by main(), exit 1
```

`load_config()` changes signature to `-> tuple[Config, Migration | None]` so
`main()` can print the one-time migration notice without `config.py`
printing anything. (Signature break is fine: major version, and `main` is
the only caller.) Invalid TOML (`tomllib.TOMLDecodeError`) is wrapped in
`ConfigError` naming the file, so every config failure has the same shape.

Legacy-class retirement (Critic Round 1, B1 — the new `Config` shares its
name with the legacy `Config`, so they cannot coexist "side by side"):
the new `Config` **replaces** the legacy `Config` in the first step;
`AWSConfig` alone survives until the last importer (`aws.py`, tests) is
rewired, then is deleted. Pre-1.0 with a planned schema break — replaced,
not deprecated.

### Selection rules (`Config.select`)

Implemented in `config.py`, exactly per the Analyst behaviour list:

1. Name given → that target, or `ConfigError` naming it and listing
   defined names.
2. No name, `default` set → that target, or `ConfigError` if `default`
   references an undefined name (names the bad reference, lists defined).
3. No name, no `default`, exactly one target → it, silently.
4. No name, no `default`, multiple → `ConfigError` listing names and telling
   the user to pass `--target` or set `default`.

Selection happens in `main()` immediately after `parse_args()`, **before**
constructing `AWS` and before the `--policy` branch, so every operation —
including `--policy` — is target-scoped and selection errors fire
uniformly.

### Migration (old schema → new)

Old schema is recognized by a top-level `aws` table with no `target`
table. A file containing **both** `aws` and `target` tables is new schema
by this rule and the stray `[aws]` table is ignored — intentionally:
migration never produces such a file, so it is hand-made, and guessing
intent would be worse than ignoring (Critic Round 2 decision). Then:

- **Placeholder values** (`aws.bucket == "example-bucket"`): unconfigured —
  overwrite with the new-schema template and raise `MustEditConfig`, exactly
  the current first-run flow. No backup (nothing user-authored to lose).
- **Real values**: migrate in place, then continue the invocation.
  Order matters (Critic Round 1, B3): everything that can *fail* happens
  before anything touches the filesystem, so a failed migration never
  leaves a backup behind that would wedge the next run.
  1. **Emit first, in memory**: map `url` → `target.main.url`,
     `aws.bucket` → storage (`type = "aws_s3"`), `aws.cloudfront` → cache
     (`type = "aws_cloudfront"`, `distribution`), `aws.session`/`aws.service`
     → the target-level `aws_session`/`aws_service` tables. Write
     `default = "main"`. The migrated target is named **`main`**
     (short, obvious, valid on the CLI; matches the template). Non-scalar
     values raise `ConfigError` here, before any write — the message names
     the offending *key* only (values under `aws_session` may be secrets)
     and tells the user to migrate that table by hand.
  2. Backup: copy the original bytes to `config.toml.bak` (same
     directory), opened with `"xb"` so an existing backup is **never**
     overwritten — if it exists, raise `ConfigError` naming both paths and
     telling the user to move or remove the backup and re-run. The backup
     is created with the original file's permission bits (it may contain
     AWS credentials).
  3. Write the new content to a temp file in the same directory, then
     `os.replace()` onto `config.toml` — a failed migration can never leave
     a half-written config.
  4. Return `Migration(path, backup)` for `main()` to announce.

An already-migrated (new-schema) file is never rewritten: the migration path
only triggers on the old-schema shape.

**TOML emission**: `tomllib` cannot write, and there is no stdlib writer.
Rather than adding a dependency (`tomli-w`), migration output is produced by
a small private emitter in `config.py` that serializes the known new-schema
layout with scalar values only (`str`, `bool`, `int`, `float` — everything
boto3 session/service kwargs can be in TOML). Non-scalar values in old
`session`/`service` tables raise `ConfigError`. String values are emitted as
TOML basic strings with proper escaping (backslash, double quote, control
characters) — URLs and paths can contain any of these (Critic Round 1, W1).
**Critic Round 1 decision (N4): the emitter is endorsed over `tomli-w`** —
the layout is fixed, values are scalar-only, it is ~30 lines, and a new
dependency needs a user-confirmation gate the feature doesn't warrant.

### aws.py changes

- `AWS.__init__` takes a `Target`. The CloudFront client is only
  created when `target.cache` is set; `invalidate_cache()` reads the
  distribution ID from `target.cache.distribution`. No defensive guard for
  calling it on a cache-less target: `main()` simply never does.
- `generate_needed_permissions()` emits **two statements**: an S3 statement
  (always) and a CloudFront statement (only when the target has a
  cache). Cache-less policies contain no CloudFront actions or resources.

### main.py changes

- New flag: `-t NAME` / `--target NAME`. The `-t` short form is
  **reassigned from `--content-type`**, which becomes long-only: the
  everyday selector gets the good letter, the rare MIME override spells
  itself out. (Decision with Liz, 2026-07-11; amends the Analyst's
  CLI-compatibility constraint for this one short form — long names and
  semantics are untouched, and the change ships inside the same major
  bump as the schema break.)
- **Letter reservation** (recorded in `specs/1.0-release.md`, open question
  1, resolved the same day): the 1.0 freeze audit will promote `--year` to
  `-p`/`--path` with `-y`/`--year` kept as working aliases, and `--policy`
  becomes long-only to donate `-p`. That work stays in the 1.0 spec — this
  spec must simply not take `-p` or break `--year`.
- Flag-combination rules in `parse_args()`:
  - `--target` combines with everything, including `--policy` — the
    "`--policy` cannot be used with other arguments" check must exempt it
    (the `num_arg_types` counting needs a careful, tested adjustment).
  - `--target` alone (no operation) is an error: it modifies an
    operation but is not one, same doctrine as bare `--year`.
- Display prefix: everywhere `config.url` is interpolated today
  (upload/delete progress lines, `--list` lines, the "No files under"
  message), use `base = target.url or f"{target.storage.bucket}/"`.
- Migration notice: when `load_config()` returns a `Migration`, print (once,
  before anything else) a notice naming the migrated file and the backup
  path.
- First-run message: `MustEditConfig.created` distinguishes "created the
  template at PATH, edit it" from "PATH exists but is unconfigured, edit
  it" (the current single message claims creation even when the file
  already existed — subtly wrong today, actively misleading once
  unconfigured new-schema files are left untouched).
- `--invalidate` on a cache-less target: run everything else normally,
  then print a notice that the target has no cache configured and the
  invalidation is skipped; exit 0.
- Catch `ConfigError` around config loading + selection: print the message,
  exit 1.

## CLI Contract

(The template's API-contract table, adapted: this is a CLI tool.)

| Surface | Change | Compatibility |
|---------|--------|---------------|
| `-t/--target NAME` | New optional flag on all operations | Additive (long form); `-t` reassigned |
| `--content-type` | Loses its `-t` short form; long name and semantics unchanged | Breaking, sanctioned by the major bump |
| `--invalidate` | On cache-less target: skip + notice, exit 0 | Relaxed (was structurally impossible) |
| `--policy` | Scoped to selected/default target; accepts `--target`; two statements; CloudFront statement omitted without cache | Output shape change, pre-1.0 |
| All other flags | Unchanged names and semantics; `-p`/`--path` reserved for the 1.0 freeze audit's `--year` promotion | Frozen per 1.0 spec |
| Output lines | `target.url` prefix, or `bucket/` when no URL | Identical for migrated single-URL configs |
| Exit codes | `ConfigError` paths exit 1; first-run flow unchanged (exit 1) | Consistent with today |

## Data Model Changes

No database. The config file schema is redesigned as described above
(new-schema TOML with `[target.<name>]` tables); the "migration file"
equivalent is the in-place migration logic in `config.py` plus the
`config.toml.bak` backup. The old layout remains readable exactly once, as
migration input.

## Files to Create

| File | Purpose |
|------|---------|
| *(none)* | The three-module layout absorbs the feature |

## Files to Modify

| File | Change |
|------|--------|
| `src/sobe/config.py` | New model, validation, selection, template, migration, `load_config()` rewrite |
| `src/sobe/aws.py` | `AWS` consumes `Target`; optional cache; split policy statements |
| `src/sobe/main.py` | `-t/--target` flag (reassigning `-t`), combination rules, migration notice, display prefix, invalidate skip |
| `tests/test_config.py` | Rewrite for new model, selection, migration, load flows |
| `tests/test_aws.py` | `Target` fixtures, cache-less cases, split policy |
| `tests/test_main.py` | New flag rules, selection errors, notices, no-URL output |
| `docs/configuration.md` | New schema reference, migration behaviour, all new keys |
| `docs/usage.md` | `--target` examples, `--content-type` long-only, invalidate notice, new `--policy` output |
| `README.md` | Old-schema snippet becomes false information once this lands — update it |
| `CLAUDE.md` | Architecture notes reference the old schema (`aws.bucket` placeholder check, `AWS(config.aws)` flow, `[aws.session]`/`[aws.service]`) — stale once this lands (Critic Round 1, W5) |

## Dependencies Between Steps

- Steps 1–6 (config.py) are strictly sequential — same file, each builds on
  the previous.
- Step 10 (aws.py) depends on Step 1 (needs `Target`).
- Steps 12–13 (main.py) depend on Steps 6 and 10 (new `load_config` shape
  and new `AWS` signature).
- Step 14 (delete `AWSConfig`) depends on Steps 7, 10, and 11 — the
  importers are `aws.py` (Step 10), `tests/test_aws.py` (Step 11), and
  `tests/test_config.py` (Step 7 rewrites its `isinstance(..., AWSConfig)`
  assertions). It does not depend on Step 13: `main.py` never imports
  `AWSConfig`. (Corrected in Critic Round 2.)
- Test steps depend on the code steps they cover: 7–9 on 1–6; 11 on 10;
  15–16 on 12–13.
- Docs steps 17–19c depend on the design being final (after 13), not on
  tests.

## Parallelisation Opportunities

- **File locks**: steps 1–6 (all `config.py`), 12–13 (both `main.py`), and
  15–16 (both `tests/test_main.py`) must each run sequentially within their
  group.
- After Step 6: Step 10 (`aws.py`) and Steps 7–9 (`tests/test_config.py`)
  touch different files — safe in parallel.
- Steps 11 (`tests/test_aws.py`) and 12–13 (`main.py`) are independent —
  safe in parallel after Step 10.
- Steps 17, 18, 19, 19b, 19c (five different doc/spec files) are mutually
  independent — safe in parallel.
- Note: the full test suite (95% coverage gate) is only expected green from
  Step 16 onward; per-file test runs are the check before that — and they
  must pass `--no-cov`, because pyproject's addopts apply the coverage gate
  to every run and a single-file run cannot meet it (Critic Round 2).

## Risks & Open Questions

Known risks. Items marked *resolved* were settled by Critic Round 1 —
resolutions are recorded inline and in `CriticReview.md`.

- **Hand-rolled TOML emitter vs `tomli-w`.** *Resolved (Round 1, N4):
  emitter, with escaping required (W1).* The layout is fixed and
  scalar-only; a new dependency needs a user gate the feature doesn't
  warrant.
- **Migration fires on `sobe --help` / `--version`** *(accepted risk,
  Round 1, W3)*: `main()` calls `load_config()` before `parse_args()`, so
  an old-schema config is migrated (and a `ConfigError` in a broken config
  aborts) even for help/version invocations. This matches today's wart —
  the placeholder flow already writes files and exits 1 on `--help` — and
  is safe (backup kept). The 1.0 wizard spec (item 2) reorders parsing
  before config access and resolves it for good; this spec does not.
- **`num_arg_types` logic in `parse_args()`** counts truthy args to decide
  help vs `--policy` exclusivity; adding `--target` shifts these counts
  in non-obvious ways. This is the most regression-prone step (13/15 must
  cover: bare `sobe`, `sobe -t x` alone, `sobe -p -t x`, `sobe -p -y 2024`,
  and `--content-type` still working long-only).
- **`-t` muscle memory.** A pre-existing habit of `sobe -t image/png file`
  now parses `image/png` as a target name. It can never silently succeed:
  MIME types contain `/`, which the target-name charset forbids, so
  the invocation always fails with the unknown-target error (which
  lists the real names). Loud failure, but worth a line in the docs.
- **Interrupted-migration recovery.** If migration wrote the backup but died
  before the rename, the next run sees old schema + existing backup and
  fails with the move-the-backup error. Safe (nothing lost) but the user is
  wedged until they act — the error message's "next step" must be precise.
  *Narrowed (Round 1, B3):* emission and validation now happen before any
  filesystem write, so the only remaining window is between the backup
  write and `os.replace()` — a process kill, not a code path.
- **Migrated target name `main` collides** with nothing today, but if
  a user's muscle memory expects a different name they must edit the config;
  acceptable, one-time.
- **Wizard spec coupling** (1.0 item 2): it keys on the placeholder-bucket
  test and the current template. This spec redefines both; the wizard spec
  must be written against the new-schema unconfigured test defined here.
- **Zero-targets file is overwritten by the template** — *resolved
  (Round 1, W2): it is not.* An existing new-schema file that is
  unconfigured (zero targets, or all buckets placeholder) is left
  untouched; `MustEditConfig(created=False)` points at it. The template is
  written only for a missing file or an old-schema placeholder file.

## Architect Checklist

- [x] Approach fits existing project patterns (three modules, NamedTuples, ConfigError->main prints)
- [x] CLI contract defined before any code (API-contract equivalent)
- [x] Schema changes identified (config schema redesign + migration; no database)
- [x] Auth and ownership checks included in plan (n/a — local CLI; per-target credentials covered)
- [x] No step requires modifying multiple unrelated files
- [x] Parallelisation opportunities and file locks declared
- [x] Notification/event needs considered for mutations affecting live state (migration notice, invalidate-skip notice)
