from fastapi import APIRouter, Depends, HTTPException

from app.api.decimal_json import DecimalJSONRoute
from app.api.dependencies import require_api_key
from app.schemas.assignments import AssignmentRequest, AssignmentResponse, ErrorResponse
from app.services.batch_assignment import NoCompatibleVehicleError, evaluate_assignment


router = APIRouter(
    prefix="/api/v1/batch-assignments",
    tags=["Asignación de lotes"],
    route_class=DecimalJSONRoute,
)


@router.post(
    "/evaluate",
    response_model=AssignmentResponse,
    dependencies=[Depends(require_api_key)],
    responses={
        401: {"model": ErrorResponse, "description": "Clave interna ausente o incorrecta."},
        422: {"model": ErrorResponse, "description": "Datos inválidos o vehículo incompatible."},
    },
)
def evaluate(request: AssignmentRequest) -> AssignmentResponse:
    try:
        return evaluate_assignment(request)
    except NoCompatibleVehicleError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
