# Critic Review: First-Run Onboarding (Tutorial Pointer)

> Phase 3 — Plan stress-test. Approved before coding begins.
> This review went through two rounds. Round 1 = self-critique.
> Round 2 = fresh-eyes adversarial pass by an independent agent (fresh context window).
> All blocker and warning fixes were applied directly to the spec files in the same
> session; cross-references below say where.

## Post-harden scope change (2026-07-15, user decision) + Round 3 verification

After both rounds completed, the user decided bare `sobe` **should keep today's
first-run behavior** (the original hardened design had it print help and exit 0 without
touching config). Revised design: `--help`/`--version` still never touch config (the
actual bug); bare invocation parses first, sets `args.bare`, runs the config phase
(template/message/pointer + exit 1 when missing/unconfigured; migration as today), and
prints help + exit 0 only when config is fine — via a new `_build_parser()` extraction
so `main()` can print help. All spec files were updated in the same session.

Effect on earlier findings:

- **Round 1 B1 — reverted.** Bare first run is retained, so "Run `sobe` once" is
  accurate again: the TutorialOutline correction was undone, and Steps 6/7 went back to
  transcript-update-only (usage.md keeps `$ sobe`; configuration.md's opening sentence
  gains only a `--help`/`--version` parenthetical).
- **Round 2 W1 — dropped.** README's "On first run, sobe will create its config file"
  stays true under the natural bare-run reading; Step 7b was removed per the
  "README only when false" rule.
- **Round 2 note (migration side effect) — narrowed.** Only `--help`/`--version` lose
  the migration side effect; bare `sobe` still migrates, as today. Delta.md updated.
- **Round 2 W3 (parse errors preempt template) and W4 (PDF build in gate) — unchanged,
  still applied.** Round 1 W1 (OQ4 annotation) unchanged.
- **New test surface:** `TestMain._mock_args` needs `bare=False`; two `TestParseArgs`
  tests that asserted self-printed help on bare input are updated to assert the
  returned `bare` flag; Step 3 grew bare-with-config-phase cases (see tasks.md
  Steps 2-3).

### Round 3 (fresh-eyes verification of the revised design) — findings

A focused fresh-eyes pass verified the revised bare-`sobe` design against the actual
code. Verdict: the design itself (bare flag, `_build_parser()` extraction, `main()`
ordering, test plan) is sound. 1 blocker + 3 warnings, all stale-text leftovers from
the pre-revision spec, all applied:

| ID | Finding | Where fixed |
|----|---------|-------------|
| R3-B1 | Architect.md Files-to-Modify `docs/usage.md` row still said the transcript command "becomes `sobe --list`" — contradicting revised tasks.md Step 6 and the contract table; a coder following the table would rewrite the transcript wrongly. | Architect.md Files to Modify (usage.md row) |
| R3-W1 | Same table's `docs/configuration.md` row still said config is "not" created on bare invocation. | Architect.md Files to Modify (configuration.md row) |
| R3-W2 | Data Model section claimed "no new `argparse.Namespace` attributes" while the design hinges on the new synthesized `bare` attribute. | Architect.md Data Model Changes |
| R3-W3 | tests/test_main.py `test_prefix_slash_alone_errors` comment ("frozen help-and-exit-0 quirk") becomes false — `--prefix ''` alone is bare, now config-state-dependent (test outcome unchanged). | tasks.md Step 2 (comment fix added) |

Round 3 verified TRUE (spot-check summary): nothing intervenes between the
`num_arg_types` computation and the bare check, and setting `args.bare` afterwards
cannot perturb the count (`args.__dict__` is read nowhere else); every returning path
gets `bare` set (all others raise); bare + ConfigError / bare + migration produce
byte-identical output and ordering vs. today; the only two tests hitting the bare path
and the only two patching `ArgumentParser.print_help` are exactly the two Step 2
rewrites; all `TestMain` Namespaces come from `_mock_args`, so one `bare=False` default
fixes the class; no coverage risk (every new branch has a specced test). Noted, no
action: `sobe -y ""` / `-p ""` / `-t ""` count as bare (falsy values), matching today's
behavior in every config state except that the `--year` deprecation warning now prints
even when config is missing — consistent with parse-first; and the configuration.md
parenthetical deliberately omits the parse-error preemption nuance.

The original two rounds' findings follow, preserved as history.

---

## Round 2 (fresh-eyes) — findings

