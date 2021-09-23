from typing import Callable, Mapping, Awaitable, Literal

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Scope, Receive, Send


Handler = Callable[[Request], Awaitable[Response]]

Method = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]


class MethodDispatch:
    """
    ASGI application do dispatch a request based on its method (HTTP verb)
    """

    def __init__(self, handlers: Mapping[Method, Handler]):
        self._handlers: Mapping[str, Handler] = handlers

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        req = Request(scope, receive, send)
        method = req.method.upper()
        handler = self._handlers.get(method)
        if handler is None:
            await Response(status_code=405)(scope, receive, send)
            return
        await (await handler(req))(scope, receive, send)
