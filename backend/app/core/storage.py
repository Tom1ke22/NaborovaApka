import logging
import os
from abc import ABC, abstractmethod

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, data: bytes, filename: str) -> str:
        """Ulož súbor, vráť storage_path ktorý sa uloží do DB."""

    @abstractmethod
    async def load(self, storage_path: str) -> bytes | None:
        """Načítaj súbor späť. None ak neexistuje alebo sa nedá prečítať.

        Potrebuje to AI hodnotenie, ktoré si z uloženého CV vytiahne text.
        """

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

    async def load(self, storage_path: str) -> bytes | None:
        try:
            with open(storage_path, "rb") as f:
                return f.read()
        except OSError:
            logger.warning("CV sa nedá prečítať z disku: %s", storage_path)
            return None

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

    async def load(self, storage_path: str) -> bytes | None:
        import asyncio

        def _download() -> bytes | None:
            blob = self._bucket.blob(storage_path)
            if not blob.exists():
                return None
            return blob.download_as_bytes()

        try:
            # Knižnica GCS je synchrónna, preto ju pustíme mimo event loop.
            return await asyncio.to_thread(_download)
        except Exception:  # noqa: BLE001
            logger.warning("CV sa nedá stiahnuť z GCS: %s", storage_path, exc_info=True)
            return None

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
