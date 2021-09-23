import pytest
from starlette.testclient import TestClient

from blob_storage.app import App
from test.memory_storage import MemoryStorage


@pytest.fixture
def client():
    storage = MemoryStorage()
    return TestClient(App(storage).asgi())


def test_initial_app_has_no_files(client: TestClient):
    resp = client.get("download/abcdef01234")
    assert resp.status_code == 404


def test_uploading_new_file_returns_201(client: TestClient):
    resp = client.post("upload", data=b"Test file")
    assert resp.status_code == 201


def test_uploading_existing_file_returns_200(client: TestClient):
    client.post("upload", data=b"Test file")

    resp = client.post("upload", data=b"Test file")
    assert resp.status_code == 200


def test_file_can_be_downloaded_after_uploading_it(client: TestClient):
    upload_resp = client.post("upload", data=b"Test file")
    file_hash = upload_resp.text

    download_resp = client.get("download/{}".format(file_hash))
    assert download_resp.status_code == 200
    assert download_resp.content == b"Test file"


def test_existing_file_can_be_deleted(client: TestClient):
    upload_resp = client.post("upload", data=b"Test file")
    file_hash = upload_resp.text

    delete_resp = client.delete("delete/{}".format(file_hash))
    assert delete_resp.status_code == 200


def test_missing_file_cannot_be_deleted(client: TestClient):
    resp = client.delete("delete/abcdef01234")
    assert resp.status_code == 404


def test_file_cannot_be_deleted_twice(client: TestClient):
    upload_resp = client.post("upload", data=b"Test file")
    file_hash = upload_resp.text

    client.delete("delete/{}".format(file_hash))
    delete_resp = client.delete("delete/{}".format(file_hash))
    assert delete_resp.status_code == 404


def test_file_cannot_be_downloaded_after_deletion(client: TestClient):
    upload_resp = client.post("upload", data=b"Test file")
    file_hash = upload_resp.text

    client.delete("delete/{}".format(file_hash))

    download_resp = client.get("download/{}".format(file_hash))
    assert download_resp.status_code == 404
