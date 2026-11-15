import math
from fractions import Fraction

from app.data import geography
from app.schemas.assignments import (
    AssignmentRequest,
    AssignmentResponse,
    CandidateBatch,
    CreateBatchResponse,
    UseBatchResponse,
)


# Un lote solo recibe paquetes cuyo destino está a esta distancia de su centro.
RADIO_AGRUPACION_KM = 3.0
RADIO_TIERRA_KM = 6371.0

Point = tuple[float, float]


class NoCompatibleVehicleError(ValueError):
    pass


def distance_km(a: Point, b: Point) -> float:
    """Distancia en línea recta entre dos puntos (fórmula de haversine)."""
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    )
    return 2 * RADIO_TIERRA_KM * math.asin(math.sqrt(h))


def destination_point(request: AssignmentRequest) -> Point | None:
    """Punto del mapa; si no se envió, el centro del distrito de destino."""
    if request.destino_lat is not None and request.destino_lng is not None:
        return (request.destino_lat, request.destino_lng)
    district = geography.get_district(request.ubigeo_destino)
    return None if district is None else (district["lat"], district["lng"])


def is_nearby(batch: CandidateBatch, point: Point | None) -> bool:
    # Sin centro del lote o sin punto del paquete no se puede medir: se conserva el orden de llegada.
    if point is None or batch.centro_lat is None or batch.centro_lng is None:
        return True
    return distance_km(point, (batch.centro_lat, batch.centro_lng)) <= RADIO_AGRUPACION_KM


def evaluate_assignment(request: AssignmentRequest) -> AssignmentResponse:
    package = request.paquete
    longest_side = max(package.largo_cm, package.ancho_cm, package.alto_cm)
    compatible = [
        vehicle
        for vehicle in request.vehiculos
        if package.peso_kg <= vehicle.peso_max_total_kg
        and longest_side <= vehicle.lado_max_cm
    ]
    if not compatible:
        raise NoCompatibleVehicleError("Ningún vehículo admite el peso y las dimensiones del paquete.")

    # El ID hace determinista la selección si se reciben niveles iguales.
    vehicle = min(compatible, key=lambda item: (item.nivel, item.id))
    candidates = sorted(
        (batch for batch in request.lotes_candidatos if batch.id_tipo_vehiculo == vehicle.id),
        key=lambda batch: (batch.created_at, batch.id),
    )
    point = destination_point(request)

    for batch in candidates:
        # La suma de fracciones de Decimal es exacta incluso fuera de la precisión
        # del contexto decimal; no se introducen redondeos en el límite de peso.
        total_weight = Fraction(batch.peso_total_kg) + Fraction(package.peso_kg)
        if (
            batch.cantidad_paquetes + 1 <= vehicle.max_paquetes
            and total_weight <= Fraction(vehicle.peso_max_total_kg)
            and is_nearby(batch, point)
        ):
            return UseBatchResponse(id_tipo_vehiculo=vehicle.id, id_lote=batch.id)

    return CreateBatchResponse(id_tipo_vehiculo=vehicle.id)
