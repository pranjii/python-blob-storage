import asyncio
import hashlib
import os
import shutil
from pathlib import Path
from typing import AsyncIterator, Optional, Protocol, cast

import aiofiles
from aiofiles.tempfile import NamedTemporaryFile
from aiofiles.threadpool.binary import AsyncBufferedIOBase
from starlette import status
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.routing import Route

Stream = AsyncIterator[bytes]


class Storage(Protocol):
    async def find(self, key: str, /) -> Optional[Stream]:
        """
        Find a binary file I/O object by unique key.

        It's the responsibility of the caller to close it.
        """

    async def upload(self, stream: Stream, /) -> tuple[bool, str]:
        """
        :return: (file already exists, key)
        """

    async def delete(self, key: str, /) -> None:
        """
        :raises: KeyError
        """


async def _stream_file(file: AsyncBufferedIOBase, chunk_size: int) -> Stream:
    while chunk := await file.read(chunk_size):
        yield chunk


async def _move_file(source: Path, destination: Path):
    def sync_move_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source, destination)
    await asyncio.to_thread(sync_move_file)


class FileStorage:
    def __init__(self, base_path: Path, chunk_size: int):
        """
        :base_path: Path where files will be stored by their hash
        :chunk_size: How long to make the `bytes` chunks returned by `find`
        """
        self._base_path = base_path
        self._chunk_size = chunk_size

    async def find(self, file_hash: str) -> Optional[Stream]:
        if len(file_hash) < 3:
            return None

        file_path = self._file_path_from_hash(file_hash)

        if not await asyncio.to_thread(file_path.exists):
            return None

        return self._stream_from_path(file_path)

    async def upload(self, stream: Stream) -> tuple[bool, str]:
        temp_dir = self._base_path / ".temp"
        await asyncio.to_thread(lambda: temp_dir.mkdir(parents=True, exist_ok=True))

        async with NamedTemporaryFile(mode="wb", dir=temp_dir, delete=False) as temp_file:
            temp_file: AsyncBufferedIOBase

            h = hashlib.sha512()
            async for chunk in stream:
                await temp_file.write(chunk)
                h.update(chunk)
            file_hash = h.hexdigest()

            persistent_path = self._file_path_from_hash(file_hash)
            temp_file_name = cast(str, temp_file.name)

            exists = await asyncio.to_thread(persistent_path.exists)
            if exists:
                await asyncio.to_thread(lambda: os.unlink(temp_file_name))
                return True, file_hash

            await temp_file.flush()
            await _move_file(source=Path(temp_file_name), destination=persistent_path)

        return False, file_hash

    async def delete(self, file_hash: str) -> None:
        if len(file_hash) < 3:
            raise KeyError(file_hash)

        file_path = self._file_path_from_hash(file_hash)

        try:
            await asyncio.to_thread(file_path.unlink)
        except FileNotFoundError:
            raise KeyError(file_hash)

    async def _stream_from_path(self, path: Path) -> Stream:
        async with aiofiles.open(path, "rb") as file:
            async for chunk in _stream_file(file, self._chunk_size):
                yield chunk

    def _file_path_from_hash(self, file_hash: str) -> Path:
        return self._base_path / file_hash[:2] / file_hash


class App:
    def __init__(self, storage: Storage):
        self._storage = storage

    async def upload_file(self, request: Request) -> Response:
        exists, file_hash = await self._storage.upload(request.stream())
        status_code = status.HTTP_200_OK if exists else status.HTTP_201_CREATED
        return Response(file_hash, status_code)

    async def download_file(self, request: Request) -> Response:
        file_hash = request.path_params["hash"]

        stream = await self._storage.find(file_hash)

        if stream is None:
            return Response("File not found", status_code=status.HTTP_404_NOT_FOUND)

        return StreamingResponse(stream)

    async def delete_file(self, request: Request) -> Response:
        file_hash = request.path_params["hash"]

        try:
            await self._storage.delete(file_hash)
        except KeyError:
            return Response("File not found", status_code=status.HTTP_404_NOT_FOUND)
        else:
            return Response(status_code=status.HTTP_200_OK)

    def asgi(self) -> Starlette:
        return Starlette(routes=[
            Route("/download/{hash:str}", self.download_file, methods=["GET"]),
            Route("/upload", self.upload_file, methods=["POST"]),
            Route("/delete/{hash:str}", self.delete_file, methods=["DELETE"]),
        ])


KB = 1024
storage = FileStorage(Path("./store"), chunk_size=32*KB)
app = App(storage).asgi()
