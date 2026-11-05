import os
import tempfile

# Must be set BEFORE the app is imported so tests never touch a real/dev database.
_tmp = tempfile.mkdtemp(prefix="eventvault_test_")
_remote = os.environ.get("TEST_DATABASE_URL")
if _remote:
    # SAFETY: the suite DROPS ALL TABLES, so only allow databases whose name says "test".
    if "test" not in _remote.lower().rsplit("/", 1)[-1].split("?")[0]:
        raise RuntimeError("TEST_DATABASE_URL database name must contain 'test' (the tests wipe the database).")
os.environ["DATABASE_URL"] = _remote or f"sqlite:///{_tmp}/test.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["ENVIRONMENT"] = "test"
os.environ["STORAGE_BACKEND"] = "local"

import shutil

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.db_objects import init_db
from app.main import app
from app.services import storage


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    with engine.begin() as c:
        for obj in ("VIEW IF EXISTS vw_event_stats",):
            c.exec_driver_sql(f"DROP {obj}")
    init_db()
    shutil.rmtree(os.environ["UPLOAD_DIR"], ignore_errors=True)
    storage.reset_storage()
    yield


@pytest.fixture()
def client():
    return TestClient(app)
