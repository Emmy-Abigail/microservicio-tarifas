import math

import pytest

from app.data import geography
from app.schemas.routes import RouteRequest
from app.services.route_optimizer import (
    UnknownDistrictError,
    UnknownSedeError,
    optimize_route,
)


URL = "/api/v1/optimize-route"

MIRAFLORES = "150122"
BARRANCO = "150104"
SURCO = "150140"


@pytest.fixture
def route_payload():
    return {
        "id_sede": 3,
        "paradas": [
            {"id_paquete": 5021, "ubigeo_destino": MIRAFLORES},
            {"id_paquete": 5022, "ubigeo_destino": BARRANCO},
            {"id_paquete": 5023, "ubigeo_destino": SURCO},
        ],
    }


def route(id_sede, stops):
    request = RouteRequest.model_validate(
        {
            "id_sede": id_sede,
            "paradas": [
                {"id_paquete": package_id, "ubigeo_destino": ubigeo}
                for package_id, ubigeo in stops
            ],
        }
    )
    return optimize_route(request).orden


def assert_error(response, status_code):
    assert response.status_code == status_code
    body = response.json()
    assert set(body) == {"error", "detalle"}
    assert body["error"] == "datos_invalidos"
    assert isinstance(body["detalle"], str) and body["detalle"]


# --- Algoritmo ---------------------------------------------------------------


def test_contract_example_starts_in_the_sede_district():
    # La Sede Sur está en Surco (0 km), luego Barranco (1.87 km) y Miraflores (3.15 km).
    stops = [(5021, MIRAFLORES), (5022, BARRANCO), (5023, SURCO)]
    assert route(3, stops) == [5023, 5022, 5021]


def test_single_stop():
    assert route(1, [(7, MIRAFLORES)]) == [7]


def test_chain_of_nearest_neighbours_from_sede_norte():
    # Independencia -> Comas -> Carabayllo -> Puente Piedra -> Cercado -> Miraflores
    stops = [
        (1, "150106"),  # Carabayllo
        (2, "150101"),  # Cercado de Lima
        (3, "150112"),  # Independencia
        (4, "150125"),  # Puente Piedra
        (5, "150110"),  # Comas
        (6, MIRAFLORES),
    ]
    assert route(1, stops) == [3, 5, 1, 4, 2, 6]


def test_first_stop_is_the_closest_to_the_sede():
    # Cálculo independiente de la distancia en línea recta desde la sede.
    sede = geography.get_sede(2)
    stops = [(1, "150106"), (2, "150142"), (3, "150132"), (4, "150103"), (5, "150119")]

    def distance_to_sede(ubigeo):
        district = geography.get_district(ubigeo)
        dx = (district["lng"] - sede["lng"]) * 111.32 * math.cos(math.radians(sede["lat"]))
        dy = (district["lat"] - sede["lat"]) * 110.57
        return math.hypot(dx, dy)

    closest = min(stops, key=lambda stop: distance_to_sede(stop[1]))
    assert route(2, stops)[0] == closest[0]


def test_stops_in_the_same_district_keep_arrival_order():
    stops = [(30, MIRAFLORES), (10, MIRAFLORES), (20, MIRAFLORES)]
    assert route(3, stops) == [30, 10, 20]


def test_equal_distance_uses_arrival_order():
    # Dos paquetes del mismo distrito intercalados con otro más lejano.
    stops = [(1, MIRAFLORES), (2, "150119"), (3, MIRAFLORES)]
    assert route(3, stops) == [1, 3, 2]


def test_result_contains_every_package_exactly_once():
    districts = [district["ubigeo"] for district in geography.list_districts()][:20]
    stops = [(1000 + position, ubigeo) for position, ubigeo in enumerate(districts)]
    assert sorted(route(4, stops)) == sorted(package_id for package_id, _ in stops)


def test_same_input_gives_same_output():
    stops = [(1, MIRAFLORES), (2, BARRANCO), (3, SURCO), (4, "150108")]
    assert route(3, stops) == route(3, stops)


