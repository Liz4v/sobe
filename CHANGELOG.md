# Changelog

All notable changes to sobe are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0rc1] - 2026-07-18

### Changed

- **Breaking:** `-p` now means `--prefix`, not `--policy`. The remote-directory
  flag (formerly `-y`/`--year`) is promoted to `-p`/`--prefix`; `--policy` is
  long-only now.
- **Breaking:** `-t` now means `--target`, not `--content-type`. `-t` selects a
  configured target; `--content-type` is long-only now.
- **Breaking:** new multi-target config schema with named `[target.<name>]`
  tables (each with `storage`, optional `url`/`cache`, and per-target
  `aws_session`/`aws_service` sections) plus a top-level `default` key.
  Existing single-`[aws]`-table files are migrated automatically in place,
  with the original saved to `config.toml.bak`.
- **Breaking:** leading slashes in the prefix are stripped: `--prefix /2024`
  now means the `2024/` directory and `--prefix /` means the bucket root.
  Previously a leading slash produced a literal `/`-prefixed S3 key.
- **Breaking:** `--list --invalidate` is now rejected as a usage error.
  Previously the combination was accepted and the invalidation silently
  skipped.
- `sobe --help` and `sobe --version` answer immediately on a fresh machine
  without creating a config file; first-run messages link to the new
  [onboarding tutorial](https://sobe.readthedocs.io/en/latest/tutorial.html).
- Documentation converted to Markdown (MyST) and expanded.

### Added

- Multiple targets: define several buckets/distributions in one config, pick
  one with `-t`/`--target`, and set a `default`. A target without a `cache`
  section skips CloudFront invalidation with a notice.
- CI test matrix on Python 3.11-3.14, ruff lint/format checks, and type
  checking with [ty](https://docs.astral.sh/ty/).

### Deprecated

- `-y`/`--year` are deprecated aliases for `-p`/`--prefix`; they print a
  warning on stderr and will be removed in 2.0.

### Fixed

- `--policy` no longer errors when the STS account lookup fails (for example
  with no credentials configured); the generated IAM policy falls back to a
  wildcard account ID.

## [0.4.1] - 2025-11-10

### Fixed

- Upload progress message.

## [0.4.0] - 2025-11-09

### Added

- `-r`/`--remote-name` to upload a single file under a different remote name.
- `--version`.

## [0.3.0] - 2025-11-07

### Added

- `-l`/`--list` to list files in the remote directory.
- `--content-type` to override the detected MIME type.
- Last-resort content-type detection via puremagic.
- The year flag accepts arbitrary directory names, not just years.

### Fixed

- Inconsistent S3 directory handling.

## [0.2.1] - 2025-10-18

### Added

- Sphinx documentation hosted on Read the Docs.
- Unit tests and stricter CLI flag validation.

### Fixed

- Documentation/behavior inconsistencies.

## [0.2] - 2025-10-10

First PyPI release: file uploads with `--delete`, `--invalidate`, and
`--policy`, configured via a TOML file.

[1.0.0rc1]: https://github.com/Liz4v/sobe/compare/0.4.1...1.0.0rc1
[0.4.1]: https://github.com/Liz4v/sobe/compare/0.4.0...0.4.1
[0.4.0]: https://github.com/Liz4v/sobe/compare/0.3.0...0.4.0
[0.3.0]: https://github.com/Liz4v/sobe/compare/0.2.1...0.3.0
[0.2.1]: https://github.com/Liz4v/sobe/compare/0.2...0.2.1
[0.2]: https://github.com/Liz4v/sobe/releases/tag/0.2
