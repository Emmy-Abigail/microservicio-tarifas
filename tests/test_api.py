from copy import deepcopy
import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.api import assignments as assignments_api
from app.core.config import Settings, get_settings
from app.main import app


URL = "/api/v1/batch-assignments/evaluate"


def assert_error(response, status_code):
    assert response.status_code == status_code
    body = response.json()
    assert set(body) == {"error", "detalle"}
    assert body["error"] == "datos_invalidos"
    assert isinstance(body["detalle"], str) and body["detalle"]


def test_evaluate_endpoint(client, payload, auth_headers):
    response = client.post(URL, json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"accion": "USAR_LOTE", "id_tipo_vehiculo": 1, "id_lote": 101}


def test_create_batch_response(client, payload, auth_headers):
    payload["lotes_candidatos"] = []
    response = client.post(URL, json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"accion": "CREAR_LOTE", "id_tipo_vehiculo": 1, "id_lote": None}


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "incorrecta"}, {"X-API-Key": ""}])
def test_authentication(client, payload, headers):
    response = client.post(URL, json=payload, headers=headers)
    assert_error(response, 401)
    assert "incorrecta" in response.json()["detalle"]


@pytest.mark.parametrize("configured_key", [None, ""])
def test_missing_server_key_rejects_requests(client, payload, auth_headers, configured_key):
    app.dependency_overrides[get_settings] = lambda: Settings(
        api_key=configured_key, _env_file=None
    )
    try:
        assert_error(client.post(URL, json=payload, headers=auth_headers), 401)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("id_sede",), 0),
        (("id_sede",), True),
        (("id_sede",), 1.5),
        (("ubigeo_destino",), "15012"),
        (("ubigeo_destino",), "1501220"),
        (("ubigeo_destino",), "15012a"),
        (("ubigeo_destino",), "１５０１２２"),
        (("ubigeo_destino",), 150122),
        (("paquete", "peso_kg"), "0.09999"),
        (("paquete", "peso_kg"), "50.00001"),
        (("paquete", "peso_kg"), "NaN"),
        (("paquete", "peso_kg"), "Infinity"),
        (("paquete", "peso_kg"), True),
        (("paquete", "largo_cm"), "9.99"),
        (("paquete", "ancho_cm"), "150.01"),
        (("paquete", "alto_cm"), 0),
        (("vehiculos", 0, "id"), -1),
        (("vehiculos", 0, "nivel"), 0),
        (("vehiculos", 0, "peso_max_total_kg"), 0),
        (("vehiculos", 0, "peso_max_total_kg"), "NaN"),
        (("vehiculos", 0, "lado_max_cm"), -1),
        (("vehiculos", 0, "lado_max_cm"), "Infinity"),
        (("vehiculos", 0, "max_paquetes"), 0),
        (("vehiculos", 0, "max_paquetes"), 21),
        (("vehiculos", 0, "max_paquetes"), True),
        (("lotes_candidatos", 0, "id"), 0),
        (("lotes_candidatos", 0, "id_tipo_vehiculo"), 0),
        (("lotes_candidatos", 0, "id_tipo_vehiculo"), 999),
        (("lotes_candidatos", 0, "cantidad_paquetes"), -1),
        (("lotes_candidatos", 0, "cantidad_paquetes"), 1.5),
        (("lotes_candidatos", 0, "peso_total_kg"), -1),
        (("lotes_candidatos", 0, "peso_total_kg"), "NaN"),
        (("lotes_candidatos", 0, "created_at"), "2026-10-21T08:00:00"),
        (("lotes_candidatos", 0, "created_at"), "2026-10-21"),
        (("lotes_candidatos", 0, "created_at"), "fecha-invalida"),
        (("lotes_candidatos", 0, "created_at"), 1761051600),
        (("lotes_candidatos", 0, "created_at"), "1761051600"),
        (("vehiculos",), None),
        (("lotes_candidatos",), None),
    ],
)
def test_input_validation(client, payload, auth_headers, path, value):
    target = payload
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = value
    assert_error(client.post(URL, json=payload, headers=auth_headers), 422)


@pytest.mark.parametrize("collection", ["vehiculos", "lotes_candidatos"])
def test_duplicate_ids(client, payload, auth_headers, collection):
    payload[collection].append(deepcopy(payload[collection][0]))
    response = client.post(URL, json=payload, headers=auth_headers)
    assert_error(response, 422)
    assert "duplicados" in response.json()["detalle"]


@pytest.mark.parametrize("field", ["id_sede", "ubigeo_destino", "paquete", "vehiculos", "lotes_candidatos"])
def test_required_fields(client, payload, auth_headers, field):
    del payload[field]
    assert_error(client.post(URL, json=payload, headers=auth_headers), 422)


@pytest.mark.parametrize("raw_body", ['{"id_sede":', "null", "[]"])
def test_malformed_or_invalid_body(client, auth_headers, raw_body):
    response = client.post(
        URL, content=raw_body, headers={**auth_headers, "Content-Type": "application/json"}
    )
    assert_error(response, 422)


def test_no_compatible_vehicle_returns_422(client, payload, auth_headers):
    payload["vehiculos"] = []
    payload["lotes_candidatos"] = []
    response = client.post(URL, json=payload, headers=auth_headers)
    assert_error(response, 422)
    assert "Ningún vehículo" in response.json()["detalle"]


