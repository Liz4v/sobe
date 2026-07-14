# Analyst: `-p/--prefix` rename (CLI 1.0 freeze, final item)

> Phase 1 — Problem definition. Approved before architecture begins.

## Goal / Outcome

**Scope classification:** Medium

Close the last pending CLI-surface change before the 1.0 freeze
(`specs/1.0-release.md`, item 3, decision resolved 2026-07-11): the flag that
sets the remote directory is named `-y/--year`, but it accepts arbitrary
prefixes — the name misdescribes the behavior and would be locked in by the
1.0 compatibility contract. `-p/--prefix` becomes the documented name;
`--policy` (rare, diagnostic) donates its `-p` short option. `-y/--year`
remain as deprecated aliases through 1.x and are slated for removal in 2.0.

The companion half of the freeze decision (`-t` reassigned from
`--content-type` to `--target`) already shipped with the multi-target change;
this spec covers only the `--prefix`/`--policy` half plus the deprecation
lifecycle for `-y/--year`.

## Scope

**Included:**

- Rename: `-p/--prefix` is the primary flag for setting the remote directory,
  with semantics identical to today's `--year`.
- `--policy` becomes long-only (loses `-p`).
- `-y/--year` kept as deprecated aliases: functional, shown in `--help`
  marked deprecated, and emitting a runtime deprecation warning on stderr.
- Passing both `--prefix` and `--year` in one invocation is an error.
- All user-facing text that names the flag (help text, `parse_args()` error
  messages) refers to `--prefix`.
- Leading-slash normalization: any leading slashes in the value are stripped,
  so `--prefix /` means the bucket root and `--prefix /2024` means `2024/`.
  (Today a leading slash silently creates distinct S3 keys like
  `/filename.txt` — a footgun being removed before the freeze.)
- Documentation updates: `docs/usage.md` examples and prose move to `--prefix`,
  documenting `--prefix /` as the recommended way to upload to the bucket root
  (replacing the awkward `--prefix ''` spelling in examples), with a note that
  `--year` is a deprecated alias removed in 2.0;
  `specs/1.0-release.md` item 3 / open question 1 annotated as implemented.
- Tests covering the new flag, the aliases, the warning, and the conflict
  error.

**Excluded (non-goals):**

- Actually removing `-y/--year` — that happens in 2.0, not here. This spec
  only establishes the deprecation.
- Any change to prefix semantics beyond the leading-slash normalization
  above (default-to-current-year, trailing-slash normalization, and empty
  string meaning bucket root are all unchanged).
- Any way to intentionally create leading-slash S3 keys — deliberately
  dropped; nobody plausibly wants them.
- Any other flag or flag-combination change; the rest of the `parse_args()`
  validation matrix is a frozen contract.
- `--list` filtering (separate post-1.0 spec).

## Behaviour

- When the user passes `-p <value>` or `--prefix <value>`, the system must use
  that value as the remote directory prefix, with behavior identical to
  today's `--year <value>` (including the "requires files or `--list`"
  constraint, trailing-slash normalization, and `''` meaning the bucket
  root) except for the leading-slash rule below.
- When the value begins with one or more slashes, the system must strip all
  leading slashes before any other normalization: `--prefix /` and `--prefix //`
  mean the bucket root (same as `--prefix ''`), and `--prefix /2024` means
  `2024/`. Object keys must never begin with `/`. This applies identically
  through the `-y`/`--year` aliases.
- When neither `--prefix` nor `--year` is given, the system must default the
  remote directory to the current year, as today.
- When the user passes `-y <value>` or `--year <value>`, the system must
  behave exactly as if `--prefix <value>` had been passed, and must additionally
  emit a one-line deprecation warning on **stderr** naming the replacement
  and the removal version (e.g. `warning: --year is deprecated, use --prefix;
  it will be removed in sobe 2.0`). The warning must not appear on stdout,
  so piped output is unaffected.
- When the user passes both `--prefix` and `--year` (any short/long spelling of
  each) in one invocation, the system must reject the invocation with a
  parser error (exit code 2), consistent with the existing strict
  flag-combination validation.
- When the user runs `sobe --help`, the output must list `-p/--prefix` as the
  primary flag with the remote-directory help text, and must list
  `-y/--year` marked as a deprecated alias for `--prefix` slated for removal
  in 2.0.
- When the user passes `--policy`, the system must behave exactly as today;
  `-p` must no longer invoke it.
