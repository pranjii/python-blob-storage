import asyncio
import hashlib
import os
import shutil
from pathlib import Path
from typing import AsyncIterator, Optional, cast

import aiofiles
from aiofiles.tempfile import NamedTemporaryFile
from aiofiles.threadpool.binary import AsyncBufferedIOBase


__all__ = ("FileStorage",)

Stream = AsyncIterator[bytes]


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
        :param base_path: Path where files will be stored by their hash
        :param chunk_size: How long to make the `bytes` chunks returned by `find`
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
