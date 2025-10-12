# sobe

A simple command-line tool for uploading files to an AWS S3 bucket that is publicly available through a CloudFront distribution. This is the traditional "drop box" use case that existed long before the advent of modern file sharing services.

It will upload any files you give it to your bucket, in a current year subdirectory, because that's the only easy way to organize chaos.

"Sobe" is Portuguese for "take it up" (in the imperative), as in "upload".

## Installation

Use [uv](https://docs.astral.sh/uv/) to manage it.

```bash
uv tool install sobe
```

If you have Python ≥ 3.11, you can also install it via pip:

```bash
pip install sobe
```

## Configuration

On first run, `sobe` will create its config file as appropriate to the platform. You'll need to edit this file with your AWS bucket and CloudFront details.

```bash
$ uv run sobe
Created config file at the path below. You must edit it before use.
C:\Users\So-and-so\AppData\Roaming\sobe
```

Here's a minimal set up.

```toml
url = "https://example.com/"
[aws]
bucket = "your-bucket-name"
cloudfront = "your-cloudfront-distribution-id"
```

## Usage

```bash
sobe [-y] [-i] [-d] files...
sobe -i
sobe -p
```

- `-y`, `--year`: Change the target year directory (default: current year)
- `-i`, `--invalidate`: Invalidate CloudFront cache after upload
- `-d`, `--delete`: Delete files instead of uploading
- `-p`, `--policy`: Display required AWS IAM policy and exit

### Examples

Upload files to current year directory:
```bash
$ sobe file1.jpg file2.pdf
https://example.com/2025/file1.jpg ...ok.
https://example.com/2025/file2.pdf ...ok.
```

Upload files to a specific year:
```bash
$ sobe -y 2024 file1.jpg file2.pdf
https://example.com/2024/file1.jpg ...ok.
https://example.com/2024/file2.pdf ...ok.
```

Upload and invalidate CloudFront cache:
```bash
$ sobe -i file3.html
https://example.com/2025/file3.html ...ok.
Clearing cache.........complete.
```

Delete files:
```bash
$ sobe -d file1.jpg file0.gif
https://example.com/2025/file1.jpg ...deleted.
https://example.com/2025/file0.gif ...didn't exist.
```

Get required AWS IAM policy:
```bash
$ sobe -p
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
        "arn:aws:cloudfront::555555555555:distribution/E1111111111111"
      ]
    }
  ]
}
```

## License

See the [LICENSE](LICENSE) file for details.
