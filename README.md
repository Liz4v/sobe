# sobe

A simple command-line tool for uploading files to an AWS S3 bucket that is publicly available through a CloudFront distribution. This is the traditional "drop box" use case that existed long before the advent of modern file sharing services.

It will upload any files you give it to your bucket, in a current year subdirectory, because that's the only easy way to organize chaos.

## Installation

Use [uv](https://docs.astral.sh/uv/) to manage it.

```bash
uv tool install https://github.com/Liz4v/sobe.git
```

## Configuration

On first run, `sobe` will create its config file as appropriate to the platform. You'll need to edit this file with your AWS bucket and CloudFront details:

```toml
# sobe configuration
bucket = "your-bucket-name"
url = "https://your-public-url/"
cloudfront = "your-cloudfront-distribution-id"

[aws_session]
# If you already have AWS CLI set up, don't fill keys here.
# region_name = "..."
# profile_name = "..."
# aws_access_key_id = "..."
# aws_secret_access_key = "..."

[aws_client]
verify = true
```

## Usage

```bash
sobe [options] files...
```

### Options

- `-y`, `--year`: Change the target year directory (default: current year)
- `-i`, `--invalidate`: Invalidate CloudFront cache after upload
- `-d`, `--delete`: Delete files instead of uploading
- `-p`, `--policy`: Display required AWS IAM policy and exit

### Examples

Upload files to current year directory:
```bash
sobe file1.jpg file2.pdf
```

Upload files to a specific year:
```bash
sobe -y 2024 file1.jpg file2.pdf
```

Upload and invalidate CloudFront cache:
```bash
sobe -i file1.jpg
```

Delete files:
```bash
sobe -d file1.jpg
```

Get required AWS IAM policy:
```bash
sobe --policy
```

## AWS Permissions

Use `sobe --policy` to generate the exact IAM policy required for your configuration. The tool needs permissions for:
- S3: PutObject, GetObject, ListBucket, DeleteObject
- CloudFront: CreateInvalidation, GetInvalidation

## License

See the [LICENSE](LICENSE) file for details.
