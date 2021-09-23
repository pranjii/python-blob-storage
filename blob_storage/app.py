import hashlib
from typing import AsyncContextManager, AsyncIterator, Optional, Protocol
from contextlib import asynccontextmanager

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


storage = MemoryStorage()
app = App(storage).asgi()
