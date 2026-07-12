import tomllib
from unittest.mock import MagicMock, patch

import pytest

from sobe import config


def make_target_dict(**overrides):
    """Raw dict for a fully-populated valid target."""
    raw = {
        "url": "https://test.example.com/",
        "storage": {"type": "aws_s3", "bucket": "test-bucket"},
        "cache": {"type": "aws_cloudfront", "distribution": "E1234567890123"},
        "aws_session": {"region_name": "us-west-2"},
        "aws_service": {"verify": False},
    }
    raw.update(overrides)
    return raw


class TestStorageConfig:
    def test_from_dict_with_all_values(self):
        result = config.StorageConfig.from_dict("main", {"type": "aws_s3", "bucket": "test-bucket"})
        assert result.type == "aws_s3"
        assert result.bucket == "test-bucket"

    def test_missing_bucket_error(self):
        with pytest.raises(config.ConfigError, match="storage has no bucket"):
            config.StorageConfig.from_dict("main", {"type": "aws_s3"})

    def test_bad_type_error_names_target_and_supported_values(self):
        with pytest.raises(config.ConfigError, match=r'Target "main".*\'gcs\'.*aws_s3'):
            config.StorageConfig.from_dict("main", {"type": "gcs", "bucket": "b"})

    def test_missing_type_error(self):
        with pytest.raises(config.ConfigError, match="storage type is None"):
            config.StorageConfig.from_dict("main", {"bucket": "b"})


class TestCacheConfig:
    def test_from_dict_with_all_values(self):
        result = config.CacheConfig.from_dict("main", {"type": "aws_cloudfront", "distribution": "E1234567890123"})
        assert result.type == "aws_cloudfront"
        assert result.distribution == "E1234567890123"

    def test_missing_distribution_error(self):
        with pytest.raises(config.ConfigError, match="cache has no distribution"):
            config.CacheConfig.from_dict("main", {"type": "aws_cloudfront"})

    def test_bad_type_error_names_target_and_supported_values(self):
        with pytest.raises(config.ConfigError, match=r'Target "main".*\'fastly\'.*aws_cloudfront'):
            config.CacheConfig.from_dict("main", {"type": "fastly", "distribution": "E1"})


class TestTarget:
    def test_from_dict_with_all_values(self):
        result = config.Target.from_dict("main", make_target_dict())

        assert result.name == "main"
        assert result.url == "https://test.example.com/"
        assert result.storage == config.StorageConfig(type="aws_s3", bucket="test-bucket")
        assert result.cache == config.CacheConfig(type="aws_cloudfront", distribution="E1234567890123")
        assert result.aws_session == {"region_name": "us-west-2"}
        assert result.aws_service == {"verify": False}

    def test_from_dict_with_defaults(self):
        """Only storage is required; url, cache, and the aws_* tables are optional."""
        result = config.Target.from_dict("main", {"storage": {"type": "aws_s3", "bucket": "b"}})

        assert result.url is None
        assert result.cache is None
        assert result.aws_session == {}
        assert result.aws_service == {}

    def test_url_trailing_slash_normalization(self):
        result = config.Target.from_dict("main", make_target_dict(url="https://test.example.com"))
        assert result.url == "https://test.example.com/"

    def test_url_without_cache_and_cache_without_url_are_independent(self):
        raw = make_target_dict()
        del raw["cache"]
        with_url = config.Target.from_dict("main", raw)
        assert with_url.url is not None and with_url.cache is None

        raw = make_target_dict()
        del raw["url"]
        with_cache = config.Target.from_dict("main", raw)
        assert with_cache.url is None and with_cache.cache is not None

    def test_missing_storage_error(self):
        with pytest.raises(config.ConfigError, match=r'Target "main" has no storage'):
            config.Target.from_dict("main", {"url": "https://x.example/"})

    def test_empty_url_error(self):
        with pytest.raises(config.ConfigError, match="url must be a non-empty string"):
            config.Target.from_dict("main", make_target_dict(url=""))

    def test_non_table_aws_session_error(self):
        with pytest.raises(config.ConfigError, match="aws_session must be a table"):
            config.Target.from_dict("main", make_target_dict(aws_session="oops"))

    @pytest.mark.parametrize("name", ["with.dot", "with space", "with/slash", "", "-leadinghyphen", "ünïcode"])
    def test_bad_name_error(self, name):
        with pytest.raises(config.ConfigError, match="Invalid target name"):
            config.Target.from_dict(name, make_target_dict())

    @pytest.mark.parametrize("name", ["main", "MAIN-2", "_x", "0day", "a-b_c"])
    def test_good_names_accepted(self, name):
        assert config.Target.from_dict(name, make_target_dict()).name == name


