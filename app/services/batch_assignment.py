from fractions import Fraction

from app.schemas.assignments import (
    AssignmentRequest,
    AssignmentResponse,
    CreateBatchResponse,
    UseBatchResponse,
)


class NoCompatibleVehicleError(ValueError):
    pass


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
    
    for batch in candidates:
        # La suma de fracciones de Decimal es exacta incluso fuera de la precisión
        # del contexto decimal; no se introducen redondeos en el límite de peso.
        total_weight = Fraction(batch.peso_total_kg) + Fraction(package.peso_kg)
        if (
            batch.cantidad_paquetes + 1 <= vehicle.max_paquetes
            and total_weight <= Fraction(vehicle.peso_max_total_kg)
        ):
            return UseBatchResponse(id_tipo_vehiculo=vehicle.id, id_lote=batch.id)

    return CreateBatchResponse(id_tipo_vehiculo=vehicle.id)
