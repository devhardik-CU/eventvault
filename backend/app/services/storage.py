"""Poster storage: local disk (development) or Azure Blob Storage (production).
Failures raise StorageError -- we never pretend an upload succeeded."""
import uuid
from pathlib import Path

from ..config import get_settings


class StorageError(Exception):
    pass


ALLOWED = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def detect_image_type(data: bytes) -> str | None:
    """Identify the real file type from its first bytes (don't trust the client's header)."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


class LocalStorage:
    def __init__(self, base_dir: str):
        self.base = Path(base_dir)

    def save(self, data: bytes, content_type: str) -> str:
        key = f"{uuid.uuid4().hex}{ALLOWED[content_type]}"
        try:
            self.base.mkdir(parents=True, exist_ok=True)
            (self.base / key).write_bytes(data)
        except OSError as exc:
            raise StorageError("Could not save file locally.") from exc
        return key

    def read(self, key: str) -> bytes:
        path = (self.base / key).resolve()
        if self.base.resolve() not in path.parents:  # block path traversal
            raise StorageError("Invalid file key.")
        try:
            return path.read_bytes()
        except OSError as exc:
            raise StorageError("File not found.") from exc

    def delete(self, key: str) -> None:
        try:
            (self.base / key).unlink(missing_ok=True)
        except OSError:
            pass


class AzureBlobStorage:
    def __init__(self, connection_string: str, container: str, **client_options):
        from azure.storage.blob import BlobServiceClient  # imported lazily

        self.client = BlobServiceClient.from_connection_string(connection_string, **client_options).get_container_client(container)

    def save(self, data: bytes, content_type: str) -> str:
        from azure.storage.blob import ContentSettings

        key = f"{uuid.uuid4().hex}{ALLOWED[content_type]}"
        try:
            self.client.upload_blob(key, data, content_settings=ContentSettings(content_type=content_type))
        except Exception as exc:
            raise StorageError("Azure Blob upload failed.") from exc
        return key

    def read(self, key: str) -> bytes:
        try:
            return self.client.download_blob(key).readall()
        except Exception as exc:
            raise StorageError("Azure Blob download failed.") from exc

    def delete(self, key: str) -> None:
        try:
            self.client.delete_blob(key)
        except Exception:
            pass


_storage = None


def get_storage():
    global _storage
    if _storage is None:
        s = get_settings()
        if s.storage_backend == "azure":
            _storage = AzureBlobStorage(s.azure_storage_connection_string, s.azure_storage_container)
        else:
            _storage = LocalStorage(s.upload_dir)
    return _storage


def reset_storage() -> None:  # used by tests
    global _storage
    _storage = None
