Usage
=====

Installation
------------

Use uv_ to manage it::

  $ uv tool install sobe

If you have Python ≥ 3.11, you can also install it via pip::

  $ pip install sobe

Run it once to create a default configuration file::

  $ sobe
  Created config file at the path below. You must edit it before use.
  /home/username/.config/sobe/config.toml

Edit the configuration file as described in the Configuration_ section, then re-run the command.

Command-line Interface
----------------------

Show CLI help::

  $ sobe --help

Basic upload of files for the current year::

  $ sobe file1.txt image.png
  https://example.com/2025/file1.txt ...ok.
  https://example.com/2025/image.png ...ok.

Specify a different directory ("year") value. It can be anything. Some examples::

  $ sobe --year 2024 file1.txt
  https://example.com/2024/file1.txt ...ok.

  $ sobe --year f/g/h i.jpg
  https://example.com/f/g/h/i.jpg ...ok.

  $ sobe --year 2020/05/15 we-hate-wordpress.html
  https://example.com/2020/05/15/we-hate-wordpress.html ...ok.

  $ sobe --year '' index.html
  https://example.com/index.html ...ok.

Override the detected MIME type for a file (force a specific ``Content-Type`` header)::

  $ sobe --content-type application/x-custom data.bin
  https://example.com/2025/data.bin ...ok.

Delete files instead of uploading::

  $ sobe --delete file1.txt
  https://example.com/2025/file1.txt ...deleted.
  https://example.com/2025/does_not_exist.txt ...didn't exist.

Invalidate CloudFront cache::

  $ sobe --invalidate
  Clearing cache......complete.

You can invalidate after other operations::

  $ sobe --invalidate file1.txt
  https://example.com/2025/file1.txt ...ok.
  Clearing cache......complete.

List files for the current year::

  $ sobe --list
  https://example.com/2025/file1.txt
  https://example.com/2025/image.png

List files for a specific directory (same rules as above)::

  $ sobe --list --year 2024
  https://example.com/2024/old_upload.txt
  https://example.com/2024/q1/

  $ sobe --list --year 2024/q1
  https://example.com/2024/q1/report.pdf

  $ sobe --list --year ''
  https://example.com/2024/
  https://example.com/2025/
  https://example.com/index.html

Generate the minimal IAM policy required for this tool::

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

.. _uv: https://docs.astral.sh/uv/
.. _Configuration: configuration.html
