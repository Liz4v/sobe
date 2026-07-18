"""Everything related to user configuration file."""

import os
import re
import stat
import tomllib
from pathlib import Path
from typing import Any, NamedTuple, Self

from platformdirs import PlatformDirs

STORAGE_TYPES = ("aws_s3",)
CACHE_TYPES = ("aws_cloudfront",)
TARGET_NAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_-]*$")
PLACEHOLDER_BUCKET = "example-bucket"


class ConfigError(Exception):
    """Invalid configuration. The message names what is wrong and the user's next step."""


class StorageConfig(NamedTuple):
    type: str
    bucket: str

    @classmethod
    def from_dict(cls, target_name: str, raw: dict[str, Any]) -> Self:
        kind = raw.get("type")
        if kind not in STORAGE_TYPES:
            raise ConfigError(
                f'Target "{target_name}": storage type is {kind!r} but the supported values are: '
                f"{', '.join(STORAGE_TYPES)}. Set type in [target.{target_name}.storage]."
            )
        bucket = raw.get("bucket")
        if not isinstance(bucket, str) or not bucket:
            raise ConfigError(
                f'Target "{target_name}": storage has no bucket. Set bucket in [target.{target_name}.storage].'
            )
        return cls(type=kind, bucket=bucket)


class CacheConfig(NamedTuple):
    type: str
    distribution: str

    @classmethod
    def from_dict(cls, target_name: str, raw: dict[str, Any]) -> Self:
        kind = raw.get("type")
        if kind not in CACHE_TYPES:
            raise ConfigError(
                f'Target "{target_name}": cache type is {kind!r} but the supported values are: '
                f"{', '.join(CACHE_TYPES)}. Set type in [target.{target_name}.cache]."
            )
        distribution = raw.get("distribution")
        if not isinstance(distribution, str) or not distribution:
            raise ConfigError(
                f'Target "{target_name}": cache has no distribution. '
                f"Set distribution in [target.{target_name}.cache] or remove the cache table."
            )
        return cls(type=kind, distribution=distribution)


class Target(NamedTuple):
    name: str
    storage: StorageConfig
    url: str | None
    cache: CacheConfig | None
    aws_session: dict[str, Any]
    aws_service: dict[str, Any]

    @classmethod
    def from_dict(cls, name: str, raw: dict[str, Any]) -> Self:
        if not TARGET_NAME_RE.match(name):
            raise ConfigError(
                f'Invalid target name "{name}": names must start with a letter, digit, or underscore and contain '
                "only letters, digits, underscores, and hyphens (no dots). Rename its [target.*] table."
            )
        if not isinstance(raw, dict):
            raise ConfigError(f'Target "{name}" must be a table: define it as [target.{name}].')
        storage_raw = raw.get("storage")
        if not isinstance(storage_raw, dict):
            raise ConfigError(
                f'Target "{name}" has no storage. Add a [target.{name}.storage] table with type and bucket.'
            )
        storage = StorageConfig.from_dict(name, storage_raw)

        cache_raw = raw.get("cache")
        cache = None
        if cache_raw is not None:
            if not isinstance(cache_raw, dict):
                raise ConfigError(
                    f'Target "{name}": cache must be a table ([target.{name}.cache]) with type and distribution.'
                )
            cache = CacheConfig.from_dict(name, cache_raw)

        url = raw.get("url")
        if url is not None:
            if not isinstance(url, str) or not url:
                raise ConfigError(f'Target "{name}": url must be a non-empty string, or removed entirely.')
            if not url.endswith("/"):
                url += "/"

        aws_session = raw.get("aws_session", {})
        aws_service = raw.get("aws_service", {})
        for key, value in (("aws_session", aws_session), ("aws_service", aws_service)):
            if not isinstance(value, dict):
                raise ConfigError(f'Target "{name}": {key} must be a table ([target.{name}.{key}]).')

        return cls(name=name, storage=storage, url=url, cache=cache, aws_session=aws_session, aws_service=aws_service)


class Config(NamedTuple):
    targets: dict[str, Target]
    default: str | None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Self:
        table = raw.get("target", {})
        if not isinstance(table, dict):
            raise ConfigError('The "target" key must be a table: define each target as [target.<name>].')
        targets = {name: Target.from_dict(name, sub) for name, sub in table.items()}
        default = raw.get("default")
        if default is not None and not isinstance(default, str):
            raise ConfigError('The "default" key must be a string naming one of the defined targets.')
        return cls(targets=targets, default=default)

    def select(self, name: str | None) -> Target:
        """Return the target to operate on, applying the selection rules. An empty name counts as not given."""
        defined = ", ".join(self.targets)
        if name:
            if name not in self.targets:
                raise ConfigError(
                    f'Target "{name}" is not defined in the config. Defined targets: {defined}. '
                    "Pass --target with one of those names."
                )
            return self.targets[name]
        if self.default is not None:
            if self.default not in self.targets:
                raise ConfigError(
                    f'The config sets default = "{self.default}", but that target is not defined. '
                    f"Defined targets: {defined}. Fix the default key in the config."
                )
            return self.targets[self.default]
        if len(self.targets) == 1:
            return next(iter(self.targets.values()))
        raise ConfigError(
            f"Multiple targets are defined ({defined}) and none is marked as default. "
            "Pass --target with one of those names, or set default in the config."
        )

    def is_unconfigured(self) -> bool:
        """Whether the config still needs editing: no targets, or every bucket is the placeholder."""
        return not self.targets or all(t.storage.bucket == PLACEHOLDER_BUCKET for t in self.targets.values())


class Migration(NamedTuple):
    path: Path
    backup: Path


