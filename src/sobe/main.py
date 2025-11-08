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
    try:
        config = load_config()
    except MustEditConfig as err:
        print("Created config file at the path below. You must edit it before use.")
        print(err.path)
        raise SystemExit(1) from err

    args = parse_args()
    aws = AWS(config.aws)

    if args.policy:
        print(aws.generate_needed_permissions())
        return

    if args.list:
        files = aws.list(args.prefix)
        if not files:
            print(f"No files under {config.url}{args.prefix}")
            return
        for name in files:
            print(f"{config.url}{args.prefix}{name}")
        return

    for path in args.paths:
        write(f"{config.url}{args.prefix}{path.name} ...")
        if args.delete:
            existed = aws.delete(args.prefix, path.name)
            print("deleted." if existed else "didn't exist.")
        else:
            aws.upload(args.prefix, path, content_type=args.content_type )
            print("ok.")
    if args.invalidate:
        write("Clearing cache...")
        for _ in aws.invalidate_cache():
            write(".")
        print("complete.")


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload files to your AWS drop box.")
    parser.add_argument("-y", "--year", type=str, help="set remote directory (usually a year)")
    parser.add_argument("-t", "--content-type", type=str, help="override detected MIME type for uploaded files")
    parser.add_argument("-l", "--list", action="store_true", help="list all files in the year")
    parser.add_argument("-d", "--delete", action="store_true", help="delete instead of upload")
    parser.add_argument("-i", "--invalidate", action="store_true", help="invalidate CloudFront cache")
    parser.add_argument("-p", "--policy", action="store_true", help="generate IAM policy requirements and exit")
    parser.add_argument("files", nargs="*", help="Source files.")
    args = parser.parse_args(argv)
    num_arg_types = sum(map(bool, args.__dict__.values()))

    if num_arg_types == 0:
        parser.print_help()
        raise SystemExit(0)

    if args.policy:
        if num_arg_types != 1:
            parser.error("--policy cannot be used with other arguments")
        return args

    if args.year is None:
        args.year = str(datetime.date.today().year)
    elif not (args.files or args.list):
        parser.error("--year requires files or --list to be specified")
    args.prefix = args.year if args.year == "" or args.year.endswith("/") else f"{args.year}/"

    if args.content_type:
        if args.delete or args.list:
            parser.error("--content-type cannot be used with --delete or --list")
        if not args.files:
            parser.error("--content-type requires files to be specified")
    elif args.list:
        if args.delete:
            parser.error("--list and --delete cannot be used at the same time")
        if args.files:
            parser.error("--list does not support file filtering yet")
    elif args.delete:
        if not args.files:
            parser.error("--delete requires files to be specified")

    args.paths = [pathlib.Path(p) for p in args.files]
    if not (args.delete or args.list):
        missing = [p for p in args.paths if not p.exists()]
        if missing:
            print("The following files do not exist:")
            for p in missing:
                print(f"  {p}")
            raise SystemExit(1)

    return args
