# Analyst: Multiple Targets

> Phase 1 — Problem definition. Approved before architecture begins.

## Goal / Outcome

**Scope classification:** Complex

sobe currently serves exactly one drop box: a single website URL backed by one
S3 bucket, with one CloudFront distribution that is structurally required (the
config template always contains it). Users who maintain more than one site —
or one site with distinct upload areas — must maintain separate config files
or edit the config between uses.

This change lets a user define multiple named **targets** (profiles) in
one config file. Each target independently configures its storage
(today: AWS S3), an **optional** public URL, and an **optional** cache
(today: AWS CloudFront). Only the storage is mandatory.
The configuration schema is being redesigned for this, which is acceptable
because a major version bump is planned; the new schema is shaped so that
future non-AWS storage/cache providers can be added **additively**, without
another schema break.

## Scope

**Included:**
- New configuration schema supporting multiple named targets, each with
  its own storage settings and credentials/session settings, plus an optional
  public URL and an optional cache section.
- A way for the user to select a target per invocation, plus a
  configurable default target used when none is selected.
- Automatic in-place migration of existing (old-schema) config files to the
  new schema, preserving a backup of the original file.
- Cache becomes genuinely optional per target; behaviour of
  cache-dependent operations (`--invalidate`) on cache-less targets is
  defined (skip with notice).
- Per-target behaviour of `--policy` (IAM policy generation).
- Schema uses provider discriminators (storage type, cache type) with S3 and
  CloudFront as the only accepted values for now.
- Updated default/template config, docs (`docs/configuration.md`,
  `docs/usage.md`), and tests for all of the above.

**Excluded (non-goals):**
- Any actual non-AWS storage or cache implementation. Only the schema shape
  anticipates them; S3/CloudFront remain the only valid providers.
- Operating on multiple targets in one invocation (e.g. "upload to all").
  One invocation acts on exactly one target.
- Cross-target operations (copy/move between targets).
- The interactive first-run wizard (item 2 of `specs/1.0-release.md`). It is a
  separate spec; this spec only requires that the unconfigured-config flow
  keeps working against the new schema (see Rules & Constraints).
- `--list` filtering (explicitly out of scope per the 1.0 spec).
- Changing any existing flag's name or semantics beyond what targets
  strictly require.

## Behaviour

- When the config file defines multiple targets, the user must be able to
  name one target per invocation via the CLI, and every operation
  (upload, delete, list, invalidate, policy) must act only on that
  target.
- When no target is named on the command line, the system must use the
  target marked as default in the config file.
- When no target is named, no default is marked, and exactly one
  target is defined, the system must use that single target.
- When no target is named, no default is marked, and more than one
  target is defined, the system must exit with an error that lists the
  defined target names and tells the user to either name one or mark a
  default.
- When the user names a target that is not defined in the config, the
  system must exit with an error naming the requested target and listing
  the targets that are defined.
- When a target defines no public URL, every place that today prints a
  full public URL (upload/delete progress lines, `--list` output, the
  "no files under" message) must use the storage identifier (i.e. the bucket
  name) in place of the URL prefix, followed by the remote path (prefix plus
  name); all operations otherwise behave identically.
- When a target defines no cache and the user passes `--invalidate`, the
  system must perform the rest of the requested operation normally, print a
  notice that the target has no cache configured and the invalidation is
  skipped, and exit 0.
- When a target defines a cache and the user passes `--invalidate`, the
  system must invalidate that target's cache (current behaviour, scoped
  to the selected target).
- When the user passes `--policy`, the system must generate the minimal IAM
  policy for the selected (or default) target only, covering only the
  resources that target actually defines (no CloudFront statement for a
  cache-less target). Split the current single statement in two: S3 and
  CloudFront.
- When the config file uses the old (pre-targets) schema and contains
  real values (not the placeholder bucket), the system must, on load, rewrite
  it in the new schema as a single target that is the default, save a
  backup of the original file alongside it, inform the user that the config
  was migrated (naming both file paths), and continue executing the requested
  command in the same invocation.
- When the config file uses the old schema but still contains the placeholder
  bucket (unconfigured), the system must treat it as unconfigured (current
  first-run flow) and must not create a backup before replacing with new-schema.
- When no config file exists, the system must write the new-schema template
  and follow the current first-run flow (print path, exit 1).
- When a target's storage or cache declares a provider type other than
  the supported ones (S3 storage, CloudFront cache), the system must exit
  with an error naming the target, the offending key/value, and the
  supported values.
- When the config marks a default target that is not defined, the system
  must exit with an error naming the bad reference and listing defined
  targets.
- All existing single-target workflows must keep working unchanged after
  migration: a user with one migrated target runs the same commands as
  today with the same observable results (aside from the one-time migration
  notice).

## Rules & Constraints

