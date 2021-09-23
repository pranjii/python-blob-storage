from typing import AsyncIterator, Optional, Protocol

from starlette import status
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.routing import Route

from blob_storage.method_dispatch import MethodDispatch


__all__ = ("Storage", "App")

Stream = AsyncIterator[bytes]


class Storage(Protocol):
    async def find(self, key: str, /) -> Optional[Stream]:
        """
        Find a file by key and return an async generator with its contents.

        Returns `None` if the file wasn't found.
        """

    async def upload(self, stream: Stream, /) -> tuple[bool, str]:
        """
        Returns a pair of (file already exists, key)
        """

    async def delete(self, key: str, /) -> None:
        """
        :raises: KeyError if the file wasn't found
        """


class App:
    def __init__(self, storage: Storage):
        self._storage = storage

    async def upload_file(self, request: Request) -> Response:
        exists, file_hash = await self._storage.upload(request.stream())
        status_code = status.HTTP_200_OK if exists else status.HTTP_201_CREATED
        return Response(file_hash, status_code, media_type="text/plain")

    async def download_file(self, request: Request) -> Response:
        file_hash = request.path_params["hash"]

        stream = await self._storage.find(file_hash)

        if stream is None:
            return Response("File not found", status_code=status.HTTP_404_NOT_FOUND)

        return StreamingResponse(stream, media_type="application/octet-stream")

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
            Route("/", self.upload_file, methods=["POST"]),
            Route("/{hash:str}", MethodDispatch({
                "GET": self.download_file,
                "DELETE": self.delete_file,
            })),
        ])
