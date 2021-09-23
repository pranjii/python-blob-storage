import hashlib

from starlette import status
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route


class App:
    def __init__(self):
        self._storage: dict[str, bytes] = {}

    async def upload_file(self, request: Request) -> Response:
        h = hashlib.sha512()

        chunks = []
        async for chunk in request.stream():
            chunks.append(chunk)
            h.update(chunk)

        file_hash = h.hexdigest()
        if file_hash in self._storage:
            return Response(file_hash, status_code=status.HTTP_200_OK)

        self._storage[file_hash] = b"".join(chunks)
        return Response(file_hash, status_code=status.HTTP_201_CREATED)

    async def download_file(self, request: Request) -> Response:
        file_hash = request.path_params["hash"]

        file_contents = self._storage.get(file_hash)
        if file_contents is None:
            return Response("File not found", status_code=status.HTTP_404_NOT_FOUND)

        return Response(file_contents)

    async def delete_file(self, request: Request) -> Response:
        file_hash = request.path_params["hash"]

        try:
            self._storage.pop(file_hash)
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


app = App().asgi()
