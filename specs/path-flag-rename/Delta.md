# Delta: `-p/--path` rename (CLI 1.0 freeze, final item)

> Specification delta — what changes relative to the current system.
> Only exists when this feature modifies existing behaviour.

## ADDED

- `-p <value>` / `--path <value>`: new primary flag for the remote directory,
  semantics identical to the current `--year`.
- Runtime deprecation warning: using `-y`/`--year` emits one line on stderr
  naming `--path` as the replacement and 2.0 as the removal version.
- Conflict rule: passing both `--path` and `--year` in one invocation is a
  parser error (exit 2). (Previously impossible — only one flag existed.)
- Docs note in `docs/usage.md` that `--year` is a deprecated alias removed
  in 2.0.
- Leading-slash normalization: all leading slashes are stripped from the
  remote-directory value, so `--path /` (recommended docs spelling) and
  `--path //` mean the bucket root, and `--path /2024` means `2024/`.

## MODIFIED

- **`-y/--year` is the documented remote-directory flag** → **`-p/--path` is
  the documented flag; `-y/--year` become deprecated but functional aliases
  through 1.x, shown in `--help` marked deprecated.**
- **`--help` and `parse_args()` error messages name `--year`** (e.g.
  `--year requires files or --list to be specified`) → **they name `--path`.**
- **`docs/usage.md` examples use `--year`, with `--year ''` shown for root
  uploads** → **examples use `--path`, with `--path /` as the recommended
  root spelling.**
- **A leading slash in the value produces literal leading-slash S3 keys**
  (`-y /2024 f.txt` uploads to key `/2024/f.txt`, shown as an empty-named
  folder in the S3 console, URL `https://example.com//2024/f.txt`) →
  **leading slashes are stripped; such keys are no longer representable.**
- **`specs/1.0-release.md` item 3 / open question 1: decision recorded but
  unimplemented** → **annotated as implemented via this spec, including the
  newly settled 2.0 removal timeline.**

## REMOVED

- **`-p` as the short option for `--policy`** — `--policy` becomes long-only.
  A 0.x `sobe -p` now fails loudly (`expected one argument`) rather than
  printing the IAM policy.
