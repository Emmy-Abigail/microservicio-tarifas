import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


@pytest.fixture
def payload():
    return {
        "id_sede": 3,
        "ubigeo_destino": "150122",
        "paquete": {"peso_kg": 3, "largo_cm": 30, "ancho_cm": 22, "alto_cm": 10},
        "vehiculos": [
            {"id": 1, "nivel": 1, "peso_max_total_kg": 20, "lado_max_cm": 40, "max_paquetes": 20},
            {"id": 2, "nivel": 2, "peso_max_total_kg": 200, "lado_max_cm": 125, "max_paquetes": 20},
            {"id": 3, "nivel": 3, "peso_max_total_kg": 1000, "lado_max_cm": 150, "max_paquetes": 20},
        ],
        "lotes_candidatos": [
            {
                "id": 101,
                "id_tipo_vehiculo": 1,
                "cantidad_paquetes": 12,
                "peso_total_kg": 15,
                "created_at": "2026-10-21T08:00:00-05:00",
            },
            {
                "id": 102,
                "id_tipo_vehiculo": 1,
                "cantidad_paquetes": 5,
                "peso_total_kg": 8,
                "created_at": "2026-10-21T09:00:00-05:00",
            },
        ],
    }


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("API_KEY", "clave-solo-para-pruebas")
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


@pytest.fixture
def auth_headers():
    return {"X-API-Key": "clave-solo-para-pruebas"}