A second adversarial pass with a fresh context window found 0 additional blockers and
4 warnings that Round 1 missed. All warnings have been applied. Round 2 also verified
the reorder breaks none of the 83 existing tests (TestMain class-decorates
`parse_args`/`load_config`/`AWS`, so mock order is unaffected) and that no currently
covered line of `main()` becomes unreachable.

### Round 2 Blockers (applied)

None found. (For a 10-step spec of this size — a pure statement reorder plus one print
line plus one doc page — zero fresh-eyes blockers is consistent with the empirical
baseline, which calibrates the 2–5-blocker expectation on specs of >15 steps. The
Round 2 prompt covered all 14 checklist categories.)

### Round 2 Warnings (applied)

| ID | Finding | Where fixed |
|----|---------|-------------|
| W1 | `README.md:29` ("On first run, `sobe` will create its config file...") becomes false after the reorder and was missing from the modify list — Round 1 fixed the same claim in `usage.md` and `configuration.md` but missed this third instance. The project rule explicitly permits README edits when content is false. | tasks.md new Step 7b; Architect.md Files to Modify (README.md row) |
| W2 | `Delta.md` and `Analyst.md` carried stale pre-scope-change text: Delta said the tutorial page's content "is scoped separately; this pass only requires the page to exist", and Analyst's ASCII rule referred to content "written in the follow-up pass" — both contradicting the current scope (full prose written in this pass). | Delta.md ADDED section (page-scope bullet rewritten); Analyst.md Rules & Constraints (ASCII bullet) |
| W3 | Behavior-contract gap: after the reorder, argument parse/validation errors preempt template creation — `sobe missing.txt` exits 1 on the file-existence check and `sobe --prefix 2024` exits 2, with no config template written even though a "command that needs config" was invoked. Analyst promised the template unconditionally; only the unknown-flag case was noted in Architect's risks. | Analyst.md Behaviour bullet (validated-args qualifier) + two new Edge Cases rows; Architect.md contract table (two new rows); tasks.md Step 3 (fourth test case: `--prefix 2024` -> exit 2, `load_config` never called) |
| W4 | Step 10's gate only built HTML, but Read the Docs builds `formats: all` (pdflatex), and `tutorial.md` introduces pipe tables with long unbreakable tokens (the ACM CNAME values) — the likeliest page to break the PDF build. AGENTS.md documents a local LaTeX validation command that the gate never ran. | tasks.md Step 10 (PDF build added as sixth check) |

### Round 2 Notes acknowledged

- Old-schema migration no longer fires on `--help`/`--version`/bare invocation — today
  those rewrite the config file in place as a side effect. Intended, but previously
  unstated. **Applied:** Delta.md MODIFIED section now records this behavioral removal
  explicitly (together with the W3 parse-errors-preempt-config-access point).
- Step 9's annotation must explicitly supersede item 2's "Decision (resolved
  2026-07-11): wizard" line and its wizard-specific acceptance criteria (the non-TTY
  "no file is created" criterion contradicts the retained template-write). **Applied:**
  tasks.md Step 9 now spells this out; the stale `main.py:20-28` line-link in item 2's
  Problem paragraph is deliberately left as-is (historical bug description in a
  resolved item).
- The `--year` deprecation warning (stderr, inside `parse_args`) now prints before the
  migration notice and `MustEditConfig` messages. **Not applied** — cosmetic ordering
  on stderr vs stdout; no spec text promises the old order.
- `CLAUDE.md` is a symlink to `AGENTS.md`, so Step 8 covers both automatically.
  **No action needed.**

### Round 2 Residual risks (couldn't be verified offline)

- That Read the Docs actually serves the project at slug `sobe` with default version
  `latest` — only repo-internal evidence (README badge and links) supports the
  `TUTORIAL_URL` pattern. Confirmed at implementation time by visiting the URL after
  the docs deploy, or accepted as graceful degradation (a dead link is printed text).
- That the not-yet-written `docs/tutorial.md` builds warning-free under
  `nitpicky = True` and renders its long-token tables acceptably in pdflatex — Step
  10's HTML + PDF builds are the gate for this.

### Round 2 assumptions verified TRUE (spot-check summary)

- The bug is real: `main.py:22` calls `load_config()` before `parse_args()` (line 39);
  `parse_args` self-exits 0 for `--help`/`--version` (argparse) and bare invocation.
