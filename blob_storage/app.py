import hashlib
from typing import AsyncContextManager, AsyncIterator, Optional, Protocol
from contextlib import asynccontextmanager

from starlette import status
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.routing import Route


from typing import Optional


Stream = AsyncIterator[bytes]


class MemoryStorage:
    def __init__(self):
        self._files: dict[str, bytes] = {}

    @asynccontextmanager
    async def find(self, key: str) -> AsyncIterator[Optional[Stream]]:
        """
        Async context manager that provides an async iterator of `bytes` chunks
        and closes all opened resources when the `async with` block ends.
        """
        content = self._files.get(key)
        if content is None:
            yield None
            return
        content_ = content  # microsoft/pyright/issues/599

        async def _find() -> AsyncIterator[bytes]:
            yield content_
        yield _find()

    async def upload(self, stream: Stream) -> tuple[bool, str]:
        """
        :return: (file already exists, hash digest)
        """
        h = hashlib.sha512()

        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
            h.update(chunk)

        file_hash = h.hexdigest()
        if file_hash in self._files:
            return True, file_hash

        self._files[file_hash] = b"".join(chunks)
        return False, file_hash

    async def delete(self, key: str) -> None:
        """
        :raises: KeyError
        """
        self._files.pop(key)


class Storage(Protocol):
    def find(self, /, key: str) -> AsyncContextManager[Optional[Stream]]:
        """
        Async context manager that provides an async iterator of `bytes` chunks
        and closes all opened resources when the `async with` block ends.
        """

    async def upload(self, /, stream: Stream) -> tuple[bool, str]:
        """
        :return: (file already exists, hash digest)
        """

    async def delete(self, /, key: str) -> None:
        """
        :raises: KeyError
        """


class App:
    def __init__(self, storage: Storage):
        self._storage = storage

    async def upload_file(self, request: Request) -> Response:
        exists, file_hash = await self._storage.upload(request.stream())
        status_code = status.HTTP_200_OK if exists else status.HTTP_201_CREATED
        return Response(file_hash, status_code)

    async def download_file(self, request: Request) -> Response:
        file_hash = request.path_params["hash"]

        async with self._storage.find(file_hash) as contents:
            if contents is None:
                return Response("File not found", status_code=status.HTTP_404_NOT_FOUND)

            return StreamingResponse(contents)

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


storage = MemoryStorage()
app = App(storage).asgi()
