# Analyst: First-Run Onboarding (Tutorial Pointer)

> Phase 1 — Problem definition. Approved before architecture begins.

## Goal / Outcome

**Scope classification:** Medium

sobe's first-run experience today writes a template config file and exits 1, telling
the user to edit it themselves. An earlier pass at this problem proposed an interactive
wizard that would ask AWS-specific setup questions (bucket name, base URL, CloudFront
distribution ID) and even gate on "do you have an AWS account yet?" That approach was
rejected: there is a large gap between "has an AWS account" and "has a working bucket +
CloudFront distribution + ACM HTTPS certificate + DNS CNAME record" — real
infrastructure work that a handful of CLI prompts cannot meaningfully shortcut or
validate. A wizard that can't create those resources for the user, and can't verify
they exist, mostly just re-asks the same questions the config file already asks, while
adding a pile of interactive-prompt code and tests for very little real benefit.

Instead, this pass keeps the current write-template-and-exit behavior, but (a) fixes
the real bug where `--help`/`--version` touch the config file before argument parsing
even happens (bare `sobe` deliberately keeps today's first-run behavior — running the
tool once to create the config is the documented onboarding flow and stays supported),
and (b) points the exit message at a proper onboarding tutorial (to be hosted on Read the Docs) that can actually walk a beginner through the
full AWS-side setup. This closes item 2 of `specs/1.0-release.md` with a narrower,
docs-first answer, and resolves that spec's open question 4 (auto-printing `--policy`
output) as "no" — the policy is only meaningful once a real target is configured, which
this pass does not attempt to automate.

The tutorial's content already exists as a draft at
[`TutorialOutline.md`](TutorialOutline.md) (account setup, bucket, CloudFront, sobe
install/config, IAM policy via `--policy`, custom domain, ACM certificate). This spec
references that draft as the source for the new Sphinx page rather than restating or
redesigning it; turning it into an actual MyST doc page is a Phase 2/3 concern.

## Scope

**Included:**
- Reordering `main()` so `parse_args()` always runs before any config file access.
  `--help` and `--version` must exit 0 without reading or writing a config file, in
  every case (config present, absent, or unconfigured). Bare `sobe` invocation keeps
  today's behavior in every config state: it goes through the config phase first, so a
  missing config still writes the template and exits 1 (now with the tutorial pointer),
  an unconfigured one still exits 1, and a configured one prints help and exits 0.
- Updating the messages printed for both `MustEditConfig(created=True)` (no file
  existed) and `MustEditConfig(created=False)` (file exists but unconfigured) to
  include a pointer to a new onboarding tutorial, in addition to the existing config
  path line.
- Establishing that a new Sphinx doc page must exist as the tutorial's home and be
  reachable from that pointer, sourced from [`TutorialOutline.md`](TutorialOutline.md).

**Excluded (non-goals):**
- Any interactive setup wizard, AWS-account gating question, input validation/prompt
  flow, overwrite-confirmation flow, or abort handling — rejected in favor of the
  tutorial-pointer approach.
- Automatically printing the IAM policy (`--policy` output) during first run — deferred
  indefinitely; `--policy` remains a separate, manual command that the tutorial will
  reference as a follow-up step once a real target exists.
- Any live AWS API calls or validation of typed values.
- Any change to `DEFAULT_TEMPLATE`'s content, `Config.is_unconfigured()`, or
  `Target`/`Config.from_dict()` validation logic.
