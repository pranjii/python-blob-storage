import tempfile
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from blob_storage.app import App, FileStorage


@pytest.fixture
def client():
    KB = 1024
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(Path(temp_dir), chunk_size=32*KB)
        yield TestClient(App(storage).asgi())


def test_happy_path(client: TestClient):
    upload_resp = client.post("/upload", data=b"Hello, world!")
    assert upload_resp.status_code == 201

    file_hash = upload_resp.text

    download_resp = client.get("/download/{}".format(file_hash))
    assert download_resp.status_code == 200
    assert download_resp.content == b"Hello, world!"

    delete_resp = client.delete("/delete/{}".format(file_hash))
    assert delete_resp.status_code == 200


def test_uploading_existing_file(client: TestClient):
    client.post("/upload", data=b"Test data")
    assert client.post("/upload", data=b"Test data").status_code == 200


def test_downloading_unknown_file(client: TestClient):
    assert client.get("/download/abcdef01234").status_code == 404


def test_downloading_deleted_file(client: TestClient):
    file_hash = client.post("/upload", data=b"Hello, world!").text
    client.delete("/delete/{}".format(file_hash))
    assert client.get("/download/{}".format(file_hash)).status_code == 404


def test_deleting_unknown_file(client: TestClient):
    assert client.delete("/delete/abcdef01234").status_code == 404
