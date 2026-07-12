# Tasks: Multiple Targets

> Phase 2 output — implementation checklist.
> Each step is atomic: one logical unit in one file.
> Dependencies and parallelisation opportunities are documented in Architect.md.
> Terminology: "target" everywhere (see the note atop Architect.md).

### Layer: Config (`src/sobe/config.py` — steps 1-6 sequential, same file)

- [ ] Step 1: Add the new data model: `ConfigError`, `StorageConfig`,
      `CacheConfig`, `Target`, `Migration`, and the new `Config` (targets
      dict + optional default) with `from_dict` validation — required keys,
      provider `type` discriminators (`aws_s3` / `aws_cloudfront` only),
      target-name regex `^[A-Za-z0-9_][A-Za-z0-9_-]*$` (no dots — TOML
      nesting), URL trailing-slash normalization. The new `Config`
      **replaces** the legacy `Config` (same name — they cannot coexist;
      legacy `Config` is deleted here). Keep `AWSConfig` untouched: `aws.py`
      imports it until step 10 (deleted in step 14). Also add
      `created: bool` to `MustEditConfig`. Done when: new classes
      parse/reject the schemas from Architect.md (exercised via step 7
      tests); `tests/test_main.py` is expected red until step 16 (imports
      the replaced `Config`).
- [ ] Step 2: Implement `Config.select(name)` with the four selection rules
      (named, default marker, single implicit, ambiguous-multiple) and their
      `ConfigError` messages listing defined target names.
- [ ] Step 3: Replace `DEFAULT_TEMPLATE` with the new-schema template and add
      the unconfigured test (zero targets, or every bucket still
      `example-bucket`).
- [ ] Step 4: Add the private TOML emitter for the new schema: scalar values
      only, strings emitted as escaped TOML basic strings (backslash, quote,
      control chars); `ConfigError` on non-scalar `aws_session`/`aws_service`
      values, naming the offending *key* only (values may be secrets) and
      telling the user to migrate that table by hand.
- [ ] Step 5: Add old-schema detection (top-level `aws`, no `target`) and
      `_migrate()` in this order: emit new-schema text in memory first (all
      failures happen before any write), then backup via `"xb"` (error if
      backup exists) preserving the original file's permission bits, then
      temp-file + `os.replace()`, return `Migration(path, backup)`.
- [ ] Step 6: Rewire `load_config() -> tuple[Config, Migration | None]`:
      new-schema parse; old-schema real values -> migrate and continue;
      old-schema placeholder -> write template + `MustEditConfig(created=True)`;
      unconfigured new-schema (zero targets / all buckets placeholder) ->
      `MustEditConfig(created=False)` **without rewriting the file**;
      missing file -> template + `MustEditConfig(created=True)`; wrap
      `tomllib.TOMLDecodeError` in `ConfigError` naming the file.

### Layer: Config Tests (`tests/test_config.py` — after step 6; parallel with step 10)

- [ ] Step 7: Tests for the model: default + custom values for every new key,
      each validation error (missing bucket, bad provider type, bad name,
      non-scalar `aws_session` value), URL normalization.
- [ ] Step 8: Tests for `Config.select`: all four rules plus unknown-name and
      bad-default errors, asserting the messages list defined names.
- [ ] Step 9: Tests for template/unconfigured/migration/load: new-schema load,
      placeholder old-schema (no backup, template written), real old-schema
      (backup + rewrite + `Migration` returned), existing-backup failure,
      failed emission leaves no backup behind, backup preserves permission
      bits, emitter escaping round-trips through `tomllib`, migrated file
      not re-migrated, unconfigured new-schema left untouched
      (`created=False`), zero-targets flow, missing-file flow
      (`created=True`), invalid TOML raises `ConfigError`.

### Layer: AWS (`src/sobe/aws.py`)

- [ ] Step 10: Rework `AWS` to consume `Target`: CloudFront client only
      when `cache` is set; `invalidate_cache()` reads
      `cache.distribution`; `generate_needed_permissions()` emits an S3
      statement always and a CloudFront statement only with a cache.
- [ ] Step 11: Update `tests/test_aws.py`: `Target` fixtures, cache-less
      construction, policy with and without cache (two statements / one).

### Layer: CLI (`src/sobe/main.py` — steps 12-13 sequential, same file)

