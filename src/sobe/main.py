import argparse
import datetime
import functools
import json
import mimetypes
import pathlib
import sys
import time
import warnings

import boto3
import botocore.exceptions
import urllib3.exceptions

from .config import CONFIG

write = functools.partial(print, flush=True, end="")
print = functools.partial(print, flush=True)  # type: ignore
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)


def main() -> None:
    args = parse_args()
    session = boto3.Session(**CONFIG.aws.session)
    s3 = session.resource("s3", **CONFIG.aws.service)
    bucket = s3.Bucket(CONFIG.aws.bucket)  # type: ignore
    for path, key in zip(args.paths, args.keys):
        if args.delete:
            delete(bucket, key)
        else:
            upload(bucket, path, key)
    if args.invalidate:
        invalidate(session)


def upload(bucket, path: pathlib.Path, remote_path: str) -> None:
    write(f"{CONFIG.url}{remote_path} ...")
    type_guess, _ = mimetypes.guess_type(path)
    extra_args = {"ContentType": type_guess or "application/octet-stream"}
    bucket.upload_file(str(path), remote_path, ExtraArgs=extra_args)
    print("ok.")


def delete(bucket, remote_path: str) -> None:
    write(f"{CONFIG.url}{remote_path} ...")
    obj = bucket.Object(remote_path)
    try:
        obj.load()
        obj.delete()
        print("deleted.")
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] != "404":
            raise
        print("didn't exist.")


def invalidate(session: boto3.Session) -> None:
    write("Clearing cache ...")
    ref = datetime.datetime.now().astimezone().isoformat()
    cloudfront = session.client("cloudfront", **CONFIG.aws.service)
    batch = {"Paths": {"Quantity": 1, "Items": ["/*"]}, "CallerReference": ref}
    invalidation = cloudfront.create_invalidation(DistributionId=CONFIG.aws.cloudfront, InvalidationBatch=batch)
    write("ok.")
    invalidation_id = invalidation["Invalidation"]["Id"]
    status = ""
    while status != "Completed":
        time.sleep(3)
        write(".")
        response = cloudfront.get_invalidation(DistributionId=CONFIG.aws.cloudfront, Id=invalidation_id)
        status = response["Invalidation"]["Status"]
    print("complete.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload files to your AWS drop box.")
    parser.add_argument("-y", "--year", type=int, default=datetime.date.today().year, help="change year directory")
    parser.add_argument("-i", "--invalidate", action="store_true", help="invalidate CloudFront cache")
    parser.add_argument("-d", "--delete", action="store_true", help="delete instead of upload")
    parser.add_argument("--policy", action="store_true", help="generate IAM policy requirements and exit")
    parser.add_argument("files", nargs="*", help="Source files.")
    args = parser.parse_args()

    if args.policy:
        dump_policy()
        sys.exit(0)

    if not args.files and not args.invalidate:
        parser.print_help()
        sys.exit(0)

    args.paths = [pathlib.Path(p) for p in args.files]
    args.keys = [f"{args.year}/{p.name}" for p in args.paths]
    if not args.delete:
        missing = [p for p in args.paths if not p.exists()]
        if missing:
            print("The following files do not exist:")
            for p in missing:
                print(f"  {p}")
            sys.exit(1)

    return args


def dump_policy() -> None:
    try:
        session = boto3.Session(**CONFIG.aws.session)
        sts = session.client("sts", **CONFIG.aws.service)
        account_id = sts.get_caller_identity()["Account"]
    except botocore.exceptions.ClientError:
        account_id = "YOUR_ACCOUNT_ID"
    actions = """
        s3:PutObject s3:GetObject s3:ListBucket s3:DeleteObject
        cloudfront:CreateInvalidation cloudfront:GetInvalidation
    """.split()
    resources = [
        f"arn:aws:s3:::{CONFIG.aws.bucket}",
        f"arn:aws:s3:::{CONFIG.aws.bucket}/*",
        f"arn:aws:cloudfront::{account_id}:distribution/{CONFIG.aws.cloudfront}",
    ]
    statement = {"Effect": "Allow", "Action": actions, "Resource": resources}
    policy = {"Version": "2012-10-17", "Statement": [statement]}
    print(json.dumps(policy, indent=2))
