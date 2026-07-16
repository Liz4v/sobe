"""Command-line interface entry point: input validation and output to user."""

import argparse
import datetime
import functools
import importlib.metadata
import pathlib
import sys
import warnings

import urllib3.exceptions

from sobe.aws import AWS
from sobe.config import ConfigError, MustEditConfig, load_config

write = functools.partial(print, flush=True, end="")
print = functools.partial(print, flush=True)  # type: ignore
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

TUTORIAL_URL = "https://sobe.readthedocs.io/en/latest/tutorial.html"


def main() -> None:
    args = parse_args()

    try:
        config, migration = load_config()
    except MustEditConfig as err:
        if err.created:
            print("Created config file at the path below. You must edit it before use.")
        else:
            print("The config file at the path below is not configured yet. You must edit it before use.")
        print(err.path)
        print(f"Full setup tutorial: {TUTORIAL_URL}")
        raise SystemExit(1) from err
    except ConfigError as err:
        print(err)
        raise SystemExit(1) from err

    if migration is not None:
        print(f"Migrated config file {migration.path} to the new multi-target format.")
        print(f"The original file was saved to {migration.backup}")

    if args.bare:
        _build_parser().print_help()
        raise SystemExit(0)

    try:
        target = config.select(args.target)
    except ConfigError as err:
        print(err)
        raise SystemExit(1) from err

    aws = AWS(target)

    if args.policy:
        print(aws.generate_needed_permissions())
        return

    base = target.url or f"{target.storage.bucket}/"

    if args.list:
        files = aws.list(args.prefix)
        if not files:
            print(f"No files under {base}{args.prefix}")
            return
        for name in files:
            print(f"{base}{args.prefix}{name}")
        return

    for path in args.paths:
        write(f"{base}{args.prefix}{args.remote_name or path.name} ...")
        if args.delete:
            existed = aws.delete(args.prefix, path.name)
            print("deleted." if existed else "didn't exist.")
        else:
            aws.upload(args.prefix, path, args.remote_name, content_type=args.content_type)
            print("ok.")
    if args.invalidate:
        if target.cache is None:
            print(f'Target "{target.name}" has no cache configured; skipping invalidation.')
        else:
            write("Clearing cache...")
            for _ in aws.invalidate_cache():
                write(".")
            print("complete.")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload files to your AWS drop box.")
    parser.add_argument("--version", action="version", version=f"sobe {get_version()}")
    parser.add_argument("-t", "--target", type=str, help="select the configured target to operate on")
    parser.add_argument("-p", "--prefix", type=str, help="set remote directory (usually a year)")
    parser.add_argument("-y", "--year", type=str, help="deprecated alias for --prefix (removed in 2.0)")
    parser.add_argument("--content-type", type=str, help="override detected MIME type for uploaded files")
    parser.add_argument("-l", "--list", action="store_true", help="list all files in the prefix")
    parser.add_argument("-d", "--delete", action="store_true", help="delete instead of upload")
    parser.add_argument("-i", "--invalidate", action="store_true", help="invalidate CloudFront cache")
    parser.add_argument("--policy", action="store_true", help="generate IAM policy requirements and exit")
    parser.add_argument("-r", "--remote-name", type=str, help="upload a single file with a different remote name")
    parser.add_argument("files", nargs="*", help="Source files.")
    return parser


def parse_args(argv=None) -> argparse.Namespace:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.year is not None:
        if args.prefix is not None:
            parser.error("--prefix and --year cannot be used at the same time")
        print("warning: --year is deprecated, use --prefix; it will be removed in sobe 2.0", file=sys.stderr)
        args.prefix = args.year

    num_arg_types = sum(map(bool, args.__dict__.values()))

    if num_arg_types == 0:
        args.bare = True
        return args
    args.bare = False

    if args.policy:
        if num_arg_types != 1 + bool(args.target):
            parser.error("--policy cannot be used with other arguments (except --target)")
        return args

    if args.target and not (args.files or args.list or args.invalidate):
        parser.error("--target requires an operation: files to upload or delete, --list, --invalidate, or --policy")

    if args.prefix is None:
        args.prefix = str(datetime.date.today().year)
    elif not (args.files or args.list):
        parser.error("--prefix requires files or --list to be specified")
    args.prefix = args.prefix.lstrip("/")
    args.prefix = args.prefix if args.prefix == "" or args.prefix.endswith("/") else f"{args.prefix}/"

    if args.content_type or args.remote_name:
        if args.delete or args.list:
            parser.error("Arguments like --content-type and --remote-name are only valid for uploads")
        if not args.files:
            parser.error("You must specify files to be uploaded")
        elif args.remote_name and len(args.files) > 1:
            parser.error("--remote-name can only be used when uploading a single file")
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


def get_version() -> str:
    """Get the current version of the sobe package."""
    try:
        return importlib.metadata.version("sobe")
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover
        return "unknown"
