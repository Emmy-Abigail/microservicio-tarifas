from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


PositiveId = Annotated[int, Field(gt=0, strict=True)]
PositiveDecimal = Annotated[Decimal, Field(gt=0, allow_inf_nan=False)]
NonNegativeDecimal = Annotated[Decimal, Field(ge=0, allow_inf_nan=False)]
Dimension = Annotated[Decimal, Field(ge=10, le=150, allow_inf_nan=False)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Package(InputModel):
    peso_kg: Annotated[Decimal, Field(ge=Decimal("0.1"), le=50, allow_inf_nan=False)]
    largo_cm: Dimension
    ancho_cm: Dimension
    alto_cm: Dimension


class Vehicle(InputModel):
    id: PositiveId
    nivel: Annotated[int, Field(gt=0, strict=True)]
    peso_max_total_kg: PositiveDecimal
    lado_max_cm: PositiveDecimal
    max_paquetes: Annotated[int, Field(ge=1, le=20, strict=True)]


class CandidateBatch(InputModel):
    id: PositiveId
    id_tipo_vehiculo: PositiveId
    cantidad_paquetes: Annotated[int, Field(ge=0, strict=True)]
    peso_total_kg: NonNegativeDecimal
    created_at: AwareDatetime

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_date_format(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
        raise ValueError("created_at debe ser una fecha ISO 8601 con zona horaria.")


class AssignmentRequest(InputModel):
    id_sede: PositiveId
    ubigeo_destino: Annotated[str, Field(pattern=r"^[0-9]{6}$", strict=True)]
    paquete: Package
    vehiculos: list[Vehicle]
    lotes_candidatos: list[CandidateBatch]

    @model_validator(mode="after")
    def validate_ids_and_references(self) -> Self:
        vehicle_ids = [vehicle.id for vehicle in self.vehiculos]
        if len(vehicle_ids) != len(set(vehicle_ids)):
            raise ValueError("Los IDs de vehículos no pueden estar duplicados.")
        batch_ids = [batch.id for batch in self.lotes_candidatos]
        if len(batch_ids) != len(set(batch_ids)):
            raise ValueError("Los IDs de lotes no pueden estar duplicados.")
        known_vehicles = set(vehicle_ids)
        if any(batch.id_tipo_vehiculo not in known_vehicles for batch in self.lotes_candidatos):
            raise ValueError("Hay lotes que hacen referencia a vehículos inexistentes.")
        return self


class UseBatchResponse(BaseModel):
    accion: Literal["USAR_LOTE"] = "USAR_LOTE"
    id_tipo_vehiculo: PositiveId
    id_lote: PositiveId


class CreateBatchResponse(BaseModel):
    accion: Literal["CREAR_LOTE"] = "CREAR_LOTE"
    id_tipo_vehiculo: PositiveId
    id_lote: None = None


AssignmentResponse = Annotated[
    UseBatchResponse | CreateBatchResponse, Field(discriminator="accion")
]


class ErrorResponse(BaseModel):
    error: Literal["datos_invalidos"] = "datos_invalidos"
    detalle: str


class InternalErrorResponse(BaseModel):
    error: Literal["error_interno"] = "error_interno"
    detalle: Literal["No se pudo procesar la solicitud."] = "No se pudo procesar la solicitud."
