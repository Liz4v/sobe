# sobe

[![Documentation Status](https://readthedocs.org/projects/sobe/badge/?version=latest)](https://sobe.readthedocs.io/en/latest/)

A simple command-line tool to upload files to an AWS S3 bucket that is publicly available through a CloudFront distribution. This is the traditional "drop box" use case that existed long before the advent of modern file sharing services.

Full documentation: https://sobe.readthedocs.io/en/latest/

It will upload any files you give it to your bucket, defaulting to a current year directory, because that's the only easy way to organize chaos.

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

On first run, `sobe` will create its config file as appropriate to the platform and tell you its location. You'll need to edit this file with your AWS bucket and CloudFront details.

Here's a minimal set up.

```toml
url = "https://example.com/"
[aws]
bucket = "your-bucket-name"
cloudfront = "your-cloudfront-distribution-id"
```

[More information in the docs.](https://sobe.readthedocs.io/en/latest/configuration.html)

## Usage

The basic example is uploading files to current year directory:
```bash
$ sobe file1.jpg file2.pdf
https://example.com/2025/file1.jpg ...ok.
https://example.com/2025/file2.pdf ...ok.
```

You can call it with `--help` for all available options. You can list files, delete them, clear the CloudFront cache (cached objects stay for 1 day by default), select a different upload directory. [The documentation contains better examples.](https://sobe.readthedocs.io/en/latest/usage.html#command-line-interface)

## License

See the [LICENSE](LICENSE) file for details.