class TestConfigFromDict:
    def test_from_dict_with_all_values(self):
        raw = {"default": "a", "target": {"a": make_target_dict(), "b": make_target_dict()}}
        result = config.Config.from_dict(raw)

        assert set(result.targets) == {"a", "b"}
        assert result.default == "a"
        assert result.targets["a"].name == "a"

    def test_from_dict_with_defaults(self):
        result = config.Config.from_dict({})
        assert result.targets == {}
        assert result.default is None

    def test_non_table_target_key_error(self):
        with pytest.raises(config.ConfigError, match='"target" key must be a table'):
            config.Config.from_dict({"target": "oops"})

    def test_non_string_default_error(self):
        with pytest.raises(config.ConfigError, match='"default" key must be a string'):
            config.Config.from_dict({"default": 3})

    def test_same_bucket_in_two_targets_allowed(self):
        raw = {"target": {"a": make_target_dict(), "b": make_target_dict()}}
        result = config.Config.from_dict(raw)
        assert result.targets["a"].storage.bucket == result.targets["b"].storage.bucket


class TestConfigSelect:
    def make_config(self, *names: str, default: str | None = None) -> config.Config:
        raw = {"target": {name: make_target_dict() for name in names}}
        if default is not None:
            raw["default"] = default
        return config.Config.from_dict(raw)

    def test_named_target(self):
        cfg = self.make_config("a", "b")
        assert cfg.select("b").name == "b"

    def test_named_target_wins_over_default(self):
        cfg = self.make_config("a", "b", default="a")
        assert cfg.select("b").name == "b"

    def test_unknown_name_error_lists_defined(self):
        cfg = self.make_config("a", "b")
        with pytest.raises(config.ConfigError, match=r'"nope" is not defined.*a, b'):
            cfg.select("nope")

    def test_default_marker_used_when_no_name(self):
        cfg = self.make_config("a", "b", default="b")
        assert cfg.select(None).name == "b"

    def test_empty_name_treated_as_not_given(self):
        cfg = self.make_config("a", "b", default="b")
        assert cfg.select("").name == "b"

    def test_bad_default_error_lists_defined(self):
        cfg = self.make_config("a", "b", default="nope")
        with pytest.raises(config.ConfigError, match=r'default = "nope".*a, b'):
            cfg.select(None)

    def test_single_target_is_implicit_default(self):
        cfg = self.make_config("only")
        assert cfg.select(None).name == "only"

    def test_multiple_targets_without_default_error_lists_names(self):
        cfg = self.make_config("a", "b")
        with pytest.raises(config.ConfigError, match=r"a, b.*--target"):
            cfg.select(None)


class TestTomlEmitter:
    def test_non_scalar_session_value_names_key_but_not_value(self):
        target = config.Target.from_dict("main", make_target_dict(aws_session={"secret_thing": ["s3cr3t"]}))
        cfg = config.Config(targets={"main": target}, default="main")

        with pytest.raises(config.ConfigError, match="secret_thing") as excinfo:
            config._emit_config(cfg)
        assert "s3cr3t" not in str(excinfo.value)
        assert "by hand" in str(excinfo.value)

    def test_escaping_round_trips_through_tomllib(self):
        nasty = 'quo"te back\\slash tab\tnewline\ncontrol\x01/'
        target = config.Target(
            name="main",
            storage=config.StorageConfig(type="aws_s3", bucket=nasty),
            url=None,
            cache=None,
            aws_session={"weird key!": nasty},
            aws_service={"verify": True, "count": 3, "ratio": 1.5},
        )
        cfg = config.Config(targets={"main": target}, default="main")

        parsed = tomllib.loads(config._emit_config(cfg))

        assert parsed["default"] == "main"
        assert parsed["target"]["main"]["storage"]["bucket"] == nasty
        assert parsed["target"]["main"]["aws_session"]["weird key!"] == nasty
        assert parsed["target"]["main"]["aws_service"] == {"verify": True, "count": 3, "ratio": 1.5}


OLD_SCHEMA_REAL = """
url = "https://drops.example.org"

[aws]
bucket = "real-bucket"
cloudfront = "E22222"

[aws.session]
profile_name = "work"

[aws.service]
verify = true
"""

OLD_SCHEMA_PLACEHOLDER = """
url = "https://example.com/"

[aws]
bucket = "example-bucket"
cloudfront = "E1111111111111"
"""


