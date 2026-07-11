# Usage

## Installation

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
```

Edit the configuration file as described in the [Configuration](configuration.md) section, then re-run the command.

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

Specify a different directory ("year") value. It can be anything. Some examples:

```console
$ sobe --year 2024 file1.txt
https://example.com/2024/file1.txt ...ok.

$ sobe --year f/g/h i.jpg
https://example.com/f/g/h/i.jpg ...ok.

$ sobe --year 2020/05/15 we-hate-wordpress.html
https://example.com/2020/05/15/we-hate-wordpress.html ...ok.

$ sobe --year '' index.html
https://example.com/index.html ...ok.
```

Override the detected MIME type for a file (force a specific `Content-Type` header):

```console
$ sobe --content-type application/x-custom data.bin
https://example.com/2025/data.bin ...ok.
```

Upload a file using a different remote object name (rename on upload). This only works when uploading exactly one file:

```console
$ sobe --remote-name index.html local-dev-index.tmp
https://example.com/2025/index.html ...ok.
```

Example with `--year` for placement under another prefix:

```console
$ sobe --year 2024 --remote-name avatar.png profile-picture-latest.png
https://example.com/2024/avatar.png ...ok.
```

Delete files instead of uploading:

```console
$ sobe --delete file1.txt
https://example.com/2025/file1.txt ...deleted.
https://example.com/2025/does_not_exist.txt ...didn't exist.
```

Invalidate CloudFront cache:

```console
$ sobe --invalidate
Clearing cache......complete.
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
$ sobe --list --year 2024
https://example.com/2024/old_upload.txt
https://example.com/2024/q1/

$ sobe --list --year 2024/q1
https://example.com/2024/q1/report.pdf

$ sobe --list --year ''
https://example.com/2024/
https://example.com/2025/
https://example.com/index.html
```

Generate the minimal IAM policy required for this tool. This command is to help setting up AWS IAM permissions for a new user or role that will use `sobe`. The output shows the minimum AWS permissions needed for all operations (upload, delete, list, and cache invalidation). Copy this JSON and use it when creating or modifying IAM policies in the AWS Console or via AWS CLI:

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
        "s3:DeleteObject",
        "cloudfront:CreateInvalidation",
        "cloudfront:GetInvalidation"
      ],
      "Resource": [
        "arn:aws:s3:::example-bucket",
        "arn:aws:s3:::example-bucket/*",
        "arn:aws:cloudfront::YOUR_ACCOUNT_ID:distribution/E1111111111111"
      ]
    }
  ]
}
```
