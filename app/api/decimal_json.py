"""Lectura de JSON con precisión decimal, reutilizable entre routers."""

import json
from collections.abc import Callable, Coroutine
from decimal import Decimal
from typing import Any

from fastapi import Request, Response
from fastapi.routing import APIRoute


class DecimalJSONRequest(Request):
    """Conserva los decimales del JSON antes de la validación de Pydantic."""

    async def json(self) -> Any:
        if not hasattr(self, "_json"):
            # Evitar que un float redondee el valor antes de llegar a Pydantic.
            self._json = json.loads(await self.body(), parse_float=Decimal)
        return self._json


class DecimalJSONRoute(APIRoute):
    """Activa la lectura decimal para los endpoints del router que la utilice."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handle_request = super().get_route_handler()

        async def handle_decimal_request(request: Request) -> Response:
            return await handle_request(DecimalJSONRequest(request.scope, request.receive))

        return handle_decimal_request
