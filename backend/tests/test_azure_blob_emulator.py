"""Runs the real AzureBlobStorage code against the Azurite emulator. Skipped unless AZURITE_CONNECTION_STRING is set.
(Azurite is Microsoft's official local Azure Storage emulator; this does not touch a real Azure account.)"""
import os

import pytest

from app.services.storage import AzureBlobStorage, StorageError

CONN = os.environ.get("AZURITE_CONNECTION_STRING")
pytestmark = pytest.mark.skipif(not CONN, reason="AZURITE_CONNECTION_STRING not set")
PNG = b"\x89PNG\r\n\x1a\n" + b"\x01" * 50


@pytest.fixture()
def store():
    from azure.storage.blob import BlobServiceClient
    svc = BlobServiceClient.from_connection_string(CONN)
    name = "test-posters"
    try:
        svc.create_container(name)
    except Exception:
        pass
    return AzureBlobStorage(CONN, name)


def test_save_read_delete_roundtrip(store):
    key = store.save(PNG, "image/png")
    assert key.endswith(".png")
    assert store.read(key) == PNG
    store.delete(key)
    with pytest.raises(StorageError):
        store.read(key)


def test_missing_container_is_reported_not_faked():
    bad = AzureBlobStorage(CONN, "container-that-does-not-exist")
    with pytest.raises(StorageError):
        bad.save(PNG, "image/png")


def test_unreachable_storage_is_reported_not_faked():
    dead = AzureBlobStorage("DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=ZmFrZQ==;BlobEndpoint=http://127.0.0.1:1/devstoreaccount1;", "x", retry_total=0, connection_timeout=2)
    with pytest.raises(StorageError):
        dead.save(PNG, "image/png")
