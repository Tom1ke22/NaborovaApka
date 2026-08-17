import os
from abc import ABC, abstractmethod

from app.core.config import settings


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, data: bytes, filename: str) -> str:
        """Ulož súbor, vráť storage_path ktorý sa uloží do DB."""

    @abstractmethod
    async def generate_signed_url(self, storage_path: str) -> str | None:
        """Vráť dočasný download URL, alebo None ak súbor servujeme cez naše API."""


class LocalStorage(StorageBackend):
    _base_dir = "/app/uploads/cvs"

    async def save(self, data: bytes, filename: str) -> str:
        os.makedirs(self._base_dir, exist_ok=True)
        path = f"{self._base_dir}/{filename}"
        with open(path, "wb") as f:
            f.write(data)
        return path

    async def generate_signed_url(self, storage_path: str) -> str | None:
        # Lokálne súbory servujeme cez /cv/download endpoint
        return None


class GCSStorage(StorageBackend):
    def __init__(self) -> None:
        from google.cloud import storage as gcs  # type: ignore[import]
        self._client = gcs.Client()
        self._bucket = self._client.bucket(settings.gcs_bucket_name)

    async def save(self, data: bytes, filename: str) -> str:
        object_name = f"cvs/{filename}"
        blob = self._bucket.blob(object_name)
        blob.upload_from_string(data, content_type="application/octet-stream")
        return object_name

    async def generate_signed_url(self, storage_path: str) -> str | None:
        import datetime
        blob = self._bucket.blob(storage_path)
        return blob.generate_signed_url(
            expiration=datetime.timedelta(hours=1),
            method="GET",
        )


def get_storage() -> StorageBackend:
    if settings.storage_backend == "gcs":
        return GCSStorage()
    return LocalStorage()
