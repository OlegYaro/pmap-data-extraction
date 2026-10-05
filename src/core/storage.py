import asyncio
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from core.config import settings


class RawArchive:
    """Untouched source files in S3.

    Credentials are not passed here: on AWS boto3 takes them from the IAM role of the server.
    """

    def __init__(self) -> None:
        self._client = boto3.client("s3", region_name=settings.S3_REGION)

    async def exists(self, key: str) -> bool:
        """Whether S3 already has a file with this key."""
        try:
            await asyncio.to_thread(
                self._client.head_object, Bucket=settings.S3_BUCKET_RAW, Key=key
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
                return False
            raise
        return True

    async def put_file(self, key: str, path: Path) -> None:
        """Upload a file."""
        await asyncio.to_thread(self._client.upload_file, str(path), settings.S3_BUCKET_RAW, key)


archive = RawArchive()
