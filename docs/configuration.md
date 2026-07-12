# Configuration

The first time you invoke the tool, it will create a default configuration file and exit with a message telling you to edit the file. The file is created at the user config directory reported by `platformdirs` for the application name `sobe`.

## Location

Typically the path looks like:

* Linux: `~/.config/sobe/config.toml`
* macOS: `~/Library/Application Support/sobe/config.toml`
* Windows: `%APPDATA%\sobe\config.toml`

## Template

Here's the default configuration template:

```toml
# sobe configuration

# Target used when --target is not given.
default = "main"

[target.main]
url = "https://example.com/"

[target.main.storage]
type = "aws_s3"
bucket = "example-bucket"

# Optional: remove this table if the target has no CDN in front of it.
[target.main.cache]
type = "aws_cloudfront"
distribution = "E1111111111111"

[target.main.aws_session]
# If you already have AWS CLI set up, don't fill keys here.
# region_name = "..."
# profile_name = "..."
# aws_access_key_id = "..."
# aws_secret_access_key = "..."

[target.main.aws_service]
# verify = true
```

## Targets

A config file defines one or more named **targets** -- independent upload profiles, each with its own storage, optional public URL, optional cache, and its own AWS credentials. One invocation always acts on exactly one target, selected with `-t`/`--target` or via the `default` key.

Each target is a `[target.<name>]` table. Target names may contain letters, digits, underscores, and hyphens, and must not start with a hyphen (regex: `^[A-Za-z0-9_][A-Za-z0-9_-]*$`). Dots are not allowed -- in TOML, a dotted name would collide with the target's sub-tables.

```toml
default = "site"

[target.site]
url = "https://example.com/"
[target.site.storage]
type = "aws_s3"
bucket = "my-site-bucket"
[target.site.cache]
type = "aws_cloudfront"
distribution = "E1111111111111"

[target.scratch]
[target.scratch.storage]
type = "aws_s3"
bucket = "my-scratch-bucket"
```

Two targets may point at the same bucket, and different targets may use entirely different AWS accounts (each has its own `aws_session`).

### Which target is used

1. `--target NAME` on the command line always wins.
2. Otherwise, the target named by the top-level `default` key is used.
3. Otherwise, if exactly one target is defined, it is used.
4. Otherwise (multiple targets, no default), the tool exits with an error listing the defined names.

## Keys

Only the `storage` table is required per target. The `url` and `cache` keys are both optional and independent of each other.

* `default` (top level, optional): Name of the target used when `--target` is not given.
* `target.<name>.url` (optional): The public base URL for the target's uploads. A missing trailing slash is added automatically. When a target has no `url`, output lines show the bucket name in its place (for example `my-bucket/2025/file.txt`).
* `target.<name>.storage` (required): Where files go.
  * `type`: Storage provider discriminator. `"aws_s3"` is currently the only supported value.
  * `bucket`: The S3 bucket name.
* `target.<name>.cache` (optional): CDN cache in front of the storage. Remove the whole table if there is none; `--invalidate` then prints a notice and skips invalidation.
  * `type`: Cache provider discriminator. `"aws_cloudfront"` is currently the only supported value.
  * `distribution`: Distribution ID used for full-path invalidations.
* `target.<name>.aws_session` (optional): Dictionary of values passed to {class}`boto3.session.Session`.
  * You can put credentials and region here.
  * If you already have AWS CLI config set up with these settings, you can leave this empty.
  * Here's the documentation of all possible parameters: {class}`boto3.session.Session`
* `target.<name>.aws_service` (optional): Dictionary of extra options passed to each client/resource creation.
  * `verify`: Controls SSL/TLS certificate verification. Set to `false` to disable certificate validation (useful for corporate MITM proxies or self-signed certificates, but not recommended for general use). Defaults to `true` (secure).

The `type` discriminators are required so that future non-AWS providers can be added without changing the meaning of existing files. An unsupported value is an error naming the target, the key, and the supported values.

## Unconfigured configs

The config counts as unconfigured while it defines no targets, or while every target's bucket is still the placeholder `example-bucket`. In that state the tool prints the config path and exits so you can edit it. An existing file is never overwritten in this state -- only a missing file causes the template to be written.

## Migration from the old single-target format

Versions of `sobe` before the multi-target format used a single top-level `[aws]` table. When the tool finds such a file with real (non-placeholder) values, it automatically rewrites it once, in place, as a single target named `main` marked as the default:

* The original file is preserved as `config.toml.bak` in the same directory, with the same file permission bits.
* A notice naming both paths is printed, and the requested command then runs normally.
* If `config.toml.bak` already exists, the migration stops with an error instead of overwriting it; move or remove the backup and re-run.
* Values that cannot be represented automatically (non-scalar entries under `session`/`service`) stop the migration before anything is written; migrate that table by hand.

An old-format file still holding only placeholder values is simply replaced with the new template (there is nothing user-authored to preserve). Already-migrated files are never rewritten again.
