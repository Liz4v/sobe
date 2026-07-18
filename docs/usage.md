# Usage

## Installation

For a full walkthrough including AWS account, bucket, and CloudFront setup, see the [Tutorial](tutorial.md).

Use [uv](https://docs.astral.sh/uv/) to manage it:

```console
$ uv tool install sobe
```

If you have Python >= 3.11, you can also install it via pip:

```console
$ pip install sobe
```

Run it once to create a default configuration file:

```console
$ sobe
Created config file at the path below. You must edit it before use.
/home/user/.config/sobe/config.toml
Full setup tutorial: https://sobe.readthedocs.io/en/latest/tutorial.html
```

Edit the configuration file as described in the [Configuration](configuration.md) section, then re-run the command. (If the file already exists but is still unconfigured, the message says so instead of claiming it was created.)

## Command-line Interface

Show CLI help:

```console
$ sobe --help
```

Basic upload of files for the current year:

```console
$ sobe file1.txt image.png
https://example.com/2025/file1.txt ...ok.
https://example.com/2025/image.png ...ok.
```

Specify a different remote directory prefix (the flag is usually used for a year, but the value can be anything). Some examples:

```console
$ sobe --prefix 2024 file1.txt
https://example.com/2024/file1.txt ...ok.

$ sobe --prefix f/g/h i.jpg
https://example.com/f/g/h/i.jpg ...ok.

$ sobe --prefix 2020/05/15 i-dislike-wordpress.html
https://example.com/2020/05/15/i-dislike-wordpress.html ...ok.

$ sobe --prefix / index.html
https://example.com/index.html ...ok.
```

> **Warning:** Major version breaking changes.
>
> In sobe 0.x:
> * `-p` used to mean `--policy`, but in 1.x it means `--prefix`
> * Leading slashes were not removed back then. S3 keys like `/2024/file1.txt` are "valid", but only partly functional. The correct key in that example is `2024/file1.txt`. Those objects are now inacessible by sobe, but you can still remove them directly.
>
> In sobe 1.x:
> * `-y`/`--year` are deprecated aliases for `-p`/`--prefix`, to be removed in 2.0.

Upload to a specific target when the config defines more than one (see [Configuration](configuration.md) for defining targets). Without `-t`/`--target`, the config's `default` target is used:

```console
$ sobe --target scratch file1.txt
https://scratch.example.com/2025/file1.txt ...ok.

$ sobe -t scratch --list
https://scratch.example.com/2025/file1.txt
```

When the selected target defines no public URL, output shows the bucket name in its place:

```console
$ sobe -t backups file1.txt
my-backup-bucket/2025/file1.txt ...ok.
```

Override the detected MIME type for a file (force a specific `Content-Type` header). Note that `--content-type` is long-only: `-t` selects a target. A leftover `sobe -t image/png ...` habit fails loudly, because `/` is not valid in a target name:

```console
$ sobe --content-type application/x-custom data.bin
https://example.com/2025/data.bin ...ok.
```

Upload a file using a different remote object name (rename on upload). This only works when uploading exactly one file:

```console
$ sobe --remote-name index.html local-dev-index.tmp
https://example.com/2025/index.html ...ok.
```

Example with `--prefix` for placement under another prefix:

```console
$ sobe --prefix 2024 --remote-name avatar.png profile-picture-latest.png
https://example.com/2024/avatar.png ...ok.
```

Delete files instead of uploading:

```console
$ sobe --delete file1.txt
https://example.com/2025/file1.txt ...deleted.
https://example.com/2025/does_not_exist.txt ...didn't exist.
```

Invalidate the target's CloudFront cache:

```console
$ sobe --invalidate
Clearing cache......complete.
```

If the selected target has no cache configured, the rest of the command still runs; the invalidation is skipped with a notice and the exit code stays 0:

```console
$ sobe --invalidate file1.txt
my-backup-bucket/2025/file1.txt ...ok.
Target "backups" has no cache configured; skipping invalidation.
```

You can invalidate after other operations:

```console
$ sobe --invalidate file1.txt
https://example.com/2025/file1.txt ...ok.
Clearing cache......complete.
```

List files for the current year:

```console
$ sobe --list
https://example.com/2025/file1.txt
https://example.com/2025/image.png
```

List files for a specific directory (same rules as above):

```console
$ sobe --list --prefix 2024
https://example.com/2024/old_upload.txt
https://example.com/2024/q1/

$ sobe --list --prefix 2024/q1
https://example.com/2024/q1/report.pdf

$ sobe --list --prefix /
https://example.com/2024/
https://example.com/2025/
https://example.com/index.html
```

Generate the minimal IAM policy required for this tool. This command is to help setting up AWS IAM permissions for a new user or role that will use `sobe`. The output shows the minimum AWS permissions needed for all operations (upload, delete, list, and cache invalidation) on one target -- the selected (or default) one; `--policy` combines with `--target` but with no other flag. The CloudFront statement is omitted for a target without a cache. The CloudFront resource ARN includes your AWS account ID, looked up via STS; if that lookup fails (for example, no credentials are configured yet), a `*` wildcard is used instead so the JSON is still valid to paste as-is. Copy this JSON and use it when creating or modifying IAM policies in the AWS Console or via AWS CLI:

```console
$ sobe --policy
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::example-bucket",
        "arn:aws:s3:::example-bucket/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudfront:CreateInvalidation",
        "cloudfront:GetInvalidation"
      ],
      "Resource": [
        "arn:aws:cloudfront::*:distribution/E1111111111111"
      ]
    }
  ]
}
```
