import asyncio
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoredFile:
    path: str              # rovnaký tvar ako `applicants.cv_storage_path`
    modified_at: datetime  # UTC


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, data: bytes, filename: str) -> str:
        """Ulož súbor, vráť storage_path ktorý sa uloží do DB."""

    @abstractmethod
    async def load(self, storage_path: str) -> bytes | None:
        """Načítaj súbor späť. None ak neexistuje alebo sa nedá prečítať.

        Potrebuje to AI hodnotenie (text z CV) aj stiahnutie CV adminom.
        """

    @abstractmethod
    async def exists(self, storage_path: str) -> bool:
        """Je súbor v úložisku? Admin tak dostane jasnú hlášku namiesto „skúste znova"."""

    @abstractmethod
    async def delete(self, storage_path: str) -> None:
        """Zmaž súbor. Neexistujúci súbor nie je chyba (výmaz je idempotentný)."""

    @abstractmethod
    async def list_files(self) -> list[StoredFile]:
        """Všetky uložené CV — pre úklid súborov bez uchádzača."""

    # Zámerne tu nie je podpísaný URL na stiahnutie. CV ide adminovi vždy cez
    # autentifikovaný endpoint /admin/applicants/{id}/cv/download — podpísaný
    # URL by stiahol CV hocikto, kto ho získa (logy, história, preposlaný link).


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

    async def exists(self, storage_path: str) -> bool:
        return os.path.isfile(storage_path)

    async def delete(self, storage_path: str) -> None:
        try:
            os.remove(storage_path)
        except FileNotFoundError:
            pass

    async def list_files(self) -> list[StoredFile]:
        if not os.path.isdir(self._base_dir):
            return []
        files = []
        with os.scandir(self._base_dir) as entries:
            for entry in entries:
                if entry.is_file():
                    files.append(StoredFile(
                        path=f"{self._base_dir}/{entry.name}",
                        modified_at=datetime.fromtimestamp(entry.stat().st_mtime, timezone.utc),
                    ))
        return files


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

    # Knižnica GCS je synchrónna, všetko ide mimo event loop.

    async def exists(self, storage_path: str) -> bool:
        return await asyncio.to_thread(self._bucket.blob(storage_path).exists)

    async def delete(self, storage_path: str) -> None:
        from google.api_core.exceptions import NotFound  # type: ignore[import]

        def _delete() -> None:
            try:
                self._bucket.blob(storage_path).delete()
            except NotFound:
                pass

        await asyncio.to_thread(_delete)

    async def list_files(self) -> list[StoredFile]:
        def _list() -> list[StoredFile]:
            return [
                StoredFile(path=blob.name, modified_at=blob.updated)
                for blob in self._client.list_blobs(self._bucket, prefix="cvs/")
            ]

        return await asyncio.to_thread(_list)


def get_storage() -> StorageBackend:
    if settings.storage_backend == "gcs":
        return GCSStorage()
    return LocalStorage()