- Reordering or changing the tutorial's facts, section order, or warnings —
  [`TutorialOutline.md`](TutorialOutline.md) is the structural and factual source of
  truth; the Sphinx page follows its section order and preserves every fact, warning,
  and value verbatim. Turning its terse bullets into full explanatory prose for the
  actual doc page (matching the outline's existing first-person voice) is in scope for
  this pass, since a bullet-only page is not usable as a real tutorial; see Architect.md
  for how content is fleshed out.
- Any new CLI flags.
- Changing `--list` filtering behavior (out of scope per the parent 1.0 spec).

## Behaviour

- When `sobe --help` or `sobe --version` is invoked, in any position argparse honors,
  the system must answer and exit 0 without reading or writing any config file,
  regardless of whether a config file exists, is missing, or is unconfigured.
- When `sobe` is invoked with no arguments, the config phase runs first, exactly as it
  does today: missing config file → template written, message + tutorial pointer,
  exit 1; existing unconfigured file → file untouched, message + pointer, exit 1;
  configured file (including one just migrated from the old schema) → print help,
  exit 0. This deliberately preserves the documented "run `sobe` once to create the
  config" onboarding flow.
- When a command that needs config is invoked with arguments that parse and validate
  successfully, and no config file exists, the system must write the default template
  (unchanged from today), print a message that identifies the written file's path and
  points to the onboarding tutorial, and exit 1. (Argument validation now runs first:
  an invocation that fails parsing/validation — unknown flag, missing local file, bad
  flag combination — exits on that error without any config file being read, written,
  or migrated.)
- When a command that needs config is invoked and a config file exists but is
  unconfigured (per `Config.is_unconfigured()`), the system must leave that file
  untouched, print a message that identifies the file's path and points to the
  onboarding tutorial, and exit 1.
- When a config file is already configured, behavior must be unchanged from today in
  every respect.
- When an old-schema config file needs migration, behavior must be unchanged from today
  (migration still runs, and still happens before the unconfigured check).
- The onboarding tutorial must be reachable via the pointer included in both first-run
  messages (exact URL/path decided in Phase 2/Architect).

## Rules & Constraints

- No AWS API calls are introduced.
- Exit codes are unchanged: both `MustEditConfig` branches still exit 1. Only the
  printed message text changes; the compatibility promise ("exit codes are stable
  within 1.x") is preserved by construction since nothing here changes an exit code.
- `MustEditConfig`'s existing signature (`path`, `created`) is preserved; only what
  `main.py` prints when it catches the exception changes.
- Doc pages must stay ASCII-only (Read the Docs builds a PDF via pdflatex that breaks
  on non-ASCII characters) — applies to the tutorial page written in this pass.
- Placeholder values in any new docs or messages stay generic (`example.com`-style),
  matching project convention.

## Edge Cases

| Scenario | Expected behaviour |
|----------|--------------------|
| No config file present, `sobe --version` | Exit 0; no file created or touched (fixes today's bug where the template is written and the process exits 1 before argparse can answer). |
| No config file present, bare `sobe` | Unchanged from today: template written, message + tutorial pointer, exit 1. |
| Configured config file, bare `sobe` | Unchanged from today: help printed, exit 0 (config is read; old-schema migration still runs first with its notice). |
| No config file present, upload/list/delete command | Template written (unchanged content); message includes path + tutorial pointer; exit 1. |
| Existing unconfigured file, any config-needing command | File untouched; message includes path + tutorial pointer; exit 1. |
| Existing configured file | Entirely unchanged from today, including for `--help`/`--version`/bare invocation. |
| No config file present, `sobe nonexistent.txt` | parse_args' file-existence check fails first: "The following files do not exist" + exit 1; no config file created or touched. |
| No config file present, invalid flag combo (e.g. `sobe --prefix 2024` with no files) | argparse validation error, exit 2; no config file created or touched. |
| Old-schema config file needing migration | Unchanged — migration still runs before the unconfigured check. |

## Open Questions

| Question | Answer |
|----------|--------|
| Should sobe build an interactive, AWS-account-aware setup wizard? | No — rejected. The gap between "has an AWS account" and "has a working bucket + CloudFront + ACM cert + DNS CNAME" is real infrastructure work a CLI wizard cannot close or verify; a tutorial page serves that gap honestly. |
| Parent spec's open question 4: should first run auto-print the IAM policy (`--policy` output)? | No — deferred. There's no real target to compute a policy for until the user has actually configured one by hand; `--policy` stays a manual, documented follow-up step. |
| Where is the tutorial's content/outline decided? | Structure and facts are already drafted at [`TutorialOutline.md`](TutorialOutline.md); this spec follows that order and preserves every fact verbatim, but fleshes the terse bullets out into full prose for the actual Sphinx page (see Architect.md). |

## Analyst Checklist

- [x] Goal is tied to a specific user need
- [x] Scope boundaries are explicit — what's in and what's out
- [x] All ambiguities resolved — no open questions remain
- [x] Behaviour is declarative, not prescriptive
- [x] Edge cases are identified and handled
- [x] Non-goals prevent scope creep
