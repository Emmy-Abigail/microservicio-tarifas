import math

from app.data import geography
from app.schemas.routes import RouteRequest, RouteResponse


# Proyección simple de grados a kilómetros: un grado de longitud mide menos que
# uno de latitud, así que se corrige con el coseno de la latitud de la sede.
KM_PER_DEGREE_LATITUDE = 110.57
KM_PER_DEGREE_LONGITUDE_AT_EQUATOR = 111.32

# Evita que el ruido de coma flotante rompa los empates de distancia.
DISTANCE_DECIMALS = 9


class UnknownSedeError(ValueError):
    pass


class UnknownDistrictError(ValueError):
    pass


def to_kilometers(lat: float, lng: float, reference_lat: float) -> tuple[float, float]:
    x = lng * KM_PER_DEGREE_LONGITUDE_AT_EQUATOR * math.cos(math.radians(reference_lat))
    y = lat * KM_PER_DEGREE_LATITUDE
    return x, y


def optimize_route(request: RouteRequest) -> RouteResponse:
    sede = geography.get_sede(request.id_sede)
    if sede is None:
        raise UnknownSedeError(f"La sede {request.id_sede} no existe.")

    reference_lat = sede["lat"]
    current = to_kilometers(sede["lat"], sede["lng"], reference_lat)

    pending: list[tuple[int, int, tuple[float, float]]] = []
    for position, stop in enumerate(request.paradas):
        district = geography.get_district(stop.ubigeo_destino)
        if district is None:
            raise UnknownDistrictError(f"El distrito {stop.ubigeo_destino} no existe.")
        if stop.lat is not None and stop.lng is not None:
            lat, lng = stop.lat, stop.lng
        else:
            lat, lng = district["lat"], district["lng"]
        pending.append((position, stop.id_paquete, to_kilometers(lat, lng, reference_lat)))

    order: list[int] = []
    while pending:
        # Ante un empate gana la parada que llegó primero en la lista.
        nearest = min(
            pending,
            key=lambda item: (round(math.dist(current, item[2]), DISTANCE_DECIMALS), item[0]),
        )
        order.append(nearest[1])
        current = nearest[2]
        pending.remove(nearest)

    return RouteResponse(orden=order)