- [ ] Step 12: Add `-t/--target` to `parse_args()`, demoting
      `--content-type` to long-only (`-t` is reassigned), and adjust the
      combination rules: allowed with `--policy` (exempt from the
      exclusivity check), error when passed with no operation; every other
      existing rule intact. Target-presence checks must use `is not None`,
      not truthiness: `sobe -t ""` must hit the no-operation/unknown-target
      errors, not fall through to help or silently select the default
      (the `num_arg_types` truthy count treats `""` as absent). Do not
      touch `-p` or `--year` (reserved for the 1.0 freeze audit).
- [ ] Step 13: Rework `main()`: unpack `(config, migration)` and print the
      migration notice; select the target before any operation, catching
      `ConfigError` (print, exit 1); use `target.url or f"{bucket}/"` as the
      display prefix in all three output sites; print the skip notice for
      `--invalidate` without a cache (exit 0); branch the `MustEditConfig`
      message on `err.created` ("created it, edit it" vs "exists but
      unconfigured, edit it").
- [ ] Step 14: Delete the legacy `AWSConfig` class from
      `src/sobe/config.py` (legacy `Config` was already replaced in step 1;
      nothing imports `AWSConfig` after steps 7, 10, and 11 —
      `tests/test_config.py`'s `isinstance` assertions are the third
      importer, rewritten in step 7).

### Layer: CLI Tests (`tests/test_main.py` — steps 15-16 sequential, same file)

- [ ] Step 15: Tests for `parse_args()` target rules: with each operation,
      with `--policy`, alone (error), `-t ""` (error, not help/default),
      `--content-type` still working long-only, old-style `-t MIME` failing
      loudly (invalid target name), and the preserved existing combinations
      (bare help, policy exclusivity against other flags).
- [ ] Step 16: Tests for `main()` flows: migration notice text, both
      `MustEditConfig` messages (`created` True/False), selection errors
      exit 1 with names listed, no-URL bucket-prefixed output for
      upload/delete/list/"no files", invalidate skip notice + exit 0,
      policy scoped to selected target. Update **every existing `TestMain`
      mock**: `load_config` now returns `(config, None)` and the
      `_mock_args` Namespace gains `target`. Full suite green at the 95%
      coverage gate from here on.

### Layer: Docs (steps 17-19c independent — safe in parallel)

- [ ] Step 17: Rewrite `docs/configuration.md`: new template, every key
      documented (target tables, storage/cache types,
      `aws_session`/`aws_service`, default, name rules), migration + backup
      behaviour, unconfigured flow. ASCII-only MyST.
- [ ] Step 18: Update `docs/usage.md`: `-t/--target` examples (and a note
      that `--content-type` is long-only now), cache-less
      `--invalidate` notice example, new two-statement `--policy` output,
      bucket-prefixed output example for a URL-less target, and the
      first-run console example (lines 17-23) whose quoted "Created config
      file..." output changes in step 13. Also fix the one-sentence intro
      in `docs/index.md` that presents CloudFront as structurally required.
- [ ] Step 19: Update `README.md`: replace the now-false old-schema TOML
      snippet with the new-schema equivalent, and fix the prose that
      becomes false with it — line 29 ("edit this file with your AWS
      bucket and CloudFront details") and the line 5 description of
      CloudFront as structurally required (minimal changes, per project
      convention: README edits only where content is false).
- [ ] Step 19b: Update `CLAUDE.md` architecture notes: the `config.py`
      bullet (placeholder check is no longer `aws.bucket ==
      "example-bucket"`; `load_config` returns `(Config, Migration | None)`),
      the flow line (`AWS(config.aws)` becomes `AWS(target)` after
      selection), and the `[aws.session]`/`[aws.service]` mention (now
      per-target `aws_session`/`aws_service`). Validation:
      `grep -n "example-bucket\|config.aws\|aws.session" CLAUDE.md` shows
      only accurate statements.
- [ ] Step 19c: Reconcile `specs/1.0-release.md` item 2 (first-run wizard)
      with this spec: its requirements hardcode the old schema — three
      required prompts including a CloudFront distribution ID (now optional
      per target), "preserving the commented `[aws.session]`/`[aws.service]`
      sections" (now per-target `aws_session`/`aws_service`), and
      "placeholder-detection ... retained as the wizard trigger" (now the
      new-schema unconfigured test defined in Architect.md). Update the
      wording so the wizard spec's acceptance criteria are implementable
      against the new schema; do not resolve its open questions.
      Validation: `grep -n "aws.session\|example-bucket\|CloudFront"
      specs/1.0-release.md` shows no old-schema requirement in item 2.
