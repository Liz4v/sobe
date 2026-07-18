# Delta: First-Run Onboarding (Tutorial Pointer)

> Specification delta — what changes relative to the current system.
> Supersedes the earlier wizard-oriented version of this file: the interactive wizard
> described there was rejected in favor of the narrower approach below.

## ADDED

- A pointer to a new onboarding tutorial page, included in both first-run messages
  (`MustEditConfig(created=True)` and `MustEditConfig(created=False)`).
- A new Sphinx doc page as the tutorial's home, written in this pass: full prose
  fleshed out from `TutorialOutline.md` (the structural and factual source of truth),
  preserving its section order, facts, and first-person voice.

## MODIFIED

- **`main()` calls `load_config()` before `parse_args()`** → `parse_args()` always runs
  first. `--help` and `--version` now exit 0 without ever reading or writing a config
  file, in every config-file state (missing, unconfigured, or configured). Bare `sobe`
  invocation keeps today's observable behavior in every config state (first-run
  template/message when config is missing or unconfigured, help + exit 0 when
  configured) — internally it now parses first and defers the help print until after
  the config phase.
- **Printed messages for `MustEditConfig(created=True)` and `MustEditConfig(created=False)`**
  → both gain a pointer to the onboarding tutorial, in addition to the existing config
  path line. Exit code (1) is unchanged in both cases.
- **Config access side effects of `--help`/`--version` are removed** → today, those
  two on an old-schema config file trigger the in-place migration (a config rewrite)
  as a side effect; after the reorder they never touch the file. Bare `sobe` still
  runs the config phase (and thus migration) as today. Likewise, an invocation that
  fails argument parsing/validation (unknown flag, missing local file, bad
  combination) now exits on that error without writing the template or migrating —
  argument errors preempt all config access.

## REMOVED

- The previously proposed interactive setup wizard: the AWS-account gating question,
  bucket/URL/CloudFront prompts with inline explanations, input validation and
  re-prompting, overwrite-confirmation flow, Ctrl-C/EOF abort handling, and automatic
  IAM-policy printing. None of this will be built — superseded by the tutorial-pointer
  approach above.
