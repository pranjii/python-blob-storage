from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route


async def not_implemented(request: Request) -> Response:
    return JSONResponse({"error": "Not implemented"}, status_code=501)


app = Starlette(routes=[Route("/", not_implemented)])
