import os
from pathlib import Path

from blob_storage.base_app import App
from blob_storage.file_storage import FileStorage


base_dir = os.environ.get("BLOB_DIR", "./store")


KB = 1024
storage = FileStorage(Path(base_dir), chunk_size=32*KB)
app = App(storage).asgi()
