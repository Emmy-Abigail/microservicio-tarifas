from copy import deepcopy

import pytest

from app.schemas.assignments import AssignmentRequest
from app.services.batch_assignment import NoCompatibleVehicleError, evaluate_assignment


def evaluate(payload):
    return evaluate_assignment(AssignmentRequest.model_validate(payload)).model_dump()


@pytest.mark.parametrize(
    ("weight", "dimensions", "vehicle_id"),
    [
        (3, (30, 22, 10), 1),
        (20, (40, 40, 40), 1),
        ("20.0001", (30, 22, 10), 2),
        (3, ("40.0001", 22, 10), 2),
        (3, (30, "40.0001", 10), 2),
        (3, (30, 22, "125.0001"), 3),
        (50, (150, 150, 150), 3),
    ],
)
def test_choose_lowest_compatible_level(payload, weight, dimensions, vehicle_id):
    payload["paquete"] = dict(zip(
        ("peso_kg", "largo_cm", "ancho_cm", "alto_cm"), (weight, *dimensions)
    ))
    payload["vehiculos"].reverse()
    assert evaluate(payload)["id_tipo_vehiculo"] == vehicle_id


def test_oldest_batch_with_capacity(payload):
    payload["lotes_candidatos"].reverse()
    assert evaluate(payload) == {"accion": "USAR_LOTE", "id_tipo_vehiculo": 1, "id_lote": 101}


@pytest.mark.parametrize(
    ("field", "value"), [("cantidad_paquetes", 20), ("peso_total_kg", 18)]
)
def test_skip_full_oldest_batch(payload, field, value):
    payload["lotes_candidatos"][0][field] = value
    assert evaluate(payload)["id_lote"] == 102


def test_exact_weight_and_count_capacity(payload):
    payload["lotes_candidatos"][0].update(cantidad_paquetes=19, peso_total_kg=17)
    assert evaluate(payload)["id_lote"] == 101


@pytest.mark.parametrize(
    ("package_weight", "batch_weight", "limit", "action"),
    [
        ("0.1", "0.2", "0.3", "USAR_LOTE"),
        ("0.1", "0.20000000000000000000000000001", "0.3", "CREAR_LOTE"),
        ("0.1", "0.19999999999999999999999999999", "0.3", "USAR_LOTE"),
        ("0.10000000000000000000000000001", "0.2", "0.3", "CREAR_LOTE"),
    ],
)
def test_exact_decimal_weight_comparisons(payload, package_weight, batch_weight, limit, action):
    payload["paquete"]["peso_kg"] = package_weight
    payload["vehiculos"][0]["peso_max_total_kg"] = limit
    payload["lotes_candidatos"] = [payload["lotes_candidatos"][0]]
    payload["lotes_candidatos"][0]["peso_total_kg"] = batch_weight
    assert evaluate(payload)["accion"] == action


@pytest.mark.parametrize("empty", [True, False])
def test_create_batch_when_none_available(payload, empty):
    if empty:
        payload["lotes_candidatos"] = []
    else:
        for batch in payload["lotes_candidatos"]:
            batch["cantidad_paquetes"] = 20
    assert evaluate(payload) == {"accion": "CREAR_LOTE", "id_tipo_vehiculo": 1, "id_lote": None}


def test_never_upgrade_to_vehicle_with_available_batch(payload):
    payload["lotes_candidatos"][0]["cantidad_paquetes"] = 20
    payload["lotes_candidatos"][1]["id_tipo_vehiculo"] = 2
    assert evaluate(payload) == {"accion": "CREAR_LOTE", "id_tipo_vehiculo": 1, "id_lote": None}


def test_equal_timestamps_are_ordered_by_id(payload):
    payload["lotes_candidatos"][1]["created_at"] = payload["lotes_candidatos"][0]["created_at"]
    payload["lotes_candidatos"].reverse()
    assert evaluate(payload)["id_lote"] == 101


def test_dates_are_compared_as_instants(payload):
    payload["lotes_candidatos"][0]["created_at"] = "2026-10-21T08:00:00-05:00"
    payload["lotes_candidatos"][1]["created_at"] = "2026-10-21T12:30:00+00:00"
    assert evaluate(payload)["id_lote"] == 102


def test_same_instant_with_different_offsets_uses_id(payload):
    payload["lotes_candidatos"][1]["created_at"] = "2026-10-21T13:00:00Z"
    payload["lotes_candidatos"].reverse()
    assert evaluate(payload)["id_lote"] == 101


def test_equal_vehicle_levels_use_lowest_id(payload):
    payload["vehiculos"][1]["nivel"] = 1
    payload["vehiculos"].reverse()
    assert evaluate(payload)["id_tipo_vehiculo"] == 1


@pytest.mark.parametrize("empty", [True, False])
def test_no_compatible_vehicle(payload, empty):
    payload["lotes_candidatos"] = []
    if empty:
        payload["vehiculos"] = []
    else:
        for vehicle in payload["vehiculos"]:
            vehicle["lado_max_cm"] = 20
    with pytest.raises(NoCompatibleVehicleError):
        evaluate(payload)


def test_evaluation_does_not_reserve_or_mutate(payload):
    request = AssignmentRequest.model_validate(payload)
    original = deepcopy(request)
    assert evaluate_assignment(request) == evaluate_assignment(request)
    assert request == original