def test_unknown_sede():
    with pytest.raises(UnknownSedeError):
        route(99, [(1, MIRAFLORES)])


def test_unknown_district():
    with pytest.raises(UnknownDistrictError):
        route(3, [(1, "999999")])


# --- Endpoint ----------------------------------------------------------------


def test_endpoint_returns_the_ordered_package_ids(client, route_payload, auth_headers):
    response = client.post(URL, json=route_payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {
        "orden": [5023, 5022, 5021],
        "algoritmo": "greedy-nearest-neighbor",
    }


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "incorrecta"}, {"X-API-Key": ""}])
def test_endpoint_requires_the_internal_key(client, route_payload, headers):
    assert_error(client.post(URL, json=route_payload, headers=headers), 401)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(id_sede=0),
        lambda p: p.update(id_sede=True),
        lambda p: p.update(id_sede=1.5),
        lambda p: p.update(id_sede="3"),
        lambda p: p.update(paradas=[]),
        lambda p: p.update(paradas=None),
        lambda p: p["paradas"][0].update(id_paquete=0),
        lambda p: p["paradas"][0].update(id_paquete=True),
        lambda p: p["paradas"][0].update(id_paquete="5021"),
        lambda p: p["paradas"][0].update(id_paquete=1.5),
        lambda p: p["paradas"][0].update(ubigeo_destino="15012"),
        lambda p: p["paradas"][0].update(ubigeo_destino="1501220"),
        lambda p: p["paradas"][0].update(ubigeo_destino="15012a"),
        lambda p: p["paradas"][0].update(ubigeo_destino="１５０１２２"),
        lambda p: p["paradas"][0].update(ubigeo_destino=150122),
        lambda p: p.update(precio=10),
        lambda p: p["paradas"][0].update(extra="x"),
        lambda p: p.pop("id_sede"),
        lambda p: p.pop("paradas"),
        lambda p: p["paradas"][0].pop("id_paquete"),
        lambda p: p["paradas"][0].pop("ubigeo_destino"),
    ],
)
def test_endpoint_rejects_invalid_input(client, route_payload, auth_headers, mutate):
    mutate(route_payload)
    assert_error(client.post(URL, json=route_payload, headers=auth_headers), 422)


def test_endpoint_rejects_duplicated_package_ids(client, route_payload, auth_headers):
    route_payload["paradas"][1]["id_paquete"] = route_payload["paradas"][0]["id_paquete"]
    response = client.post(URL, json=route_payload, headers=auth_headers)
    assert_error(response, 422)
    assert "duplicados" in response.json()["detalle"]


def test_endpoint_accepts_20_stops_and_rejects_21(client, route_payload, auth_headers):
    stops = [{"id_paquete": 1 + i, "ubigeo_destino": MIRAFLORES} for i in range(21)]

    route_payload["paradas"] = stops[:20]
    response = client.post(URL, json=route_payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["orden"] == list(range(1, 21))

    route_payload["paradas"] = stops
    assert_error(client.post(URL, json=route_payload, headers=auth_headers), 422)


def test_endpoint_rejects_unknown_sede(client, route_payload, auth_headers):
    route_payload["id_sede"] = 99
    response = client.post(URL, json=route_payload, headers=auth_headers)
    assert_error(response, 422)
    assert "sede" in response.json()["detalle"]


def test_endpoint_rejects_unknown_district(client, route_payload, auth_headers):
    route_payload["paradas"][0]["ubigeo_destino"] = "999999"
    response = client.post(URL, json=route_payload, headers=auth_headers)
    assert_error(response, 422)
    assert "distrito" in response.json()["detalle"]


@pytest.mark.parametrize("raw_body", ['{"id_sede":', "null", "[]"])
def test_endpoint_rejects_malformed_bodies(client, auth_headers, raw_body):
    response = client.post(
        URL, content=raw_body, headers={**auth_headers, "Content-Type": "application/json"}
    )
    assert_error(response, 422)
