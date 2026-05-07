import os
import asyncio

from io import BytesIO
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from loguru import logger
from minio import Minio

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)


class AsyncMinioClient:
    def __init__(
        self,
        executor: ThreadPoolExecutor,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: Optional[bool] = None,
    ):
        self.executor = executor

        self.endpoint = endpoint or os.getenv("MINIO_ENDPOINT")
        self.access_key = access_key or os.getenv("MINIO_ACCESS_KEY")
        self.secret_key = secret_key or os.getenv("MINIO_SECRET_KEY")

        secure_env = os.getenv("MINIO_SECURE", "false").lower()
        self.secure = secure if secure is not None else secure_env == "true"

        if not all([self.endpoint, self.access_key, self.secret_key]):
            raise ValueError("Missing MinIO configuration")

        self.client = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

        logger.info(
            f"MinIO initialized | endpoint={self.endpoint}"
        )

    # ==========================================================
    # INTERNAL EXECUTOR WRAPPER
    # ==========================================================

    async def _run(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(
            self.executor,
            lambda: func(*args, **kwargs)
        )

    # ==========================================================
    # CREATE BUCKET
    # ==========================================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def create_bucket(self, bucket_name: str) -> bool:
        try:
            exists = await self.bucket_exists(bucket_name)

            if exists:
                logger.info(f"Bucket exists: {bucket_name}")
                return True

            await self._run(
                self.client.make_bucket,
                bucket_name,
            )

            logger.info(f"Created bucket: {bucket_name}")
            return True

        except Exception:
            logger.exception(
                f"Failed creating bucket: {bucket_name}"
            )
            raise

    # ==========================================================
    # CHECK BUCKET
    # ==========================================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def bucket_exists(self, bucket_name: str) -> bool:
        try:
            exists = await self._run(
                self.client.bucket_exists,
                bucket_name,
            )

            return exists

        except Exception:
            logger.exception(
                f"Failed checking bucket: {bucket_name}"
            )
            raise

    # ==========================================================
    # CREATE PATH
    # ==========================================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def create_path(
        self,
        bucket_name: str,
        path: str,
    ) -> bool:
        try:
            if not path.endswith("/"):
                path += "/"

            await self._run(
                self.client.put_object,
                bucket_name,
                path,
                BytesIO(b""),
                0,
            )

            logger.info(
                f"Created path: {bucket_name}/{path}"
            )

            return True

        except Exception:
            logger.exception(
                f"Failed creating path: {bucket_name}/{path}"
            )
            raise

    # ==========================================================
    # GET FILE COUNT
    # ==========================================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def get_file_count(
        self,
        bucket_name: str,
        prefix: Optional[str] = None,
    ) -> int:
        try:
            objects = await self._run(
                lambda: list(
                    self.client.list_objects(
                        bucket_name,
                        prefix=prefix,
                        recursive=True,
                    )
                )
            )

            return len(objects)

        except Exception:
            logger.exception(
                f"Failed getting file count"
            )
            raise

    # ==========================================================
    # UPLOAD FILE
    # ==========================================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        file_path: str,
        content_type: str = "application/octet-stream",
    ) -> bool:
        try:
            await self._run(
                self.client.fput_object,
                bucket_name,
                object_name,
                file_path,
                content_type=content_type,
            )

            logger.info(
                f"Uploaded file: {object_name}"
            )

            return True

        except Exception:
            logger.exception(
                f"Failed uploading file: {object_name}"
            )
            raise

    # ==========================================================
    # DELETE FILE
    # ==========================================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def delete_file(
        self,
        bucket_name: str,
        object_name: str,
    ) -> bool:
        try:
            await self._run(
                self.client.remove_object,
                bucket_name,
                object_name,
            )

            logger.info(
                f"Deleted file: {object_name}"
            )

            return True

        except Exception:
            logger.exception(
                f"Failed deleting file: {object_name}"
            )
            raise