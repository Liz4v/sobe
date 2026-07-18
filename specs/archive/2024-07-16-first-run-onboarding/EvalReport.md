# Eval Report: First-Run Onboarding (Tutorial Pointer)

> Phase 5 — Post-implementation evaluation. Run after sdd-coder completes.
> Evaluator had no access to the coder's reasoning — fresh context only.
> Evaluated 2026-07-15 against the uncommitted working tree (diff vs HEAD 9bfd712).

## Computational Sensors

| Check | Result |
|-------|--------|
| Lint (`uv run ruff check`) | ✅ 0 errors |
| Format (`uv run ruff format --check`) | ✅ 10 files already formatted |
| Tests (`uv run pytest`) | ✅ 157 passed, 0 failed |
| Coverage (gate 95%) | ✅ 100% |
| Docs ASCII check (`grep -rnP '[^\x00-\x7F]' docs --include='*.md'`) | ✅ empty |
| Sphinx HTML build (fresh `-E` rebuild) | ✅ succeeded, no WARNING/ERROR lines |
| Sphinx LaTeX + PDF build (nix-shell pdflatex) | ✅ succeeded, `sobe.pdf` produced |

All six Task 10 gate checks pass (HTML and PDF counted separately above).

## Semantic Evaluation

| Criterion | Verdict | Detail |
|-----------|---------|--------|
| CONTRACT | ⚠️ | All files exist; `TUTORIAL_URL`, exact three-line message text, `_build_parser()` extraction, `args.bare` mechanics, and bare-defer flow match Architect.md precisely (`src/sobe/main.py:20`, `30-34`, `44-46`, `89-102`, `115-121`). Minor: `docs/tutorial.md:212-214` adds an `{eval-rst}` block not specified anywhere; `TutorialOutline.md` (declared source of truth) was itself edited. |
| BEHAVIOUR | ✅ | Control flow traced against the First-Run Behavior Contract table: `--help`/`--version` exit inside argparse before `load_config()` is reachable; bare `sobe` always enters the config phase and prints help only on success; validation errors preempt all config access; migration order unchanged. |
| EDGE CASES | ✅ | Every row of Analyst.md's edge-case table is satisfied and exercised by a test (`TestMainArgsBeforeConfig` covers the no-config `--help`/`--version`/invalid-combo/bare cases; existing tests cover the rest). |
| TESTS | ✅ | All promised updates present: pointer-print assertions (`tests/test_main.py:488`, `501`), `bare=False` in `_mock_args` (`:476`), renamed bare tests (`:67`, `:255`), `bare is False` in a non-bare case (`:95`), stale comment fixed (`:366-369`), new 5-case `TestMainArgsBeforeConfig` class (`:742-804`) that would fail if the reorder or bare-defer were reverted. |
| PATTERNS | ❌ | (a) `docs/tutorial.md:212-214` uses reST (`.. tabularcolumns::` inside `{eval-rst}`) in a doc page, against AGENTS.md's "Markdown (MyST) ... not reST" convention — though it plausibly exists to keep the wide ACM table inside the PDF page, the risk Task 10 itself flagged. (b) `README.md:11` edited despite AGENTS.md's "don't modify README.md unless it contains false information". |
| COVERAGE | ✅ | 100% vs 95% gate; no new untested branches (the only pragma predates this feature). |
| NO EXTRAS | ❌ | Four items of content not authorized by the spec — see Findings. |

## Findings

1. **❌ NO EXTRAS — tutorial fact rewritten, not fleshed out.**
   `docs/tutorial.md:14-15` vs `specs/first-run-onboarding/TutorialOutline.md:5`.
   Outline (source of truth): addresses are "permanently yours as long as your cloud
   account is in good standing." Shipped page: "permanently yours as long you keep
   your domain (or your public cloud account if you don't use your own domain)" — a
   materially different claim (new domain-retention condition), violating the
   explicit non-goal "preserves every fact, warning, and value verbatim." Also
   contains a typo ("as long you").

2. **❌ NO EXTRAS / spec integrity — source-of-truth outline edited during
   implementation; new facts introduced.**
   `specs/first-run-onboarding/TutorialOutline.md:16` gained a post-hoc annotation
   moving region guidance from "Create an AWS account" into `docs/tutorial.md`'s
   "Create a bucket" section. The relocation itself is arguably sensible, but the
   spec was altered to match the build rather than the build following the spec, and
   the tutorial additionally invents facts absent from the outline: "CloudFront is a
   global service (the console's region picker switches to 'Global')"
   (`docs/tutorial.md:80-82`) and "Like CloudFront, IAM is a global service ... no
   region to pick" (`docs/tutorial.md:131-133`).

3. **❌ NO EXTRAS / PATTERNS — README and index gained an unspecced pronunciation
   note.**
   `README.md:11` and `docs/index.md:9` both add `(pronounced SAW-bee)`. No spec
   document mentions it; Task 7 explicitly states "README.md needs no change" and
   AGENTS.md forbids README edits unless content is false. *Caveat: the evaluation
   ran against the uncommitted working tree — if this edit is the user's own
   unrelated change rather than the coder's, this finding is moot for README, though
   `docs/index.md` was a spec-listed file.*

4. **⚠️ PATTERNS — reST directive in a MyST doc page.**
   `docs/tutorial.md:212-214`: `{eval-rst}` block with `.. tabularcolumns::`.
   Violates the "MyST, not reST" convention and appears in no task description.
   Mitigating context: Task 10 predicted the ACM CNAME table was "the likeliest new
   page to break or overflow the PDF build," and the PDF does build clean with this
   directive present — it is plausibly load-bearing, but it was never specced or
   its necessity documented.

## Verdict

- [x] **PASS** — ready to archive (initial FAIL superseded by user ratification, see below)
- [ ] **PARTIAL PASS** — only ⚠️ warnings, archive with known gaps noted
- [ ] **FAIL** — one or more ❌, specific items must go back to coder

Behaviour, edge cases, tests, and every computational sensor are green; the failures
were all spec-fidelity issues in the documentation surface, not code defects.

**Resolution (2026-07-16):** the user confirmed all four findings are her own
deliberate post-coder edits, not coder deviations: the "permanently yours" rewording
(finding 1), the region-guidance relocation and global-service notes plus the outline
annotation documenting them (finding 2), the `(pronounced SAW-bee)` note in README
and index (finding 3), and the `tabularcolumns` directive for the wide ACM table in
the PDF build (finding 4). All ratified as intentional; verdict revised from FAIL to
PASS. The Findings section above is retained as the audit trail.
