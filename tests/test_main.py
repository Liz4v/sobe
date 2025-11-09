import tempfile
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from sobe.config import Config, MustEditConfig
from sobe.main import main, parse_args


class TestParseArgs:
    def test_parse_args_policy_only(self):
        args = parse_args(["--policy"])
        assert args.policy is True
        assert args.year is None
        assert args.invalidate is False
        assert args.delete is False
        assert args.files == []

    def test_parse_args_policy_with_other_args_error(self):
        with pytest.raises(SystemExit) as risen:
            parse_args(["--policy", "--year", "2023"])
        assert risen.value.code != 0

    def test_parse_args_with_year_and_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            file1 = temp_path / "file1.txt"
            file2 = temp_path / "file2.txt"
            file1.write_text("test1")
            file2.write_text("test2")

            args = parse_args(["--year", "2023", str(file1), str(file2)])

        assert args.year == "2023"
        assert args.prefix == "2023/"
        assert args.files == [str(file1), str(file2)]
        assert len(args.paths) == 2
        assert args.paths[0] == file1
        assert args.paths[1] == file2

    def test_parse_args_default_year(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            file1 = temp_path / "file1.txt"
            file1.write_text("test")

            with patch("sobe.main.datetime.date") as mock_date:
                mock_date.today.return_value.year = 2025
                args = parse_args([str(file1)])

        assert args.year == "2025"
        assert args.prefix == "2025/"
        assert args.files == [str(file1)]

    def test_parse_args_year_without_files_error(self):
        with pytest.raises(SystemExit) as risen:
            parse_args(["--year", "2023"])
        assert risen.value.code != 0

    def test_parse_args_delete_without_files_error(self):
        with pytest.raises(SystemExit) as risen:
            parse_args(["--delete"])
        assert risen.value.code != 0

    def test_parse_args_no_files_no_invalidate_prints_help(self):
        with patch("sobe.main.argparse.ArgumentParser.print_help") as mock_help:
            with pytest.raises(SystemExit) as risen:
                parse_args([])

        assert risen.value.code == 0
        mock_help.assert_called_once()

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
        assert args.year == "2025"
        assert args.prefix == "2025/"
        assert args.files == []

    def test_parse_args_list_with_year(self):
        args = parse_args(["--list", "--year", "2024"])
        assert args.list is True
        assert args.year == "2024"
        assert args.prefix == "2024/"

    def test_parse_args_list_with_delete_error(self):
        with pytest.raises(SystemExit):
            parse_args(["--list", "--delete"])

    def test_parse_args_list_with_files_error(self):
        with pytest.raises(SystemExit):
            parse_args(["--list", "file1.txt"])  # filtering not supported yet

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

    def test_year_empty_string(self):
        args = parse_args(["--list", "--year", ""])
        assert args.year == ""
        assert args.prefix == ""

    def test_year_subfolder(self):
        args = parse_args(["--list", "--year", "2024/subfolder"])
        assert args.year == "2024/subfolder"
        assert args.prefix == "2024/subfolder/"

    def test_year_subfolder_trailing_slash(self):
        args = parse_args(["--list", "--year", "2024/subfolder/"])
        assert args.year == "2024/subfolder/"
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
        year="2025",
        invalidate=False,
        delete=False,
        lst=False,
        content_type=None,
        remote_name=None,
    ) -> Namespace:
        return Namespace(
            policy=policy,
            year=year,
            prefix=f"{year}/" if year else "",
            invalidate=invalidate,
            delete=delete,
            list=lst,
            content_type=content_type,
            remote_name=remote_name,
            paths=list(map(Path, files)),
        )

    def test_bad_config(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args()
        mock_load_config.side_effect = MustEditConfig(Path())

        with patch("sobe.main.print") as mock_print, pytest.raises(SystemExit):
            main()

        mock_print.assert_any_call("Created config file at the path below. You must edit it before use.")

    def test_main_policy_mode(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args(policy=True)
        mock_load_config.return_value = Config.from_dict({})
        mock_aws_class().generate_needed_permissions.return_value = "test policy"

        with patch("sobe.main.print") as mock_print:
            main()

        mock_print.assert_called_once_with("test policy")

    def test_main_upload_mode(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args("test.txt")
        mock_load_config.return_value = Config.from_dict({})
        with patch("sobe.main.write") as mock_write, patch("sobe.main.print") as mock_print:
            main()
        mock_write.assert_called_once_with("https://example.com/2025/test.txt ...")
        mock_aws_class().upload.assert_called_once_with("2025/", Path("test.txt"), None, content_type=None)
        mock_print.assert_called_once_with("ok.")

    def test_main_delete_mode_existing_file(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args("test.txt", delete=True)
        mock_load_config.return_value = Config.from_dict({})
        mock_aws_class().delete.return_value = True
        with patch("sobe.main.write") as mock_write, patch("sobe.main.print") as mock_print:
            main()

        mock_write.assert_called_once_with("https://example.com/2025/test.txt ...")
        mock_aws_class().delete.assert_called_once_with("2025/", "test.txt")
        mock_print.assert_called_once_with("deleted.")

    def test_main_delete_mode_nonexistent_file(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args("test.txt", delete=True)
        mock_load_config.return_value = Config.from_dict({})
        mock_aws_class().delete.return_value = False

        with patch("sobe.main.write") as mock_write, patch("sobe.main.print") as mock_print:
            main()

        mock_write.assert_called_once_with("https://example.com/2025/test.txt ...")
        mock_aws_class().delete.assert_called_once_with("2025/", "test.txt")
        mock_print.assert_called_once_with("didn't exist.")

    def test_main_invalidate_mode(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args(invalidate=True)
        mock_load_config.return_value = Config.from_dict({})
        mock_aws_class().invalidate_cache.return_value = iter(["Created", "Completed"])
        with patch("sobe.main.write") as _mock_write, patch("sobe.main.print") as _mock_print:
            main()
        _mock_write.assert_any_call("Clearing cache...")
        _mock_write.assert_any_call(".")
        _mock_print.assert_called_with("complete.")

    def test_main_multiple_files(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args("file1.txt", "file2.txt")
        mock_load_config.return_value = Config.from_dict({})
        with patch("sobe.main.write") as _mock_write, patch("sobe.main.print") as _mock_print:
            main()
        assert mock_aws_class().upload.call_count == 2
        mock_aws_class().upload.assert_any_call("2025/", Path("file1.txt"), None, content_type=None)
        mock_aws_class().upload.assert_any_call("2025/", Path("file2.txt"), None, content_type=None)

    def test_main_upload_with_content_type(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args("custom.bin", content_type="application/x-bin")
        mock_load_config.return_value = Config.from_dict({})

        with patch("sobe.main.write") as _mock_write, patch("sobe.main.print") as _mock_print:
            main()
        _mock_write.assert_called_once_with("https://example.com/2025/custom.bin ...")
        mock_aws_class().upload.assert_called_once_with(
            "2025/", Path("custom.bin"), None, content_type="application/x-bin"
        )
        _mock_print.assert_called_once_with("ok.")

    def test_main_list_mode_with_files(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args(lst=True)
        mock_load_config.return_value = Config.from_dict({})
        mock_aws_class().list.return_value = ["a.txt", "b.png"]

        with patch("sobe.main.print") as mock_print:
            main()

        mock_aws_class().list.assert_called_once_with("2025/")
        mock_print.assert_any_call("https://example.com/2025/a.txt")
        mock_print.assert_any_call("https://example.com/2025/b.png")

    def test_main_list_mode_empty(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args(lst=True)
        mock_load_config.return_value = Config.from_dict({})
        mock_aws_class().list.return_value = []

        with patch("sobe.main.print") as mock_print:
            main()

        mock_aws_class().list.assert_called_once_with("2025/")
        mock_print.assert_called_once_with("No files under https://example.com/2025/")

    def test_main_upload_with_remote_name(self, mock_parse_args, mock_load_config, mock_aws_class):
        mock_parse_args.return_value = self._mock_args("local.txt", remote_name="remote.txt")
        mock_load_config.return_value = Config.from_dict({})
        with patch("sobe.main.write") as _mock_write, patch("sobe.main.print") as _mock_print:
            main()
        _mock_write.assert_called_once_with("https://example.com/2025/local.txt ...")
        mock_aws_class().upload.assert_called_once_with("2025/", Path("local.txt"), "remote.txt", content_type=None)
        _mock_print.assert_called_once_with("ok.")
