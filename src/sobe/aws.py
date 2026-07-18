"""Everything related to AWS. In the future, we may support other cloud providers."""

import datetime
import json
import pathlib
import time

import boto3
import botocore.exceptions

from sobe.config import Target


class AWS:
    def __init__(self, target: Target) -> None:
        self.target = target
        self._session = boto3.Session(**self.target.aws_session)
        self._s3_resource = self._session.resource("s3", **self.target.aws_service)
        self._bucket = self._s3_resource.Bucket(self.target.storage.bucket)  # type: ignore[attr-defined]
        self._cloudfront = None
        if self.target.cache is not None:
            self._cloudfront = self._session.client("cloudfront", **self.target.aws_service)

    def upload(self, prefix: str, local_path: pathlib.Path, remote_name: str = "", *, content_type: str = "") -> None:
        """Upload a file."""
        extra_args = {"ContentType": content_type or guess_content_type(local_path)}
        if not remote_name:
            remote_name = local_path.name
        self._bucket.upload_file(str(local_path), f"{prefix}{remote_name}", ExtraArgs=extra_args)

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
        """Create and wait for a full-path CloudFront invalidation. Iterates until completion.

        Only valid on a target with a cache; the caller checks before dispatching here.
        """
        assert self.target.cache is not None and self._cloudfront is not None
        ref = datetime.datetime.now().astimezone().isoformat()
        batch = {"Paths": {"Quantity": 1, "Items": ["/*"]}, "CallerReference": ref}
        distribution = self.target.cache.distribution
        response = self._cloudfront.create_invalidation(DistributionId=distribution, InvalidationBatch=batch)
        invalidation = response["Invalidation"]["Id"]
        status = "Created"
        while status != "Completed":
            yield status
            time.sleep(3)
            response = self._cloudfront.get_invalidation(DistributionId=distribution, Id=invalidation)
            status = response["Invalidation"]["Status"]

    def generate_needed_permissions(self) -> str:
        """Return the minimal IAM policy required by the tool for this target."""
        bucket = self.target.storage.bucket
        statements = [
            {
                "Effect": "Allow",
                "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket", "s3:DeleteObject"],
                "Resource": [f"arn:aws:s3:::{bucket}", f"arn:aws:s3:::{bucket}/*"],
            }
        ]
        if self.target.cache is not None:
            try:
                sts = self._session.client("sts", **self.target.aws_service)
                account_id = sts.get_caller_identity()["Account"]
            except (botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError):
                account_id = "*"
            statements.append(
                {
                    "Effect": "Allow",
                    "Action": ["cloudfront:CreateInvalidation", "cloudfront:GetInvalidation"],
                    "Resource": f"arn:aws:cloudfront::{account_id}:distribution/{self.target.cache.distribution}",
                }
            )
        policy = {"Version": "2012-10-17", "Statement": statements}
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