class MustEditConfig(Exception):
    """Config file must be edited before this tool can be used."""

    def __init__(self, path: Path, created: bool = True):
        self.path = path
        self.created = created


DEFAULT_TEMPLATE = """
# sobe configuration

# Target used when --target is not given.
default = "main"

[target.main]
url = "https://example.com/"

[target.main.storage]
type = "aws_s3"
bucket = "example-bucket"

# Optional: remove this table if the target has no CDN in front of it.
[target.main.cache]
type = "aws_cloudfront"
distribution = "E1111111111111"

[target.main.aws_session]
# If you already have AWS CLI set up, don't fill keys here.
# region_name = "..."
# profile_name = "..."
# aws_access_key_id = "..."
# aws_secret_access_key = "..."

[target.main.aws_service]
# verify = true
"""


_BARE_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _toml_string(value: str) -> str:
    """Serialize a TOML basic string, escaping backslashes, quotes, and control characters."""
    out = ['"']
    for ch in value:
        if ch in ('"', "\\"):
            out.append("\\" + ch)
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ord(ch) < 0x20 or ch == "\x7f":
            out.append(f"\\u{ord(ch):04X}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _toml_key(key: str) -> str:
    return key if _BARE_KEY_RE.match(key) else _toml_string(key)


def _toml_scalar(table: str, key: str, value: Any) -> str:
    """Serialize a scalar TOML value; anything non-scalar must be migrated by hand."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return _toml_string(value)
    raise ConfigError(
        f'Cannot migrate the config automatically: key "{key}" in [{table}] has a non-scalar value. '
        "Migrate that table to the new schema by hand."
    )


def _emit_config(config: Config) -> str:
    """Serialize a Config as new-schema TOML. Only used to write migrated config files."""
    lines = ["# sobe configuration", ""]
    if config.default is not None:
        lines += [f"default = {_toml_string(config.default)}", ""]
    for target in config.targets.values():
        prefix = f"target.{target.name}"
        lines.append(f"[{prefix}]")
        if target.url is not None:
            lines.append(f"url = {_toml_string(target.url)}")
        lines += [
            "",
            f"[{prefix}.storage]",
            f"type = {_toml_string(target.storage.type)}",
            f"bucket = {_toml_string(target.storage.bucket)}",
        ]
        if target.cache is not None:
            lines += [
                "",
                f"[{prefix}.cache]",
                f"type = {_toml_string(target.cache.type)}",
                f"distribution = {_toml_string(target.cache.distribution)}",
            ]
        for table_name, table in (("aws_session", target.aws_session), ("aws_service", target.aws_service)):
            if table:
                lines += ["", f"[{prefix}.{table_name}]"]
                for key, value in table.items():
                    lines.append(f"{_toml_key(key)} = {_toml_scalar(f'{prefix}.{table_name}', key, value)}")
        lines.append("")
    return "\n".join(lines)


def _is_old_schema(payload: dict[str, Any]) -> bool:
    """Whether a parsed config file uses the pre-targets schema."""
    return "aws" in payload and "target" not in payload


def _migrate(path: Path, payload: dict[str, Any]) -> tuple[Config, Migration]:
    """Rewrite an old-schema config file in place as a single default target named "main".

    Everything that can fail happens before anything touches the filesystem, so a failed
    migration never leaves a backup behind. The original bytes are kept at
    ``<config>.bak`` with the original permission bits (the file may hold credentials).
    """
    old_aws = payload.get("aws", {})
    raw_target: dict[str, Any] = {
        "url": payload.get("url", "https://example.com/"),
        "storage": {"type": "aws_s3", "bucket": old_aws.get("bucket", PLACEHOLDER_BUCKET)},
        "cache": {"type": "aws_cloudfront", "distribution": old_aws.get("cloudfront", "E1111111111111")},
        "aws_session": old_aws.get("session", {}),
        "aws_service": old_aws.get("service", {}),
    }
    config = Config.from_dict({"default": "main", "target": {"main": raw_target}})
    text = _emit_config(config)

    backup = path.with_name(path.name + ".bak")
    original = path.read_bytes()
    mode = stat.S_IMODE(path.stat().st_mode)
    try:
        fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    except FileExistsError:
        raise ConfigError(
            f"Cannot migrate {path}: the backup path {backup} already exists. "
            "Move or remove that backup file, then run sobe again."
        ) from None
    with os.fdopen(fd, "wb") as f:
        os.fchmod(fd, mode)
        f.write(original)

    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.chmod(tmp, mode)
    os.replace(tmp, path)
    return config, Migration(path=path, backup=backup)


def load_config() -> tuple[Config, Migration | None]:
    path = PlatformDirs("sobe").user_config_path / "config.toml"
    if path.exists():
        with path.open("rb") as f:
            try:
                payload = tomllib.load(f)
            except tomllib.TOMLDecodeError as err:
                raise ConfigError(f"Cannot parse {path}: {err}. Fix the TOML syntax and run sobe again.") from err
        if _is_old_schema(payload):
            if payload.get("aws", {}).get("bucket", PLACEHOLDER_BUCKET) != PLACEHOLDER_BUCKET:
                return _migrate(path, payload)
            # old-schema placeholder: nothing user-authored to lose, replace with the new template
        else:
            config = Config.from_dict(payload)
            if config.is_unconfigured():
                # never rewrite an existing new-schema file, even an unconfigured one
                raise MustEditConfig(path, created=False)
            return config, None

    # create default file and exit for user to customize
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEFAULT_TEMPLATE.lstrip())
    raise MustEditConfig(path, created=True)