- Each target independently configures its own credentials/session and
  service settings (equivalent of today's `[aws.session]` / `[aws.service]`);
  targets may point at different AWS accounts.
- Only storage is required per target; the public URL and the cache are
  both optional and independent of each other.
- The migration must never destroy user data: the original file's content must
  be preserved in a backup before the rewrite, and a failed migration must not
  leave a half-written config.
- Migration is one-way and happens at most once per file; an already-migrated
  (new-schema) file is never rewritten on load.
- The new schema must keep a place for provider-specific advanced options so
  nothing expressible today (session keys, `verify = true`, etc.) becomes
  inexpressible.
- Target names must be usable verbatim on the command line; the accepted
  character set must be defined and validated with a clear error.
- CLI compatibility: all existing flags keep their long names and semantics;
  the target selector is additive. (Amended 2026-07-11 with the user: the
  selector takes the `-t` short form, and `--content-type` becomes
  long-only — see `Architect.md` and the resolved open question 1 in
  `specs/1.0-release.md`.) This lands with (or before) the major
  version whose release notes promise config-format stability — the schema
  break and the stability promise must not contradict each other
  (`specs/1.0-release.md` housekeeping section).
- The first-run/unconfigured detection currently keyed on the placeholder
  bucket (`example-bucket`) must have an equivalent in the new schema, since
  the planned setup wizard (1.0 spec item 2) uses it as its trigger.
- Error messages include identifiers (target name, bucket, file paths)
  and the user's next step (project convention).
- Module boundaries hold: config parsing/migration stays in `config.py`, AWS
  calls stay in `aws.py`, all user-facing output stays in `main.py`.
- Tests cover default + custom values for every new config key; coverage gate
  stays at 95%. Docs pages remain ASCII-only MyST Markdown.

## Edge Cases

| Scenario | Expected behaviour |
|----------|--------------------|
| Named target does not exist | Error naming it and listing defined targets; exit non-zero |
| No selector, no default, one target defined | That target is used silently |
| No selector, no default, multiple targets | Error listing names; tells user to select or set a default |
| Default key references an undefined target | Error naming the bad reference and listing defined targets |
| Config defines zero targets | Treated as unconfigured: same flow as missing/placeholder config |
| Target with no public URL | Output uses the storage identifier (bucket name) in place of the URL prefix, then the remote path; everything else unchanged |
| Target with URL but no cache, or cache but no URL | Both valid; the two options are independent |
| `--invalidate` on cache-less target | Other operations complete; notice printed that invalidation is skipped; exit 0 |
| `--invalidate` alone (no files) on cache-less target | Notice printed; exit 0 |
| `--policy` on cache-less target | Policy contains storage statements only, no CloudFront resource |
| Old-schema config with real values | Migrated in place; backup written; notice with both paths; command continues |
| Old-schema config still holding placeholder values | Unconfigured flow; no migration, no backup |
| Backup target file already exists (repeat/interrupted migration) | Migration must not silently overwrite an existing backup; it fails safely with an explanatory error |
| Unknown storage/cache provider type in config | Error naming target, key, value, and supported values |
| Target name with characters the CLI/TOML can't round-trip | Rejected at load with a clear error stating the allowed name format |
| Same bucket used by two targets | Allowed; targets are independent profiles |

## Open Questions

Questions resolved during this phase, with confirmed answers.

| Question | Answer |
|----------|--------|
| Selection when no target is given? | Use a configurable default (explicit default marker; single defined target acts as implicit default; multiple without a marker is an error). Confirmed. |
| What happens to existing old-schema configs? | Auto-migrate in place to the new schema, preserving a backup of the original. Confirmed. |
| Should the schema anticipate non-AWS providers? | Yes — generic storage/cache sections with a provider discriminator; S3 and CloudFront are the only accepted values for now. Confirmed. |
| `--invalidate` on a target without cache? | Skip with a notice and exit 0; the rest of the command runs normally. Confirmed. |
| `--policy` scope with multiple targets? | Per selected/default target only; "all targets" output is a possible future additive feature. Confirmed. |
| Does each target carry its own credentials? | Yes — session/service settings are per target. Confirmed. Commonalities can be created through several targets pointing to the same AWS profile. |
| Is the public URL required per target? | No — only storage is required; URL and cache are both optional. Confirmed. |
| What is printed when a target has no URL? | The storage identifier (bucket name) takes the place of the URL prefix, followed by the remote path. Confirmed. |

## Analyst Checklist

- [x] Goal is tied to a specific user need
- [x] Scope boundaries are explicit — what's in and what's out
- [x] All ambiguities resolved — no open questions remain (two Analyst defaults flagged for review)
- [x] Behaviour is declarative, not prescriptive
- [x] Edge cases are identified and handled
- [x] Non-goals prevent scope creep
