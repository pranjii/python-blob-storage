# Blob storage server in Python

This application provides an HTTP API to download, upload or delete files.

## Installing

1. Install Python 3.9 and `poetry`
2. Run `poetry install` and `poetry shell` on this project

## Running in debug mode

```sh
uvicorn blob_storage.app:app --host 127.0.0.1 --port 8108 --reload --reload-dir blob_storage/
```

## Storage path

By default, the files will be stored in a `store` folder in the current directory.
To change this, specify a directory in the `BLOB_DIR` environment variable.

## Testing

```sh
python -m pytest
```

## Documentation

OpenAPI schema is stored in `openapi.yaml`
