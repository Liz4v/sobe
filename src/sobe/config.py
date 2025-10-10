import tomllib
from typing import Any, NamedTuple, Self

from platformdirs import PlatformDirs


class AWSConfig(NamedTuple):
    bucket: str
    cloudfront: str
    session: dict[str, Any]
    service: dict[str, Any]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Self:
        return cls(
            bucket=raw.get("bucket", "example-bucket"),
            cloudfront=raw.get("cloudfront", "E1111111111111"),
            session=raw.get("session", {}),
            service=raw.get("service", {}),
        )


class Config(NamedTuple):
    url: str
    aws: AWSConfig

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Self:
        return cls(
            url=raw.get("url", "https://example.com/"),
            aws=AWSConfig.from_dict(raw.get("aws", {})),
        )


DEFAULT_TEMPLATE = """
# sobe configuration

url = "https://example.com/"

[aws]
bucket = "example-bucket"
cloudfront = "E1111111111111"

[aws.session]
# If you already have AWS CLI set up, don't fill keys here.
# region_name = "..."
# profile_name = "..."
# aws_access_key_id = "..."
# aws_secret_access_key = "..."

[aws.service]
verify = true
"""


def load_config() -> Config:
    path = PlatformDirs("sobe", "balbuena.ca").user_config_path / "config.toml"
    if path.exists():
        with path.open("rb") as f:
            payload = tomllib.load(f)
            if payload.get("aws", {}).get("bucket", "example-bucket") != "example-bucket":
                return Config.from_dict(payload)

    # create default file and exit for user to customize
    defaults = "\n".join(line.strip() for line in DEFAULT_TEMPLATE.lstrip().splitlines())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(defaults)
    print("Created config file at the path below. You must edit it before use.")
    print(path)
    raise SystemExit(1)


CONFIG: Config = load_config()
