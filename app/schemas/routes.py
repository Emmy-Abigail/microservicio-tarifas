from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


PositiveId = Annotated[int, Field(gt=0, strict=True)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Stop(InputModel):
    id_paquete: PositiveId
    ubigeo_destino: Annotated[str, Field(pattern=r"^[0-9]{6}$", strict=True)]


class RouteRequest(InputModel):
    id_sede: PositiveId
    paradas: Annotated[list[Stop], Field(min_length=1, max_length=20)]

    @model_validator(mode="after")
    def validate_unique_package_ids(self) -> Self:
        package_ids = [stop.id_paquete for stop in self.paradas]
        if len(package_ids) != len(set(package_ids)):
            raise ValueError("Los IDs de paquetes no pueden estar duplicados.")
        return self


class RouteResponse(BaseModel):
    orden: list[PositiveId]
    algoritmo: Literal["greedy-nearest-neighbor"] = "greedy-nearest-neighbor"