- When a `parse_args()` validation error involves the remote-directory flag,
  the message must name `--prefix` (e.g. `--prefix requires files or --list to be
  specified`).

## Rules & Constraints

- Prefix semantics are unchanged except for leading-slash stripping; the
  rest is a rename plus deprecation, nothing more. The stripping is a
  deliberate pre-freeze behavior change: 0.x turns `-y /file` inputs into
  literal leading-slash S3 keys, and 1.0 removes that footgun rather than
  contracting it.
- stdout discipline: `main.py` is the only module that writes user-facing
  output, and normal output goes to stdout; the deprecation warning is the
  one message that must go to stderr instead.
- The deprecation warning must appear at most once per invocation, regardless
  of how the alias was spelled.
- All existing 0.x invocations using `-y`/`--year` must keep working
  throughout 1.x (aliases are part of the 1.x compatibility contract).
- Docs remain ASCII-only (Read the Docs PDF build constraint).
- Coverage gate (95%) and existing test conventions apply.

## Edge Cases

| Scenario | Expected behaviour |
|----------|--------------------|
| `sobe -p` (no value) — a 0.x user's muscle memory for `--policy` | argparse error `argument -p/--prefix: expected one argument`, exit 2. Fails loudly instead of silently doing the wrong thing. |
| `sobe -p file.txt` (0.x `--policy` habit with a stray arg) | `file.txt` is consumed as the path value; with no positional files left, the existing `--prefix requires files or --list` error fires. No accidental upload. |
| `sobe --prefix 2024 --year 2025 f.txt` | Parser error (conflicting flags), exit 2. |
| `sobe -y '' index.html` | Works as today (root upload) via the alias, plus one deprecation warning on stderr. |
| `sobe --prefix / index.html` | Root upload — key `index.html`, equivalent to `--prefix ''`. Documented as the recommended root spelling. |
| `sobe --prefix /` (alone, no files, no `--list`) | Validation error naming `--prefix`, exit 2 — unlike `--prefix ''` alone, which keeps the frozen help-and-exit-0 quirk (`/` is truthy when flags are counted, `''` is not). |
| `sobe --prefix /2024 f.txt` | Leading slash stripped; identical to `--prefix 2024` (key `2024/f.txt`). In 0.x this created key `/2024/f.txt`. |
| `sobe --prefix //2024/ f.txt` | All leading slashes stripped, trailing slash already present; key `2024/f.txt`. |
| `sobe -y / index.html` | Alias gets the same normalization: root upload, plus the deprecation warning. |
| `sobe --year 2024 --list` | Works (alias applies everywhere `--prefix` does); deprecation warning still emitted. |
| `sobe --year 2024` with no files and no `--list` | Existing validation error, now worded with `--prefix`; whether the deprecation warning also appears on this failing invocation is not contractual. |
| Warning while stdout is piped (`sobe -y 2024 f.txt > log`) | Upload output goes to stdout/log; warning goes to stderr and remains visible on the terminal. |
| `sobe --policy` | Unchanged behavior. |

## Open Questions

Questions resolved during this phase, with confirmed answers.

| Question | Answer |
|----------|--------|
| Runtime deprecation warning for `-y/--year` in 1.x? | Yes — one line per invocation, on stderr, naming `--prefix` and the 2.0 removal. (Confirmed 2026-07-12.) |
| Show `-y/--year` in `--help` or hide it? | Shown, marked deprecated (e.g. "deprecated alias for --prefix (removed in 2.0)"). (Confirmed 2026-07-12.) |
| Both `--prefix` and `--year` given? | Parser error, exit 2. (Confirmed 2026-07-12.) |
| Do prefix semantics change at all? | Only leading-slash stripping (below); default year, trailing-slash normalization, and `''` root behavior are untouched. |
| Should `--prefix /` mean the bucket root? | Yes — strip *all* leading slashes from the value, so `/` (and `//`) mean root and `/2024` means `2024/`; leading-slash S3 keys become unrepresentable. Docs recommend `--prefix /` for root uploads. (Confirmed 2026-07-12.) |

## Analyst Checklist

- [x] Goal is tied to a specific user need
- [x] Scope boundaries are explicit — what's in and what's out
- [x] All ambiguities resolved — no open questions remain
- [x] Behaviour is declarative, not prescriptive
- [x] Edge cases are identified and handled
- [x] Non-goals prevent scope creep
