"""Everything related to AWS. In the future, we may support other cloud providers."""

import datetime
import json
import pathlib
import time

import boto3
import botocore.exceptions

from sobe.config import AWSConfig


class AWS:
    def __init__(self, config: AWSConfig) -> None:
        self.config = config
        self._session = boto3.Session(**self.config.session)
        self._s3_resource = self._session.resource("s3", **self.config.service)
        self._bucket = self._s3_resource.Bucket(self.config.bucket)  # type: ignore[attr-defined]
        self._cloudfront = self._session.client("cloudfront", **self.config.service)

    def upload(self, prefix: str, local_path: pathlib.Path, *, content_type: str | None = None) -> None:
        """Upload a file."""
        extra_args = {"ContentType": content_type or guess_content_type(local_path)}
        self._bucket.upload_file(str(local_path), f"{prefix}{local_path.name}", ExtraArgs=extra_args)

    def delete(self, prefix: str, remote_filename: str) -> bool:
        """Delete a file, if it exists. Returns whether it did."""
        obj = self._bucket.Object(f"{prefix}{remote_filename}")
        try:
            obj.load()
            obj.delete()
            return True
        except botocore.exceptions.ClientError as e:
            if e.response.get("Error", {}).get("Code") == "404":
                return False
            raise

    def list(self, prefix: str) -> list[str]:
        """Return a list of object filenames in the given prefix."""
        objects = self._bucket.objects.filter(Prefix=prefix)
        pos1 = len(prefix)
        results = set()
        for obj in objects:
            if len(obj.key) == pos1:
                continue  # skip the prefix entry itself
            pos2 = obj.key.find("/", pos1)
            if pos2 == -1:
                results.add(obj.key[pos1:])
            else:
                results.add(obj.key[pos1:pos2] + "/")
        return sorted(results)

    def invalidate_cache(self):
        """Create and wait for a full-path CloudFront invalidation. Iterates until completion."""
        ref = datetime.datetime.now().astimezone().isoformat()
        batch = {"Paths": {"Quantity": 1, "Items": ["/*"]}, "CallerReference": ref}
        distribution = self.config.cloudfront
        response = self._cloudfront.create_invalidation(DistributionId=distribution, InvalidationBatch=batch)
        invalidation = response["Invalidation"]["Id"]
        status = "Created"
        while status != "Completed":
            yield status
            time.sleep(3)
            response = self._cloudfront.get_invalidation(DistributionId=distribution, Id=invalidation)
            status = response["Invalidation"]["Status"]

    def generate_needed_permissions(self) -> str:
        """Return the minimal IAM policy statement required by the tool."""
        try:
            sts = self._session.client("sts", **self.config.service)
            account_id = sts.get_caller_identity()["Account"]
        except botocore.exceptions.ClientError:
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


def guess_content_type(path: pathlib.Path) -> str:
    """Return a guessed content type for the given file."""
    import mimetypes

    # Guess based on filename using standard library
    guess, _ = mimetypes.guess_type(path.name)
    if guess:
        return guess

    import puremagic

    # Guess based on file content using puremagic
    for result in puremagic.magic_file(path):  # result is ordered by confidence
        guess = getattr(result, "mime_type", None)
        if guess:
            return guess

    # Fallback
    return "application/octet-stream"