class TestLoadConfig:
    @pytest.fixture(autouse=True)
    def config_dir(self, tmp_path):
        mock_pd = MagicMock(name="PlatformDirs")
        mock_pd.return_value.user_config_path = tmp_path
        with patch("sobe.config.PlatformDirs", mock_pd):
            self.dir = tmp_path
            self.path = tmp_path / "config.toml"
            yield

    def test_new_schema_load(self):
        self.path.write_text(config.DEFAULT_TEMPLATE.replace("example-bucket", "real-bucket"))

        cfg, migration = config.load_config()

        assert migration is None
        assert cfg.select(None).storage.bucket == "real-bucket"

    def test_missing_file_creates_template(self):
        with pytest.raises(config.MustEditConfig) as excinfo:
            config.load_config()

        assert excinfo.value.created is True
        assert excinfo.value.path == self.path
        assert self.path.read_text() == config.DEFAULT_TEMPLATE.lstrip()

    def test_old_schema_placeholder_rewritten_without_backup(self):
        self.path.write_text(OLD_SCHEMA_PLACEHOLDER)

        with pytest.raises(config.MustEditConfig) as excinfo:
            config.load_config()

        assert excinfo.value.created is True
        assert self.path.read_text() == config.DEFAULT_TEMPLATE.lstrip()
        assert not (self.dir / "config.toml.bak").exists()

    def test_old_schema_real_values_migrated(self):
        self.path.write_text(OLD_SCHEMA_REAL)

        cfg, migration = config.load_config()

        assert migration == config.Migration(path=self.path, backup=self.dir / "config.toml.bak")
        assert migration.backup.read_text() == OLD_SCHEMA_REAL

        target = cfg.select(None)
        assert target.name == "main"
        assert target.url == "https://drops.example.org/"  # normalized
        assert target.storage == config.StorageConfig(type="aws_s3", bucket="real-bucket")
        assert target.cache == config.CacheConfig(type="aws_cloudfront", distribution="E22222")
        assert target.aws_session == {"profile_name": "work"}
        assert target.aws_service == {"verify": True}

        rewritten = tomllib.loads(self.path.read_text())
        assert "aws" not in rewritten
        assert rewritten["default"] == "main"

    def test_migrated_file_not_remigrated(self):
        self.path.write_text(OLD_SCHEMA_REAL)
        first, _ = config.load_config()

        content_after_first = self.path.read_text()
        second, migration = config.load_config()

        assert migration is None
        assert second == first
        assert self.path.read_text() == content_after_first

    def test_existing_backup_fails_safely(self):
        self.path.write_text(OLD_SCHEMA_REAL)
        backup = self.dir / "config.toml.bak"
        backup.write_text("previous backup")

        with pytest.raises(config.ConfigError, match=r"config\.toml\.bak.*Move or remove"):
            config.load_config()

        assert self.path.read_text() == OLD_SCHEMA_REAL
        assert backup.read_text() == "previous backup"

    def test_failed_emission_leaves_no_backup(self):
        self.path.write_text(OLD_SCHEMA_REAL + "\n[aws.session.nested]\nkey = 1\n")

        with pytest.raises(config.ConfigError, match="by hand"):
            config.load_config()

        assert not (self.dir / "config.toml.bak").exists()
        assert self.path.read_text().startswith(OLD_SCHEMA_REAL)

    def test_backup_preserves_permission_bits(self):
        self.path.write_text(OLD_SCHEMA_REAL)
        self.path.chmod(0o600)

        config.load_config()

        backup = self.dir / "config.toml.bak"
        assert backup.stat().st_mode & 0o7777 == 0o600
        assert self.path.stat().st_mode & 0o7777 == 0o600

    def test_unconfigured_new_schema_left_untouched(self):
        content = config.DEFAULT_TEMPLATE.lstrip() + "# my precious notes\n"
        self.path.write_text(content)

        with pytest.raises(config.MustEditConfig) as excinfo:
            config.load_config()

        assert excinfo.value.created is False
        assert self.path.read_text() == content

    def test_zero_targets_left_untouched(self):
        self.path.write_text("# not configured at all\n")

        with pytest.raises(config.MustEditConfig) as excinfo:
            config.load_config()

        assert excinfo.value.created is False
        assert self.path.read_text() == "# not configured at all\n"

    def test_invalid_toml_raises_config_error(self):
        self.path.write_text("this is === not toml")

        with pytest.raises(config.ConfigError, match=r"config\.toml"):
            config.load_config()
