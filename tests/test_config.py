from unittest.mock import MagicMock, Mock, patch

import pytest

from sobe import config


class TestConfig:
    def test_from_dict_with_all_values(self):
        """Test Config.from_dict with all values provided."""
        raw = {
            "url": "https://test.example.com/",
            "aws": {
                "bucket": "test-bucket",
                "cloudfront": "E1234567890123",
                "session": {"region_name": "us-west-2"},
                "service": {"verify": False},
            },
        }
        result = config.Config.from_dict(raw)

        assert result.url == "https://test.example.com/"
        assert isinstance(result.aws, config.AWSConfig)
        assert result.aws.bucket == "test-bucket"
        assert result.aws.cloudfront == "E1234567890123"

    def test_from_dict_with_defaults(self):
        """Test Config.from_dict with default values."""
        result = config.Config.from_dict({})

        assert result.url == "https://example.com/"
        assert isinstance(result.aws, config.AWSConfig)
        assert result.aws.bucket == "example-bucket"
        assert result.aws.cloudfront == "E1111111111111"


class TestLoadConfig:
    def setup_method(self):
        self.mock_pd = MagicMock(name="PlatformDirs")
        self.path = self.mock_pd().user_config_path.__truediv__.return_value = MagicMock(name="path")
        self.mock_toml = Mock(name="tomllib")
        self.toml_result = self.mock_toml.load.return_value = {}

    def test_file_exists(self):
        with (
            patch("sobe.config.PlatformDirs", self.mock_pd),
            patch("sobe.config.tomllib", self.mock_toml),
        ):
            self.path.exists.return_value = True
            self.toml_result["aws"] = {"bucket": "not default"}
            result = config.load_config()

        assert result.aws.bucket == "not default"

    def test_file_does_not_exist(self):
        with (
            patch("sobe.config.PlatformDirs", self.mock_pd),
            patch("sobe.config.tomllib", self.mock_toml),
            pytest.raises(config.MustEditConfig),
        ):
            self.path.exists.return_value = False
            config.load_config()

        assert self.mock_toml.load.called is False

    def test_file_exists_but_unchanged(self):
        with (
            patch("sobe.config.PlatformDirs", self.mock_pd),
            patch("sobe.config.tomllib", self.mock_toml),
            pytest.raises(config.MustEditConfig),
        ):
            self.path.exists.return_value = True
            config.load_config()

        assert self.mock_toml.load.called is True
