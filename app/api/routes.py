from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import require_api_key
from app.schemas.assignments import ErrorResponse
from app.schemas.routes import RouteRequest, RouteResponse
from app.services.route_optimizer import (
    UnknownDistrictError,
    UnknownSedeError,
    optimize_route,
)


router = APIRouter(prefix="/api/v1", tags=["Optimización de rutas"])


@router.post(
    "/optimize-route",
    response_model=RouteResponse,
    dependencies=[Depends(require_api_key)],
    responses={
        401: {"model": ErrorResponse, "description": "Clave interna ausente o incorrecta."},
        422: {"model": ErrorResponse, "description": "Datos inválidos, sede o distrito inexistente."},
    },
)
def optimize(request: RouteRequest) -> RouteResponse:
    try:
        return optimize_route(request)
    except (UnknownSedeError, UnknownDistrictError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
