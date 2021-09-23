from pathlib import Path

from blob_storage.base_app import App
from blob_storage.file_storage import FileStorage


KB = 1024
storage = FileStorage(Path("./store"), chunk_size=32*KB)
app = App(storage).asgi()
