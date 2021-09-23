# Blob storage server in Python

## Installing

1. Install Python 3.9 and `poetry`
2. Run `poetry install` and `poetry shell` on this project

## Running in debug mode

```sh
uvicorn blob_storage.app:app --host 127.0.0.1 --port 8108 --reload --reload-dir blob_storage/
```
