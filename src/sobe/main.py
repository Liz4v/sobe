"""Command-line interface entry point: input validation and output to user."""

import argparse
import datetime
import functools
import pathlib
import warnings

import urllib3.exceptions

from sobe.aws import AWS
from sobe.config import MustEditConfig, load_config

write = functools.partial(print, flush=True, end="")
print = functools.partial(print, flush=True)  # type: ignore
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)


def main() -> None:
    args = parse_args()
    try:
        config = load_config()
    except MustEditConfig as err:
        print("Created config file at the path below. You must edit it before use.")
        print(err.path)
        raise SystemExit(1) from err

    aws = AWS(config.aws)

    if args.policy:
        print(aws.generate_needed_permissions())
        return

    for path in args.paths:
        write(f"{config.url}{args.year}/{path.name} ...")
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


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload files to your AWS drop box.")
    parser.add_argument("-y", "--year", type=str, help="change year directory")
    parser.add_argument("-i", "--invalidate", action="store_true", help="invalidate CloudFront cache")
    parser.add_argument("-d", "--delete", action="store_true", help="delete instead of upload")
    parser.add_argument("-p", "--policy", action="store_true", help="generate IAM policy requirements and exit")
    parser.add_argument("files", nargs="*", help="Source files.")
    args = parser.parse_args(argv)

    if args.policy:
        if args.year or args.delete or args.invalidate or args.files:
            parser.error("--policy cannot be used with other arguments")
        return args

    if args.year is None:
        args.year = datetime.date.today().year
    elif not args.files:
        parser.error("--year requires files to be specified")

    if args.delete and not args.files:
        parser.error("--delete requires files to be specified")

    if not args.files and not args.invalidate:
        parser.print_help()
        raise SystemExit(0)

    args.paths = [pathlib.Path(p) for p in args.files]
    if not args.delete:
        missing = [p for p in args.paths if not p.exists()]
        if missing:
            print("The following files do not exist:")
            for p in missing:
                print(f"  {p}")
            raise SystemExit(1)

    return args
