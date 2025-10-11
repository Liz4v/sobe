import argparse
import datetime
import functools
import pathlib
import sys
import warnings

import urllib3.exceptions

from .aws import AWS
from .config import CONFIG

write = functools.partial(print, flush=True, end="")
print = functools.partial(print, flush=True)  # type: ignore
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)


def main() -> None:
    args = parse_args()
    aws = AWS(CONFIG.aws)

    for path in args.paths:
        write(f"{CONFIG.url}{args.year}/{path.name} ...")
        if args.delete:
            existed = aws.delete(args.year, path.name)
            print("deleted." if existed else "didn't exist.")
        else:
            aws.upload(args.year, path)
            print("ok.")
    if args.invalidate:
        write("Clearing cache...")
        for _ in aws.invalidate_cache():
            write(".")
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
        aws = AWS(CONFIG.aws)
        print(aws.generate_needed_permissions())
        sys.exit(0)

    if not args.files and not args.invalidate:
        parser.print_help()
        sys.exit(0)

    args.paths = [pathlib.Path(p) for p in args.files]
    if not args.delete:
        missing = [p for p in args.paths if not p.exists()]
        if missing:
            print("The following files do not exist:")
            for p in missing:
                print(f"  {p}")
            sys.exit(1)

    return args
