import logging
from collections.abc import Awaitable, Callable
from traceback import extract_tb

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.api.assignments import router as assignments_router
from app.schemas.assignments import ErrorResponse, InternalErrorResponse


logger = logging.getLogger(__name__)

app = FastAPI(
    title="Asignación de lotes y optimizacion de rutas",
    version="0.1.0",
    responses={500: {"model": InternalErrorResponse, "description": "Error interno inesperado."}},
)
app.include_router(assignments_router)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = "; ".join(
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
        for error in exc.errors()
    )
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(detalle=details).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(detalle=str(exc.detail)).model_dump(),
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Registrar ubicaciones de la traza sin mensajes, código fuente ni variables
    # locales: cualquiera de ellos podría contener claves o datos de la solicitud.
    trace = " -> ".join(
        f"{frame.filename}:{frame.lineno} ({frame.name})"
        for frame in extract_tb(exc.__traceback__)
    )
    logger.error("Error inesperado (%s). Traza: %s", type(exc).__name__, trace)
    return JSONResponse(status_code=500, content=InternalErrorResponse().model_dump())


@app.middleware("http")
async def contain_unexpected_errors(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    try:
        return await call_next(request)
    except Exception as exc:
        # Starlette relanza los errores de su manejador 500 al servidor ASGI.
        # Capturarlos aquí evita que el servidor registre su mensaje sin filtrar.
        return await unexpected_error_handler(request, exc)