- `test_bad_config_created` / `test_bad_config_existing_unconfigured` exist at
  tests/test_main.py:477/:487; `sobe.main.load_config` is the correct patch target.
- Architect's quoted message text matches `main.py:26-29` exactly; adding one line
  yields exactly three.
- MyST pipe tables: `myst_parser/parsers/mdit.py` calls `.enable("table")`
  unconditionally — no `conf.py` change needed.
- `https://sobe.readthedocs.io/en/latest/...` matches all four RTD references in
  README.md; no redirects/overrides in `.readthedocs.yaml` or `docs/conf.py`.
- `docs/index.md` "User Guide" toctree, `usage.md` transcript + placeholder path,
  `configuration.md` opening sentence, and AGENTS.md:27 "Flow:" sentence all exist as
  described; the archived `2026-07-13-prefix-flag-rename` annotation-style reference
  is sound.

---

## Round 1 (self-critique) — findings

Adversarial pass across the eight lenses, with codebase verification (main.py,
config.py, tests/test_main.py, docs/, README.md, AGENTS.md, specs/1.0-release.md).

### 🔴 Blockers

| ID | Lens | Finding | Where fixed |
|----|------|---------|-------------|
| B1 | Correctness / Completeness | The reorder makes bare `sobe` print help and exit 0 **without creating the config file**, but three doc surfaces in the plan still taught the removed flow: (1) `TutorialOutline.md` "Run `sobe` once. If no config file exists yet, it creates one" — and Step 4 mandated preserving that fact verbatim, so the shipped tutorial would strand a beginner at a help screen; (2) Step 6 kept `$ sobe` as the `usage.md` transcript command while only adding the third message line; (3) Step 7 missed `configuration.md`'s opening "The first time you invoke the tool..." sentence. | TutorialOutline.md Install bullet corrected to `sobe --list` (the one sanctioned fact change — invalidated by this spec itself); tasks.md Steps 4, 6, 7 rewritten; Architect.md Files to Modify rows + new "[Resolved in harden Round 1]" risk entry |

### 🟡 Warnings

| ID | Lens | Finding | Where fixed |
|----|------|---------|-------------|
| W1 | Completeness | Step 9 annotated 1.0-release item 2 but not **open question 4** (auto-print `--policy` on first run), which Analyst.md explicitly resolves as "no — deferred". | tasks.md Step 9 |

### 🟢 Notes

- Step 3's mock design ("raise AssertionError if invoked" + "assert never called")
  was slightly ambiguous about the mock object shape. **Applied cheaply:** step now
  specifies `Mock(side_effect=AssertionError(...))` so `assert_not_called()` works on
  the same object.
- Task 6's `[Tutorial](tutorial.md)` cross-reference needs Task 4's file to exist only
  at build time (Step 10), so the declared "depends only on Task 1" parallelisation
  stays valid. **No change needed.**
- `README.md:29` "On first run..." was assessed in Round 1 as borderline-true and left
  alone under the "only when false" README rule. **Superseded by Round 2 W1**, which
  judged it false for the bare-`sobe` reading and added Step 7b. Recorded here per the
  conflict-resolution rule: Round 1's "not applied" decision was overridden because
  Round 2 fresh-eyes read the sentence as a user would (bare first run), which the
  reorder makes false. Final state: README fixed via Step 7b.
- The hover.com affiliate link and real AWS console walk-through values in the tutorial
  are deliberate Analyst-approved content (personal, first-person tutorial), not
  placeholder-convention violations. **No change.**

### Round 1 verifications (all TRUE)

- Exact `MustEditConfig` message strings match `main.py:26-28`; `MustEditConfig(path,
  created)` signature untouched by the plan.
- `TutorialOutline.md` is ASCII-clean (`grep -P '[^\x00-\x7F]'` empty).
- MyST `.enable("table")` unconditional (verified in the installed docs venv).
- `docs/api/` pages are pure autodoc stubs — no stale first-run prose to update there;
  `config.py` docstrings don't describe the call order.
- Step count matched status.json (10 at the time; now 11 after Round 2's Step 7b).
- No scope creep: every task traces to Analyst.md's Included list or its doc/bookkeeping
  obligations; the parse-reorder is a pure statement move with no `parse_args` changes.

### Verdict

Round 1: **Needs revision** — 1 blocker, 1 warning, both applied same-session.
Round 2: **Approved** — 0 blockers, 4 warnings, all applied same-session.
Final: **Approved — implementation-ready.**
