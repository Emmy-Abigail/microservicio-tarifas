import json
from functools import lru_cache
from pathlib import Path
from typing import Any


# Copia solo para cálculos de Python. La fuente oficial es MySQL (migración
# MigrateToV3Schema del backend PHP); una prueba verifica sus totales.
DATA_FILE = Path(__file__).with_name("geography.json")


@lru_cache(maxsize=1)
def _dataset() -> dict[str, dict[Any, dict[str, Any]]]:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {
        "zonas": {zone["id"]: zone for zone in data["zonas"]},
        "sedes": {sede["id"]: sede for sede in data["sedes"]},
        "distritos": {district["ubigeo"]: district for district in data["distritos"]},
    }


def get_zone(zone_id: int) -> dict[str, Any] | None:
    return _dataset()["zonas"].get(zone_id)


def get_sede(sede_id: int) -> dict[str, Any] | None:
    return _dataset()["sedes"].get(sede_id)


def get_district(ubigeo: str) -> dict[str, Any] | None:
    return _dataset()["distritos"].get(ubigeo)


def list_sedes() -> list[dict[str, Any]]:
    return list(_dataset()["sedes"].values())


def list_districts() -> list[dict[str, Any]]:
    return list(_dataset()["distritos"].values())
