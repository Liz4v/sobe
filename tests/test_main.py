import sys
import tempfile
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from sobe.config import Config, ConfigError, Migration, MustEditConfig
from sobe.main import main, parse_args


class TestParseArgs:
    def test_parse_args_policy_only(self):
        args = parse_args(["--policy"])
        assert args.policy is True
        assert args.year is None
        assert args.prefix is None
        assert args.invalidate is False
        assert args.delete is False
        assert args.files == []

    def test_parse_args_policy_with_other_args_error(self):
        with pytest.raises(SystemExit) as risen:
            parse_args(["--policy", "--prefix", "2023"])
        assert risen.value.code != 0

    def test_parse_args_with_prefix_and_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            file1 = temp_path / "file1.txt"
            file2 = temp_path / "file2.txt"
            file1.write_text("test1")
            file2.write_text("test2")

            args = parse_args(["--prefix", "2023", str(file1), str(file2)])

        assert args.prefix == "2023/"
        assert args.files == [str(file1), str(file2)]
        assert len(args.paths) == 2
        assert args.paths[0] == file1
        assert args.paths[1] == file2

    def test_parse_args_default_prefix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            file1 = temp_path / "file1.txt"
            file1.write_text("test")

            with patch("sobe.main.datetime.date") as mock_date:
                mock_date.today.return_value.year = 2025
                args = parse_args([str(file1)])

        assert args.prefix == "2025/"
        assert args.files == [str(file1)]

    def test_parse_args_prefix_without_files_error(self):
        with pytest.raises(SystemExit) as risen:
            parse_args(["--prefix", "2023"])
        assert risen.value.code != 0

    def test_parse_args_delete_without_files_error(self):
        with pytest.raises(SystemExit) as risen:
            parse_args(["--delete"])
        assert risen.value.code != 0

    def test_parse_args_no_files_no_invalidate_returns_bare(self):
        with patch("sobe.main.argparse.ArgumentParser.print_help") as mock_help:
            args = parse_args([])

        assert args.bare is True
        mock_help.assert_not_called()

    def test_parse_args_invalidate_only(self):
        args = parse_args(["--invalidate"])

        assert args.invalidate is True
        assert args.files == []

    def test_parse_args_delete_with_files(self):
        args = parse_args(["--delete", "file1.txt", "file2.txt"])

        assert args.delete is True
        assert args.files == ["file1.txt", "file2.txt"]
        assert len(args.paths) == 2

    def test_parse_args_list_only(self):
        with patch("sobe.main.datetime.date") as mock_date:
            mock_date.today.return_value.year = 2025
            args = parse_args(["--list"])

        assert args.list is True
        assert args.prefix == "2025/"
        assert args.files == []
        assert args.bare is False

    def test_parse_args_list_with_prefix(self):
        args = parse_args(["--list", "--prefix", "2024"])
        assert args.list is True
        assert args.prefix == "2024/"

    def test_parse_args_list_with_delete_error(self):
        with pytest.raises(SystemExit):
            parse_args(["--list", "--delete"])

    def test_parse_args_list_with_files_error(self):
        with pytest.raises(SystemExit):
            parse_args(["--list", "file1.txt"])  # filtering not supported yet

    def test_parse_args_list_with_invalidate_error(self):
        with pytest.raises(SystemExit):
            parse_args(["--list", "--invalidate"])

    def test_parse_args_content_type_with_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            file1 = temp_path / "file1.txt"
            file1.write_text("test1")
            args = parse_args(["--content-type", "text/custom", str(file1)])

        assert args.content_type == "text/custom"
        assert args.files == [str(file1)]
        assert args.paths[0] == file1

    def test_parse_args_content_type_without_files_error(self):
        with pytest.raises(SystemExit):
            parse_args(["--content-type", "text/plain"])

    def test_parse_args_content_type_with_delete_error(self):
        with pytest.raises(SystemExit):
            parse_args(["--content-type", "text/plain", "--delete", "file.txt"])

    def test_parse_args_content_type_with_list_error(self):
        with pytest.raises(SystemExit):
            parse_args(["--content-type", "text/plain", "--list"])

    def test_parse_args_nonexistent_files_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            existing_file = temp_path / "existing.txt"
            existing_file.write_text("test")

            nonexistent_file = temp_path / "nonexistent.txt"

        with pytest.raises(SystemExit) as risen:
            parse_args([str(existing_file), str(nonexistent_file)])
        assert risen.value.code != 0

    def test_parse_args_existing_files_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            file1 = temp_path / "file1.txt"
            file2 = temp_path / "file2.txt"
            file1.write_text("test1")
            file2.write_text("test2")

            args = parse_args([str(file1), str(file2)])

        assert len(args.paths) == 2
        assert args.paths[0] == file1
        assert args.paths[1] == file2

    def test_prefix_empty_string(self):
        args = parse_args(["--list", "--prefix", ""])
        assert args.prefix == ""

    def test_prefix_subfolder(self):
        args = parse_args(["--list", "--prefix", "2024/subfolder"])
        assert args.prefix == "2024/subfolder/"

    def test_prefix_subfolder_trailing_slash(self):
        args = parse_args(["--list", "--prefix", "2024/subfolder/"])
        assert args.prefix == "2024/subfolder/"

    # --remote-name tests
    def test_parse_args_remote_name_with_single_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            file1 = temp_path / "local.txt"
            file1.write_text("x")
            args = parse_args(["--remote-name", "remote.txt", str(file1)])

        assert args.remote_name == "remote.txt"
        assert args.files == [str(file1)]
        assert args.paths[0] == file1

    def test_parse_args_remote_name_with_multiple_files_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            file1 = temp_path / "a.txt"
            file2 = temp_path / "b.txt"
            file1.write_text("a")
            file2.write_text("b")
            with pytest.raises(SystemExit):
                parse_args(["--remote-name", "remote.txt", str(file1), str(file2)])

    def test_parse_args_remote_name_without_files_error(self):
        with pytest.raises(SystemExit):
            parse_args(["--remote-name", "remote.txt"])

    def test_parse_args_remote_name_with_delete_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            file1 = temp_path / "a.txt"
            file1.write_text("a")
            with pytest.raises(SystemExit):
                parse_args(["--remote-name", "remote.txt", "--delete", str(file1)])

    def test_parse_args_remote_name_with_list_error(self):
        with pytest.raises(SystemExit):
            parse_args(["--remote-name", "remote.txt", "--list"])  # list mode not compatible

    def test_parse_args_version_flag(self):
        # Argparse's --version action should exit cleanly with code 0
        with pytest.raises(SystemExit) as risen:
            parse_args(["--version"])
        assert risen.value.code == 0

    # -t/--target tests
    def test_parse_args_target_with_upload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = Path(temp_dir) / "file1.txt"
            file1.write_text("test")
            args = parse_args(["--target", "alpha", str(file1)])

        assert args.target == "alpha"
        assert args.paths == [file1]

    def test_parse_args_target_short_form(self):
        args = parse_args(["-t", "alpha", "--list"])
        assert args.target == "alpha"
        assert args.list is True

    def test_parse_args_target_with_delete(self):
        args = parse_args(["-t", "alpha", "--delete", "file1.txt"])
        assert args.target == "alpha"
        assert args.delete is True

    def test_parse_args_target_with_invalidate(self):
        args = parse_args(["-t", "alpha", "--invalidate"])
        assert args.target == "alpha"
        assert args.invalidate is True

    def test_parse_args_target_with_policy(self):
        args = parse_args(["--policy", "--target", "alpha"])
        assert args.policy is True
        assert args.target == "alpha"

    def test_parse_args_policy_with_target_and_more_error(self):
        with pytest.raises(SystemExit) as risen:
            parse_args(["--policy", "--target", "alpha", "--prefix", "2024"])
        assert risen.value.code != 0

    def test_parse_args_target_alone_error(self):
        with pytest.raises(SystemExit) as risen:
            parse_args(["--target", "alpha"])
        assert risen.value.code != 0

    def test_parse_args_empty_target_alone_returns_bare(self):
        # An empty --target counts as not given, so this is the same as bare `sobe`.
        with patch("sobe.main.argparse.ArgumentParser.print_help") as mock_help:
            args = parse_args(["-t", ""])

        assert args.bare is True
        mock_help.assert_not_called()

    def test_parse_args_empty_target_treated_as_not_given(self):
        args = parse_args(["-t", "", "--list"])
        assert not args.target

    def test_parse_args_no_target_is_none(self):
        args = parse_args(["--list"])
        assert args.target is None

    def test_parse_args_content_type_is_long_only(self):
        # Old muscle memory `-t MIME` now parses as a target name, never as a content type.
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = Path(temp_dir) / "file1.txt"
            file1.write_text("test")
            args = parse_args(["-t", "image/png", str(file1)])

        assert args.target == "image/png"  # rejected later by selection: "/" is not a valid target name
        assert args.content_type is None

    # -p/--prefix and -y/--year alias tests

    def test_year_alias_works_and_warns_on_stderr_once(self, capsys):
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = Path(temp_dir) / "file1.txt"
            file1.write_text("test")
            args = parse_args(["--year", "2024", str(file1)])

        assert args.prefix == "2024/"
        captured = capsys.readouterr()
        assert captured.err.count("warning: --year is deprecated, use --prefix; it will be removed in sobe 2.0") == 1
        assert "warning:" not in captured.out

    def test_year_alias_works_with_list_and_warns_once(self, capsys):
        args = parse_args(["--year", "2024", "--list"])

        assert args.prefix == "2024/"
        captured = capsys.readouterr()
        assert captured.err.count("warning: --year is deprecated") == 1
        assert "warning:" not in captured.out

    def test_prefix_and_year_conflict_error(self):
        with pytest.raises(SystemExit) as risen:
            parse_args(["--prefix", "2024", "--year", "2025", "f.txt"])
        assert risen.value.code == 2

    def test_prefix_and_year_conflict_error_short_form(self):
        with pytest.raises(SystemExit) as risen:
            parse_args(["-p", "2024", "-y", "2025", "f.txt"])
        assert risen.value.code == 2

    def test_parse_args_prefix_short_form(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = Path(temp_dir) / "file1.txt"
            file1.write_text("test")
            args = parse_args(["-p", "2024", str(file1)])

        assert args.prefix == "2024/"

    def test_parse_args_bare_dash_p_no_value_error(self):
        with pytest.raises(SystemExit) as risen:
            parse_args(["-p"])
        assert risen.value.code == 2

    def test_dash_p_no_longer_means_policy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = Path(temp_dir) / "file1.txt"
            file1.write_text("test")
            args = parse_args(["-p", "2024", str(file1)])

        assert args.policy is False
        assert args.prefix == "2024/"

    def test_dash_p_muscle_memory_file_txt_hits_requires_files_error(self):
        # 0.x --policy habit: `-p file.txt` now consumes file.txt as the prefix value,
        # leaving no positional files, so it hits the requires-files-or-list error.
        with pytest.raises(SystemExit) as risen:
            parse_args(["-p", "file.txt"])
        assert risen.value.code == 2

    # Leading-slash normalization

    def test_prefix_leading_slash_is_root(self):
        args = parse_args(["--list", "--prefix", "/"])
        assert args.prefix == ""

    def test_prefix_double_leading_slash_is_root(self):
        args = parse_args(["--list", "--prefix", "//"])
        assert args.prefix == ""

    def test_prefix_leading_slash_with_value(self):
        args = parse_args(["--list", "--prefix", "/2024"])
        assert args.prefix == "2024/"

    def test_prefix_double_leading_slash_with_trailing_slash(self):
        args = parse_args(["--list", "--prefix", "//2024/"])
        assert args.prefix == "2024/"

    def test_year_alias_leading_slash_normalizes_and_warns(self, capsys):
        args = parse_args(["--list", "--year", "/"])

        assert args.prefix == ""
        captured = capsys.readouterr()
        assert "warning: --year is deprecated" in captured.err

    def test_prefix_slash_alone_errors(self):
        # Unlike `--prefix ''` alone (which counts as bare, so its outcome depends on
        # config state), `/` is truthy before stripping, so this hits the
        # requires-files-or-list validation error.
        with pytest.raises(SystemExit) as risen:
            parse_args(["--prefix", "/"])
        assert risen.value.code == 2

    def test_prefix_slash_alone_with_file_is_root_upload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = Path(temp_dir) / "index.html"
            file1.write_text("<html></html>")
            args = parse_args(["--prefix", "/", str(file1)])

        assert args.prefix == ""
        assert args.paths == [file1]

    def test_year_alias_slash_with_file_is_root_upload_and_warns(self, capsys):
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = Path(temp_dir) / "index.html"
            file1.write_text("<html></html>")
            args = parse_args(["--year", "/", str(file1)])

        assert args.prefix == ""
        captured = capsys.readouterr()
        assert "warning: --year is deprecated" in captured.err

    def test_year_alias_empty_string_root_upload_and_warns(self, capsys):
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = Path(temp_dir) / "index.html"
            file1.write_text("<html></html>")
            args = parse_args(["-y", "", str(file1)])

        assert args.prefix == ""
        captured = capsys.readouterr()
        assert "warning: --year is deprecated" in captured.err

    # --help output

    def test_help_output_shows_prefix_and_deprecated_year(self, capsys):
        with pytest.raises(SystemExit) as risen:
            parse_args(["--help"])

        assert risen.value.code == 0
        captured = capsys.readouterr()
        assert "--prefix" in captured.out
        assert "deprecated alias for --prefix (removed in 2.0)" in captured.out

    # Validation error wording

    def test_prefix_requires_files_error_message(self, capsys):
        with pytest.raises(SystemExit) as risen:
            parse_args(["--prefix", "2024"])

        assert risen.value.code == 2
        captured = capsys.readouterr()
        assert "--prefix requires files or --list to be specified" in captured.err

    def test_year_alias_requires_files_error_message(self, capsys):
        with pytest.raises(SystemExit) as risen:
            parse_args(["--year", "2024"])

        assert risen.value.code == 2
        captured = capsys.readouterr()
        assert "--prefix requires files or --list to be specified" in captured.err


def make_config(*names: str, url: str | None = "https://example.com/", cache=True, default=None) -> Config:
    """New-schema Config with the given targets (default: one named "main")."""
    target: dict = {"storage": {"type": "aws_s3", "bucket": "my-bucket"}}
    if url is not None:
        target["url"] = url
    if cache:
        target["cache"] = {"type": "aws_cloudfront", "distribution": "E1111111111111"}
    raw: dict = {"target": {name: dict(target) for name in names or ("main",)}}
    if default is not None:
        raw["default"] = default
    return Config.from_dict(raw)


@patch("sobe.main.AWS")
@patch("sobe.main.load_config")
@patch("sobe.main.parse_args")
class TestMain:
    # I'm not sure whether we should be asserting over prints and writes.
    # This could easily become a maintenance nightmare. Keeping them in for now.

    def _mock_args(
        self,
        *files: str,
        policy=False,
        prefix="2025/",
        invalidate=False,
        delete=False,
        lst=False,
        content_type=None,
        remote_name=None,
        target=None,
    ) -> Namespace:
        return Namespace(
            policy=policy,
            year=None,
            prefix=prefix,
            invalidate=invalidate,
            delete=delete,
            list=lst,
            content_type=content_type,
            remote_name=remote_name,
            target=target,
            paths=list(map(Path, files)),
            bare=False,
        )

    def test_bad_config_created(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args()
        mock_load_config.side_effect = MustEditConfig(Path(), created=True)

        with patch("sobe.main.print") as mock_print, pytest.raises(SystemExit) as risen:
            main()

        assert risen.value.code == 1
        mock_print.assert_any_call("Created config file at the path below. You must edit it before use.")
        mock_print.assert_any_call("Full setup tutorial: https://sobe.readthedocs.io/en/latest/tutorial.html")

    def test_bad_config_existing_unconfigured(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args()
        mock_load_config.side_effect = MustEditConfig(Path(), created=False)

        with patch("sobe.main.print") as mock_print, pytest.raises(SystemExit) as risen:
            main()

        assert risen.value.code == 1
        mock_print.assert_any_call(
            "The config file at the path below is not configured yet. You must edit it before use."
        )
        mock_print.assert_any_call("Full setup tutorial: https://sobe.readthedocs.io/en/latest/tutorial.html")

    def test_config_error_on_load(self, mock_parse_args, mock_load_config, mock_aws_class):
        error = ConfigError("Cannot parse config.toml")
        mock_load_config.side_effect = error

        with patch("sobe.main.print") as mock_print, pytest.raises(SystemExit) as risen:
            main()

        assert risen.value.code == 1
        mock_print.assert_called_once_with(error)

    def test_migration_notice(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args(lst=True)
        migration = Migration(path=Path("/cfg/config.toml"), backup=Path("/cfg/config.toml.bak"))
        mock_load_config.return_value = (make_config(), migration)
        mock_aws_class().list.return_value = []

        with patch("sobe.main.print") as mock_print:
            main()

        mock_print.assert_any_call("Migrated config file /cfg/config.toml to the new multi-target format.")
        mock_print.assert_any_call("The original file was saved to /cfg/config.toml.bak")

    def test_selection_error_ambiguous_exits_1(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args(lst=True)
        mock_load_config.return_value = (make_config("alpha", "beta"), None)

        with patch("sobe.main.print") as mock_print, pytest.raises(SystemExit) as risen:
            main()

        assert risen.value.code == 1
        message = str(mock_print.call_args[0][0])
        assert "alpha" in message and "beta" in message
        mock_aws_class.assert_not_called()

    def test_selection_error_unknown_target_exits_1(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args(lst=True, target="image/png")
        mock_load_config.return_value = (make_config("alpha"), None)

        with patch("sobe.main.print") as mock_print, pytest.raises(SystemExit) as risen:
            main()

        assert risen.value.code == 1
        message = str(mock_print.call_args[0][0])
        assert '"image/png" is not defined' in message and "alpha" in message

    def test_selected_target_used(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args(lst=True, target="beta")
        config = make_config("alpha", "beta")
        mock_load_config.return_value = (config, None)
        mock_aws_class.reset_mock()
        mock_aws_class().list.return_value = []

        with patch("sobe.main.print"):
            main()

        mock_aws_class.assert_called_with(config.targets["beta"])

    def test_main_policy_mode(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args(policy=True)
        mock_load_config.return_value = (make_config(), None)
        mock_aws_class().generate_needed_permissions.return_value = "test policy"

        with patch("sobe.main.print") as mock_print:
            main()

        mock_print.assert_called_once_with("test policy")

    def test_main_policy_mode_scoped_to_selected_target(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args(policy=True, target="beta")
        config = make_config("alpha", "beta")
        mock_load_config.return_value = (config, None)
        mock_aws_class.reset_mock()
        mock_aws_class().generate_needed_permissions.return_value = "test policy"

        with patch("sobe.main.print") as mock_print:
            main()

        mock_aws_class.assert_called_with(config.targets["beta"])
        mock_print.assert_called_once_with("test policy")

    def test_main_upload_mode(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args("test.txt")
        mock_load_config.return_value = (make_config(), None)
        with patch("sobe.main.write") as mock_write, patch("sobe.main.print") as mock_print:
            main()
        mock_write.assert_called_once_with("https://example.com/2025/test.txt ...")
        mock_aws_class().upload.assert_called_once_with("2025/", Path("test.txt"), None, content_type=None)
        mock_print.assert_called_once_with("ok.")

    def test_main_delete_mode_existing_file(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args("test.txt", delete=True)
        mock_load_config.return_value = (make_config(), None)
        mock_aws_class().delete.return_value = True
        with patch("sobe.main.write") as mock_write, patch("sobe.main.print") as mock_print:
            main()

        mock_write.assert_called_once_with("https://example.com/2025/test.txt ...")
        mock_aws_class().delete.assert_called_once_with("2025/", "test.txt")
        mock_print.assert_called_once_with("deleted.")

    def test_main_delete_mode_nonexistent_file(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args("test.txt", delete=True)
        mock_load_config.return_value = (make_config(), None)
        mock_aws_class().delete.return_value = False

        with patch("sobe.main.write") as mock_write, patch("sobe.main.print") as mock_print:
            main()

        mock_write.assert_called_once_with("https://example.com/2025/test.txt ...")
        mock_aws_class().delete.assert_called_once_with("2025/", "test.txt")
        mock_print.assert_called_once_with("didn't exist.")

    def test_main_invalidate_mode(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args(invalidate=True)
        mock_load_config.return_value = (make_config(), None)
        mock_aws_class().invalidate_cache.return_value = iter(["Created", "Completed"])
        with patch("sobe.main.write") as _mock_write, patch("sobe.main.print") as _mock_print:
            main()
        _mock_write.assert_any_call("Clearing cache...")
        _mock_write.assert_any_call(".")
        _mock_print.assert_called_with("complete.")

    def test_main_invalidate_without_cache_skips_with_notice(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args(invalidate=True)
        mock_load_config.return_value = (make_config(cache=False), None)

        with patch("sobe.main.write") as mock_write, patch("sobe.main.print") as mock_print:
            main()  # exits normally (code 0), no SystemExit

        mock_aws_class().invalidate_cache.assert_not_called()
        mock_write.assert_not_called()
        mock_print.assert_called_once_with('Target "main" has no cache configured; skipping invalidation.')

    def test_main_upload_invalidate_without_cache_still_uploads(
        self, mock_parse_args, mock_load_config, mock_aws_class
    ):
        mock_parse_args.return_value = self._mock_args("test.txt", invalidate=True)
        mock_load_config.return_value = (make_config(cache=False), None)

        with patch("sobe.main.write"), patch("sobe.main.print") as mock_print:
            main()

        mock_aws_class().upload.assert_called_once()
        mock_aws_class().invalidate_cache.assert_not_called()
        mock_print.assert_any_call('Target "main" has no cache configured; skipping invalidation.')

    def test_main_multiple_files(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args("file1.txt", "file2.txt")
        mock_load_config.return_value = (make_config(), None)
        with patch("sobe.main.write") as _mock_write, patch("sobe.main.print") as _mock_print:
            main()
        assert mock_aws_class().upload.call_count == 2
        mock_aws_class().upload.assert_any_call("2025/", Path("file1.txt"), None, content_type=None)
        mock_aws_class().upload.assert_any_call("2025/", Path("file2.txt"), None, content_type=None)

    def test_main_upload_with_content_type(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args("custom.bin", content_type="application/x-bin")
        mock_load_config.return_value = (make_config(), None)

        with patch("sobe.main.write") as _mock_write, patch("sobe.main.print") as _mock_print:
            main()
        _mock_write.assert_called_once_with("https://example.com/2025/custom.bin ...")
        mock_aws_class().upload.assert_called_once_with(
            "2025/", Path("custom.bin"), None, content_type="application/x-bin"
        )
        _mock_print.assert_called_once_with("ok.")

    def test_main_list_mode_with_files(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args(lst=True)
        mock_load_config.return_value = (make_config(), None)
        mock_aws_class().list.return_value = ["a.txt", "b.png"]

        with patch("sobe.main.print") as mock_print:
            main()

        mock_aws_class().list.assert_called_once_with("2025/")
        mock_print.assert_any_call("https://example.com/2025/a.txt")
        mock_print.assert_any_call("https://example.com/2025/b.png")

    def test_main_list_mode_empty(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args(lst=True)
        mock_load_config.return_value = (make_config(), None)
        mock_aws_class().list.return_value = []

        with patch("sobe.main.print") as mock_print:
            main()

        mock_aws_class().list.assert_called_once_with("2025/")
        mock_print.assert_called_once_with("No files under https://example.com/2025/")

    def test_main_upload_no_url_uses_bucket_prefix(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args("test.txt")
        mock_load_config.return_value = (make_config(url=None), None)

        with patch("sobe.main.write") as mock_write, patch("sobe.main.print"):
            main()

        mock_write.assert_called_once_with("my-bucket/2025/test.txt ...")

    def test_main_delete_no_url_uses_bucket_prefix(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args("test.txt", delete=True)
        mock_load_config.return_value = (make_config(url=None), None)
        mock_aws_class().delete.return_value = True

        with patch("sobe.main.write") as mock_write, patch("sobe.main.print"):
            main()

        mock_write.assert_called_once_with("my-bucket/2025/test.txt ...")

    def test_main_list_no_url_uses_bucket_prefix(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args(lst=True)
        mock_load_config.return_value = (make_config(url=None), None)
        mock_aws_class().list.return_value = ["a.txt"]

        with patch("sobe.main.print") as mock_print:
            main()

        mock_print.assert_any_call("my-bucket/2025/a.txt")

    def test_main_list_empty_no_url_uses_bucket_prefix(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args(lst=True)
        mock_load_config.return_value = (make_config(url=None), None)
        mock_aws_class().list.return_value = []

        with patch("sobe.main.print") as mock_print:
            main()

        mock_print.assert_called_once_with("No files under my-bucket/2025/")

    def test_main_upload_with_remote_name(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args("local.txt", remote_name="remote.txt")
        mock_load_config.return_value = (make_config(), None)
        with patch("sobe.main.write") as _mock_write, patch("sobe.main.print") as _mock_print:
            main()
        _mock_write.assert_called_once_with("https://example.com/2025/remote.txt ...")
        mock_aws_class().upload.assert_called_once_with("2025/", Path("local.txt"), "remote.txt", content_type=None)
        _mock_print.assert_called_once_with("ok.")


class TestMainArgsBeforeConfig:
    """main() parses arguments before any config access; bare `sobe` still runs the config phase."""

    def test_help_never_touches_config(self, monkeypatch, capsys):
        mock_load_config = Mock(side_effect=AssertionError("load_config should not be called"))
        monkeypatch.setattr("sobe.main.load_config", mock_load_config)
        monkeypatch.setattr(sys, "argv", ["sobe", "--help"])

        with pytest.raises(SystemExit) as risen:
            main()

        assert risen.value.code == 0
        mock_load_config.assert_not_called()
        assert "usage:" in capsys.readouterr().out

    def test_version_never_touches_config(self, monkeypatch, capsys):
        mock_load_config = Mock(side_effect=AssertionError("load_config should not be called"))
        monkeypatch.setattr("sobe.main.load_config", mock_load_config)
        monkeypatch.setattr(sys, "argv", ["sobe", "--version"])

        with pytest.raises(SystemExit) as risen:
            main()

        assert risen.value.code == 0
        mock_load_config.assert_not_called()
        assert capsys.readouterr().out.startswith("sobe ")

    def test_argument_error_preempts_config_access(self, monkeypatch):
        # --prefix without files or --list is a validation error; no template may be written.
        mock_load_config = Mock(side_effect=AssertionError("load_config should not be called"))
        monkeypatch.setattr("sobe.main.load_config", mock_load_config)
        monkeypatch.setattr(sys, "argv", ["sobe", "--prefix", "2024"])

        with pytest.raises(SystemExit) as risen:
            main()

        assert risen.value.code == 2
        mock_load_config.assert_not_called()

    def test_bare_enters_config_phase(self, monkeypatch):
        mock_load_config = Mock(side_effect=MustEditConfig(Path(), created=True))
        monkeypatch.setattr("sobe.main.load_config", mock_load_config)
        monkeypatch.setattr(sys, "argv", ["sobe"])

        with patch("sobe.main.print") as mock_print, pytest.raises(SystemExit) as risen:
            main()

        assert risen.value.code == 1
        mock_print.assert_any_call("Created config file at the path below. You must edit it before use.")
        mock_print.assert_any_call("Full setup tutorial: https://sobe.readthedocs.io/en/latest/tutorial.html")

    def test_bare_with_configured_config_prints_help(self, monkeypatch, capsys):
        mock_load_config = Mock(return_value=(make_config(), None))
        monkeypatch.setattr("sobe.main.load_config", mock_load_config)
        monkeypatch.setattr(sys, "argv", ["sobe"])

        with pytest.raises(SystemExit) as risen:
            main()

        assert risen.value.code == 0
        mock_load_config.assert_called_once()
        assert "usage:" in capsys.readouterr().out