def test_decimal_limit_over_http(client, payload, auth_headers):
    payload["paquete"]["peso_kg"] = "0.1"
    payload["vehiculos"][0]["peso_max_total_kg"] = "0.3"
    payload["lotes_candidatos"] = [payload["lotes_candidatos"][0]]
    payload["lotes_candidatos"][0]["peso_total_kg"] = "0.2"
    response = client.post(URL, json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id_lote"] == 101


def test_json_decimal_numbers_are_not_rounded_before_validation(client, payload, auth_headers):
    payload["paquete"]["peso_kg"] = "0.1"
    payload["vehiculos"][0]["peso_max_total_kg"] = "0.3"
    payload["lotes_candidatos"] = [payload["lotes_candidatos"][0]]
    weight = "0.20000000000000000000000000001"
    payload["lotes_candidatos"][0]["peso_total_kg"] = weight
    body = json.dumps(payload).replace(f'"{weight}"', weight)
    response = client.post(
        URL, content=body, headers={**auth_headers, "Content-Type": "application/json"}
    )
    assert response.status_code == 200
    assert response.json() == {"accion": "CREAR_LOTE", "id_tipo_vehiculo": 1, "id_lote": None}


def test_zero_occupancy_and_minimum_package_are_valid(client, payload, auth_headers):
    payload["paquete"] = {"peso_kg": "0.1", "largo_cm": 10, "ancho_cm": 10, "alto_cm": 10}
    payload["ubigeo_destino"] = "010101"
    payload["vehiculos"][0]["max_paquetes"] = 1
    payload["lotes_candidatos"][0].update(cantidad_paquetes=0, peso_total_kg=0)
    response = client.post(URL, json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id_lote"] == 101


def test_unknown_fields_are_rejected(client, payload, auth_headers):
    payload["precio"] = 10
    assert_error(client.post(URL, json=payload, headers=auth_headers), 422)


def test_api_key_is_read_from_environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("API_KEY", "clave-de-entorno")
    settings = Settings(_env_file=None)
    assert settings.api_key.get_secret_value() == "clave-de-entorno"
    assert "clave-de-entorno" not in repr(settings)


def test_dotenv_and_environment_precedence(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("API_KEY", raising=False)
    (tmp_path / ".env").write_text("API_KEY=clave-en-dotenv\n", encoding="utf-8")
    assert Settings().api_key.get_secret_value() == "clave-en-dotenv"
    monkeypatch.setenv("API_KEY", "clave-en-entorno")
    assert Settings().api_key.get_secret_value() == "clave-en-entorno"


def test_only_assignment_task_is_registered():
    paths = set(app.openapi()["paths"])
    assert paths == {URL, "/api/v1/optimize-route"}
    operation = app.openapi()["paths"][URL]["post"]
    assert operation["security"] == [{"APIKeyHeader": []}]
    assert operation["responses"]["422"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorResponse"
    }


def test_unexpected_service_error_returns_safe_json(
    monkeypatch, payload, auth_headers, caplog
):
    monkeypatch.setenv("API_KEY", auth_headers["X-API-Key"])
    get_settings.cache_clear()
    original_message = f"API_KEY={auth_headers['X-API-Key']}; datos=cliente-privado"

    def failing_service(request):
        raise RuntimeError(original_message)

    monkeypatch.setattr(assignments_api, "evaluate_assignment", failing_service)
    try:
        with caplog.at_level(logging.ERROR, logger="app.main"):
            with TestClient(app, raise_server_exceptions=False) as error_client:
                response = error_client.post(URL, json=payload, headers=auth_headers)
    finally:
        get_settings.cache_clear()

    assert response.status_code == 500
    assert response.headers["content-type"].split(";")[0] == "application/json"
    assert response.json() == {
        "error": "error_interno",
        "detalle": "No se pudo procesar la solicitud.",
    }
    assert original_message not in response.text
    assert auth_headers["X-API-Key"] not in response.text
    assert "cliente-privado" not in response.text

    records = [record for record in caplog.records if record.name == "app.main"]
    assert len(records) == 1
    assert records[0].levelno == logging.ERROR
    assert "RuntimeError" in records[0].getMessage()
    assert "failing_service" in records[0].getMessage()
    assert records[0].exc_info is None
    assert original_message not in caplog.text
    assert auth_headers["X-API-Key"] not in caplog.text
    assert "cliente-privado" not in caplog.text


def test_unexpected_error_does_not_escape_to_asgi_server(
    client, monkeypatch, payload, auth_headers
):
    def failing_service(request):
        raise RuntimeError("Diagnóstico privado del servicio")

    monkeypatch.setattr(assignments_api, "evaluate_assignment", failing_service)
    # El fixture usa TestClient con raise_server_exceptions=True por defecto.
    # Si el error escapara al servidor ASGI, esta petición relanzaría la excepción.
    response = client.post(URL, json=payload, headers=auth_headers)
    assert response.status_code == 500
    assert response.json()["error"] == "error_interno"


def test_internal_error_is_documented_in_openapi():
    schema = app.openapi()
    response = schema["paths"][URL]["post"]["responses"]["500"]
    assert response["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/InternalErrorResponse"
    }
    properties = schema["components"]["schemas"]["InternalErrorResponse"]["properties"]
    assert properties["error"]["const"] == "error_interno"
    assert properties["detalle"]["const"] == "No se pudo procesar la solicitud."
