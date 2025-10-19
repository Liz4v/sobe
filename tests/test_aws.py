import json
import pathlib
import tempfile
from unittest.mock import Mock, patch

import botocore.exceptions
import pytest

from sobe.aws import AWS
from sobe.config import AWSConfig


def mock_boto_session():
    """Create a mock boto3 session with all necessary components."""
    mock_session = Mock()
    mock_s3_resource = Mock()
    mock_bucket = Mock()
    mock_cloudfront_client = Mock()

    # Configure the mock session
    mock_session.resource.return_value = mock_s3_resource
    mock_session.client.return_value = mock_cloudfront_client
    mock_s3_resource.Bucket.return_value = mock_bucket

    return mock_session, mock_bucket, mock_cloudfront_client


class TestAWS:
    def setup_method(self):
        self.config = AWSConfig(
            bucket="test-bucket",
            cloudfront="E1234567890123",
            session={"region_name": "ca-west-1"},
            service={"verify": True},
        )

    def test_init(self):
        mock_session, _, _ = mock_boto_session()

        with patch("sobe.aws.boto3.Session") as mock_session_class:
            mock_session_class.return_value = mock_session
            aws = AWS(self.config)

        assert aws.config == self.config
        mock_session_class.assert_called_once_with(region_name="ca-west-1")
        mock_session.resource.assert_called_once_with("s3", verify=True)
        mock_session.client.assert_called_once_with("cloudfront", verify=True)

    @patch("sobe.aws.mimetypes.guess_type")
    def test_upload_with_known_mime_type(self, mock_guess_type):
        mock_guess_type.return_value = ("text/plain", None)
        mock_session, mock_bucket, _ = mock_boto_session()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=True) as f:
            f.write("test content")
            test_file = pathlib.Path(f.name)

            with patch("sobe.aws.boto3.Session") as mock_session_class:
                mock_session_class.return_value = mock_session
                aws = AWS(self.config)
                aws.upload("2025/", test_file)

        mock_bucket.upload_file.assert_called_once_with(
            str(test_file), f"2025/{test_file.name}", ExtraArgs={"ContentType": "text/plain"}
        )

    @patch("sobe.aws.mimetypes.guess_type")
    def test_upload_with_unknown_mime_type(self, mock_guess_type):
        mock_guess_type.return_value = (None, None)
        mock_session, mock_bucket, _ = mock_boto_session()

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".unknown", delete=True) as f:
            f.write("test content")
            test_file = pathlib.Path(f.name)

            with patch("sobe.aws.boto3.Session") as mock_session_class:
                mock_session_class.return_value = mock_session
                aws = AWS(self.config)
                aws.upload("2025/", test_file)

        mock_bucket.upload_file.assert_called_once_with(
            str(test_file), f"2025/{test_file.name}", ExtraArgs={"ContentType": "application/octet-stream"}
        )

    def test_delete_existing_file(self):
        mock_session, mock_bucket, _ = mock_boto_session()
        mock_object = Mock()
        mock_bucket.Object.return_value = mock_object

        with patch("sobe.aws.boto3.Session") as mock_session_class:
            mock_session_class.return_value = mock_session
            aws = AWS(self.config)
            result = aws.delete("2025/", "test.txt")

        assert result is True
        mock_bucket.Object.assert_called_once_with("2025/test.txt")
        mock_object.load.assert_called_once()
        mock_object.delete.assert_called_once()

    def test_delete_nonexistent_file(self):
        mock_session, mock_bucket, _ = mock_boto_session()
        mock_object = Mock()

        # Simulate 404 error
        error = botocore.exceptions.ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
        mock_object.load.side_effect = error

        mock_bucket.Object.return_value = mock_object

        with patch("sobe.aws.boto3.Session") as mock_session_class:
            mock_session_class.return_value = mock_session
            aws = AWS(self.config)
            result = aws.delete("2025/", "nonexistent.txt")

        assert result is False
        mock_bucket.Object.assert_called_once_with("2025/nonexistent.txt")
        mock_object.load.assert_called_once()
        mock_object.delete.assert_not_called()

    def test_delete_other_error(self):
        mock_session, mock_bucket, _ = mock_boto_session()
        mock_object = Mock()

        # Simulate other error
        error = botocore.exceptions.ClientError({"Error": {"Code": "403", "Message": "Forbidden"}}, "HeadObject")
        mock_object.load.side_effect = error

        mock_bucket.Object.return_value = mock_object

        with patch("sobe.aws.boto3.Session") as mock_session_class:
            mock_session_class.return_value = mock_session
            aws = AWS(self.config)
            with pytest.raises(botocore.exceptions.ClientError):
                aws.delete("2025", "forbidden.txt")

    @patch("sobe.aws.datetime.datetime")
    def test_invalidate_cache(self, mock_datetime):
        # Mock datetime
        mock_now = Mock()
        mock_now.astimezone.return_value.isoformat.return_value = "2025-01-01T12:00:00+00:00"
        mock_datetime.now.return_value = mock_now

        mock_session, _, mock_cloudfront = mock_boto_session()

        # Mock invalidation responses
        create_response = {"Invalidation": {"Id": "E1234567890123"}}
        get_response_created = {"Invalidation": {"Status": "Created"}}
        get_response_completed = {"Invalidation": {"Status": "Completed"}}

        mock_cloudfront.create_invalidation.return_value = create_response
        mock_cloudfront.get_invalidation.side_effect = [
            get_response_created,
            get_response_created,
            get_response_completed,
        ]

        with (
            patch("sobe.aws.boto3.Session") as mock_session_class,
            patch("sobe.aws.time.sleep") as mock_sleep,
        ):
            mock_session_class.return_value = mock_session
            aws = AWS(self.config)
            statuses = list(aws.invalidate_cache())

        assert statuses == ["Created", "Created", "Created"]
        mock_cloudfront.create_invalidation.assert_called_once_with(
            DistributionId="E1234567890123",
            InvalidationBatch={
                "Paths": {"Quantity": 1, "Items": ["/*"]},
                "CallerReference": "2025-01-01T12:00:00+00:00",
            },
        )
        assert mock_cloudfront.get_invalidation.call_count == 3
        assert mock_sleep.call_count == 3

    def test_generate_needed_permissions_success(self):
        mock_session, _, _ = mock_boto_session()
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_session.client.return_value = mock_sts

        with patch("sobe.aws.boto3.Session") as mock_session_class:
            mock_session_class.return_value = mock_session
            aws = AWS(self.config)
            policy_json = aws.generate_needed_permissions()
            policy = json.loads(policy_json)

        assert policy["Version"] == "2012-10-17"
        assert len(policy["Statement"]) == 1

        statement = policy["Statement"][0]
        assert statement["Effect"] == "Allow"
        assert "s3:PutObject" in statement["Action"]
        assert "s3:GetObject" in statement["Action"]
        assert "s3:ListBucket" in statement["Action"]
        assert "s3:DeleteObject" in statement["Action"]
        assert "cloudfront:CreateInvalidation" in statement["Action"]
        assert "cloudfront:GetInvalidation" in statement["Action"]

        assert "arn:aws:s3:::test-bucket" in statement["Resource"]
        assert "arn:aws:s3:::test-bucket/*" in statement["Resource"]
        assert "arn:aws:cloudfront::123456789012:distribution/E1234567890123" in statement["Resource"]

    def test_generate_needed_permissions_sts_error(self):
        mock_session, _, _ = mock_boto_session()
        mock_sts = Mock()
        mock_sts.get_caller_identity.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}, "GetCallerIdentity"
        )
        mock_session.client.return_value = mock_sts

        with patch("sobe.aws.boto3.Session") as mock_session_class:
            mock_session_class.return_value = mock_session
            aws = AWS(self.config)
            policy_json = aws.generate_needed_permissions()
            policy = json.loads(policy_json)

        # Should use placeholder account ID
        statement = policy["Statement"][0]
        assert "arn:aws:cloudfront::YOUR_ACCOUNT_ID:distribution/E1234567890123" in statement["Resource"]

    def test_list_year_directory(self):
        mock_session, mock_bucket, _ = mock_boto_session()

        obj1 = Mock()
        obj1.key = "2025/"  # no (base directory placeholder)
        obj2 = Mock()
        obj2.key = "2025/file1.txt"  # yes
        obj3 = Mock()
        obj3.key = "2025/file2.txt"  # yes
        obj4 = Mock()
        obj4.key = "2025/subdir/"  # yes (subdir placeholder)
        obj5 = Mock()
        obj5.key = "2025/subdir/file3.txt"  # no (recursive entry)
        mock_bucket.objects.filter.return_value = [obj1, obj2, obj3, obj4, obj5]

        with patch("sobe.aws.boto3.Session") as mock_session_class:
            mock_session_class.return_value = mock_session
            aws = AWS(self.config)
            listing = aws.list("2025/")

        assert listing == ["file1.txt", "file2.txt", "subdir/"]
        mock_bucket.objects.filter.assert_called_once_with(Prefix="2025/")
