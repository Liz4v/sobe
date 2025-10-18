Usage
=====

Installation
------------

Install using uv::

  uv tool install sobe

Or, if you have Python ≥3.11, use pip::

  pip install sobe

Command-line Interface
----------------------

Show CLI help::

  $ sobe --help

Basic upload of files for the current year::

  $ sobe file1.txt image.png
  https://example.com/2025/file1.txt ...ok.
  https://example.com/2025/image.png ...ok.

Specify a different year directory::

  $ sobe --year 2024 file1.txt
  https://example.com/2024/file1.txt ...ok.

Delete files instead of uploading::

  $ sobe --delete file1.txt
  https://example.com/2025/file1.txt ...deleted.
  https://example.com/2025/does_not_exist.txt ...didn't exist.

Invalidate CloudFront cache::

  $ sobe --invalidate
  Clearing cache......complete.

You can invalidate after uploads::

  $ sobe --invalidate file1.txt
  https://example.com/2025/file1.txt ...ok.
  Clearing cache......complete.

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
