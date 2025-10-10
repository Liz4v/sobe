import argparse
import datetime
import functools
import json
import mimetypes
import pathlib
import sys
import time
import tomllib
import warnings

import boto3
import botocore.exceptions
import platformdirs
import urllib3.exceptions


def load_config():
    path = platformdirs.PlatformDirs("sobe", "balbuena.ca").user_config_path / "config.toml"
    if path.exists():
        with path.open("rb") as f:
            payload = tomllib.load(f)
            if payload["bucket"] != "example-bucket":
                return payload

    defaults = """
        # sobe configuration
        bucket = "example-bucket"
        url = "https://example.com/"
        cloudfront = "E1111111111111"

        [aws_session]
        # If you already have AWS CLI set up, don't fill keys here.
        # region_name = "..."
        # profile_name = "..."
        # aws_access_key_id = "..."
        # aws_secret_access_key = "..."

        [aws_client]
        verify = true
    """
    defaults = "\n".join(line.strip() for line in defaults.lstrip().splitlines())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(defaults)
    print("Created config file at the path below. You must edit it before use.")
    print(path)
    sys.exit(1)


CONFIG = load_config()
write = functools.partial(print, flush=True, end="")
print = functools.partial(print, flush=True)  # type: ignore
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)


def main() -> None:
    args = parse_args()
    session = boto3.Session(**CONFIG["aws_session"])
    bucket = session.resource("s3", **CONFIG["aws_client"]).Bucket(CONFIG["bucket"])
    for path, key in zip(args.paths, args.keys):
        if args.delete:
            delete(bucket, key)
        else:
            upload(bucket, path, key)
    if args.invalidate:
        invalidate(session)


def upload(bucket, path: pathlib.Path, remote_path: str) -> None:
    write(f"{CONFIG['url']}{remote_path} ...")
    type_guess, _ = mimetypes.guess_type(path)
    extra_args = {"ContentType": type_guess or "application/octet-stream"}
    bucket.upload_file(str(path), remote_path, ExtraArgs=extra_args)
    print("ok.")


def delete(bucket, remote_path: str) -> None:
    write(f"{CONFIG['url']}{remote_path} ...")
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
    cloudfront = session.client("cloudfront", **CONFIG["aws_client"])
    batch = {"Paths": {"Quantity": 1, "Items": ["/*"]}, "CallerReference": ref}
    invalidation = cloudfront.create_invalidation(DistributionId=CONFIG["cloudfront"], InvalidationBatch=batch)
    write("ok.")
    invalidation_id = invalidation["Invalidation"]["Id"]
    status = ""
    while status != "Completed":
        time.sleep(3)
        write(".")
        response = cloudfront.get_invalidation(DistributionId=CONFIG["cloudfront"], Id=invalidation_id)
        status = response["Invalidation"]["Status"]
    print("complete.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload files to your AWS drop box.")
    parser.add_argument("-y", "--year", type=int, default=datetime.date.today().year, help="change year directory")
    parser.add_argument("-i", "--invalidate", action="store_true", help="invalidate CloudFront cache")
    parser.add_argument("-d", "--delete", action="store_true", help="delete instead of upload")
    parser.add_argument("--policy", action="store_true", help="display IAM policy requirements and exit")
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
    session = boto3.Session(**CONFIG["aws_session"])
    sts = session.client("sts", **CONFIG["aws_client"])
    caller = sts.get_caller_identity()["Arn"]
    account_id = caller.split(":")[4]
    actions = """
        s3:PutObject s3:GetObject s3:ListBucket s3:DeleteObject
        cloudfront:CreateInvalidation cloudfront:GetInvalidation
    """.split()
    resources = [
        f"arn:aws:s3:::{CONFIG['bucket']}",
        f"arn:aws:s3:::{CONFIG['bucket']}/*",
        f"arn:aws:cloudfront::{account_id}:distribution/{CONFIG['cloudfront']}",
    ]
    statement = {"Effect": "Allow", "Action": actions, "Resource": resources}
    policy = {"Version": "2012-10-17", "Statement": [statement]}
    print(json.dumps(policy, indent=2))
