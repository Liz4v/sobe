# Delta: Multiple Targets

> Specification delta — what changes relative to the current system.
> Only exists when this feature modifies existing behaviour.

## ADDED

- Named targets: the config file can define any number of targets,
  each with its own storage settings and credentials/session settings, plus
  an optional public URL and an optional cache.
- CLI target selection: an additive way to name the target an
  invocation acts on.
- Default target: a config-level marker selecting which target is
  used when none is named; a single defined target acts as the implicit
  default.
- One-time automatic migration of old-schema config files to the new schema
  (single target, marked default), with a backup of the original file
  and a user-facing notice.
- Provider discriminators in the schema (storage type, cache type), with
  S3 and CloudFront as the only accepted providers, so future providers are
  additive.
- Validation errors for: unknown target name, undefined default
  reference, unsupported provider type, invalid target name, zero
  targets defined.

## MODIFIED

- **Config schema is single-site: top-level `url` plus one `[aws]` table with
  `bucket`, `cloudfront`, `[aws.session]`, `[aws.service]`** → **schema is
  multi-target: each target bundles its own URL, storage, optional
  cache, and session/service settings; the old top-level layout is no longer
  the written format.**
- **CloudFront is structurally always present (template always writes a
  distribution ID; `--invalidate` assumes one exists)** → **cache is optional
  per target; `--invalidate` on a cache-less target skips with a
  notice and exits 0.**
- **`--policy` generates one policy covering the single bucket and the single
  CloudFront distribution** → **`--policy` generates the policy for the
  selected/default target only, and omits the CloudFront statement when
  that target has no cache.**
- **All operations implicitly act on the one configured site** → **all
  operations act on exactly one selected (or default) target.**
- **The public URL is effectively required (top-level `url` key, always
  present, prefixes all output)** → **the URL is optional per target;
  when absent, the storage identifier (bucket name) takes the URL's place as
  the output prefix, followed by the remote path.**
- **Unconfigured detection: `aws.bucket` equals the placeholder
  `example-bucket`** → **an equivalent placeholder/unconfigured test defined
  for the new schema (still the trigger for the first-run flow and the
  planned setup wizard).**
- **`load_config()` either returns a config or writes the template and raises
  `MustEditConfig`** → **loading additionally recognises the old schema and
  migrates it (real values) or routes it to the unconfigured flow
  (placeholder values); the written template is in the new schema.**

## REMOVED

- The requirement that every configuration includes a CloudFront
  distribution.
- The old-schema layout as a supported *written* format (it remains readable
  exactly once, as migration input).
