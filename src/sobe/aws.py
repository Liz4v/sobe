import datetime
import json
import mimetypes
import pathlib
import time

import boto3
import botocore.exceptions

from .config import AWSConfig


class AWS:
    def __init__(self, config: AWSConfig) -> None:
        self.config = config
        self._session = boto3.Session(**self.config.session)
        self._s3_resource = self._session.resource("s3", **self.config.service)
        self._bucket = self._s3_resource.Bucket(self.config.bucket)  # type: ignore[attr-defined]
        self._cloudfront = self._session.client("cloudfront", **self.config.service)

    def upload(self, year: str, local_path: pathlib.Path) -> None:
        """Uploads a file."""
        type_guess, _ = mimetypes.guess_type(local_path)
        extra_args = {"ContentType": type_guess or "application/octet-stream"}
        self._bucket.upload_file(str(local_path), f"{year}/{local_path.name}", ExtraArgs=extra_args)

    def delete(self, year: str, remote_filename: str) -> bool:
        """Delete a file, if it exists. Returns whether it did."""
        obj = self._bucket.Object(f"{year}/{remote_filename}")
        try:
            obj.load()
            obj.delete()
            return True
        except botocore.exceptions.ClientError as e:  # pragma: no cover - network edge
            if e.response.get("Error", {}).get("Code") == "404":
                return False
            raise

    def invalidate_cache(self):
        """Create and wait for a full-path CloudFront invalidation. Iterates until completion."""
        ref = datetime.datetime.now().astimezone().isoformat()
        batch = {"Paths": {"Quantity": 1, "Items": ["/*"]}, "CallerReference": ref}
        distribution = self.config.cloudfront
        response = self._cloudfront.create_invalidation(DistributionId=distribution, InvalidationBatch=batch)
        invalidation = response["Invalidation"]["Id"]
        status = "Created"
        while status != "Completed":  # pragma: no cover - polling side effect
            yield status
            time.sleep(3)
            response = self._cloudfront.get_invalidation(DistributionId=distribution, Id=invalidation)
            status = response["Invalidation"]["Status"]

    def generate_needed_permissions(self) -> str:
        """Return the minimal IAM policy statement required by the tool."""
        try:
            sts = self._session.client("sts", **self.config.service)
            account_id = sts.get_caller_identity()["Account"]
        except botocore.exceptions.ClientError:  # pragma: no cover - network edge
            account_id = "YOUR_ACCOUNT_ID"

        actions = """
            s3:PutObject s3:GetObject s3:ListBucket s3:DeleteObject
            cloudfront:CreateInvalidation cloudfront:GetInvalidation
        """.split()
        resources = [
            f"arn:aws:s3:::{self.config.bucket}",
            f"arn:aws:s3:::{self.config.bucket}/*",
            f"arn:aws:cloudfront::{account_id}:distribution/{self.config.cloudfront}",
        ]
        statement = {"Effect": "Allow", "Action": actions, "Resource": resources}
        policy = {"Version": "2012-10-17", "Statement": [statement]}
        return json.dumps(policy, indent=2)
