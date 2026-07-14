# Eval Report: `-p/--prefix` rename (CLI 1.0 freeze, final item)

> Phase 5 — Post-implementation evaluation. Run after sdd-coder completes.
> Evaluator had no access to the coder's reasoning — fresh context only.

## Computational Sensors

| Check | Result |
|-------|--------|
| Backend lint (ruff check) | ✅ 0 errors |
| Backend format (ruff format --check) | ✅ 10 files already formatted |
| Backend tests (pytest) | ✅ 151 passed |
| Backend coverage | ✅ 100% ≥ 95% |
| Docs ASCII-only (`grep -rnP '[^\x00-\x7F]' docs --include='*.md'`) | ✅ 0 matches (fixed post-review — see Addendum) |

## Semantic Evaluation

| Criterion | Verdict | Detail |
|-----------|---------|--------|
| CONTRACT | ✅ | All five files in Architect.md's file list were modified as described; `main.py` matches the three-step design almost verbatim. |
| BEHAVIOUR | ✅ | Every clause in Analyst.md's Behaviour section is implemented and traceable to specific lines in `parse_args()`. |
| EDGE CASES | ✅ | All 12 rows of the Analyst.md edge-case table have a matching test. Two rows (`--prefix /2024 f.txt`, `--prefix //2024/ f.txt`) are exercised via `--list` rather than a literal positional file, which is behaviorally equivalent (normalization runs before the upload/list branch) but not a literal reproduction of the table's exact invocation. |
| TESTS | ✅ | No tautological assertions found; new tests assert real values (`args.prefix`, `capsys` stdout/stderr separation), not just "didn't raise." |
| PATTERNS | ✅ | `main.py:100` (`file=sys.stderr`) is the only stderr-directed write in the module; everything else goes through the stdout-bound `print`/`write` partials, preserving the project's stdout discipline. |
| COVERAGE | ✅ | 100% vs 95% gate, sensor-confirmed. |
| NO EXTRAS | ✅ | No scope creep in `main.py`, `test_main.py`, or `docs/usage.md` beyond what Analyst.md/Architect.md specified. |
| ASCII-ONLY DOCS (spec's own Rules & Constraint + Step 9 gate) | ✅ | Fixed post-review by the user directly — see Addendum. |

## Findings

1. **`docs/usage.md:59`** — non-ASCII `⚠️` in the new "Version notes" blockquote added by Step 6. This is a direct violation of a rule the spec itself states, and would break the pdflatex Read the Docs PDF build (`.readthedocs.yaml` → `formats: all`). Confirmed as the sole match by both the orchestrator's and the evaluator's independent runs of the exact command named in Step 9. Since Step 9 claims this gate was run and passed, either it wasn't run against this exact content or its result was disregarded.

2. **Untested `num_arg_types` asymmetry** (`main.py:97-112`, informational, not a spec violation) — independent re-derivation of the Architect's audit confirms the alias double-count never flips an accept/reject outcome in any constructed case, *except* one untested corner: `--policy --target x --year ''` is silently **accepted** (both `year` and the copied `prefix` are falsy `''`, so they don't count against the policy-exclusivity check), while the equivalent with a non-empty value (`--policy --target x --year 2024`) is correctly **rejected**. This mirrors the pre-existing `--policy --target x --year ''` quirk that Architect.md explicitly says is frozen/non-contractual behavior, so it does not constitute a new defect — but it is untested and worth a note if the coder revisits this area.

3. Minor editorial nit (not part of the rubric): `docs/usage.md:63` has a typo, "inacessible" → "inaccessible". Cosmetic only.

## Addendum — post-review fix

The user manually edited `docs/usage.md:59`, replacing `> ⚠️ **Version notes**:` with
`> **Warning:** Major version breaking changes.` (plain ASCII). Re-ran the full gate
after the edit:

- `grep -rnP '[^\x00-\x7F]' docs --include='*.md'` → no matches (exit 1, clean).
- `uv run pytest` → 151 passed, 100% coverage.
- `uv run ruff check` → all checks passed.
- `uv run ruff format --check` → 10 files already formatted.

All 8 criteria now pass. No further action needed.

## Verdict

- [x] **PASS** — all criteria ✅ (after post-review fix), ready to archive.
- [ ] **PARTIAL PASS**
- [ ] **FAIL**
