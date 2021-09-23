import tempfile
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from blob_storage.base_app import App
from blob_storage.file_storage import FileStorage


@pytest.fixture
def client():
    KB = 1024
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(Path(temp_dir), chunk_size=32*KB)
        yield TestClient(App(storage).asgi())


def test_happy_path(client: TestClient):
    upload_resp = client.post("/", data=b"Hello, world!")
    assert upload_resp.status_code == 201

    file_hash = upload_resp.text

    download_resp = client.get(file_hash)
    assert download_resp.status_code == 200
    assert download_resp.content == b"Hello, world!"

    delete_resp = client.delete(file_hash)
    assert delete_resp.status_code == 200


def test_uploading_existing_file(client: TestClient):
    client.post("/", data=b"Test data")
    assert client.post("/", data=b"Test data").status_code == 200


def test_downloading_unknown_file(client: TestClient):
    assert client.get("/abcdef01234").status_code == 404


def test_downloading_deleted_file(client: TestClient):
    file_hash = client.post("/", data=b"Hello, world!").text
    client.delete(file_hash)
    assert client.get(file_hash).status_code == 404


def test_deleting_unknown_file(client: TestClient):
    assert client.delete("/abcdef01234").status_code == 404
