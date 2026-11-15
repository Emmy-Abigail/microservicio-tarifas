# Contrato de integracion PHP-Python

JSON de peticiones y respuestas entre PHP y Python. Angular nunca llama a Python: siempre pasa por PHP.
Python es un servicio de calculo puro: no se conecta a la base de datos ni guarda nada.

Seguridad: las rutas `/api/v1/*` exigen el header `X-API-Key` (variable `API_KEY` en Python,
`ASSIGNMENT_API_KEY` en PHP). Los errores tienen la forma `{ "error": "...", "detalle": "..." }`.

## GET /health

Sin API key. Responde `{"status": "ok"}`. Lo usan el despertador del despliegue y el login de PHP
(`SERVICE_WARMUP_PATH`) para despertar el servicio en Render.

## #13 - Asignacion de lote

`POST /api/v1/batch-assignments/evaluate` (header `X-API-Key`). PHP lo llama al registrar un paquete
(`POST /packages`) y al reasignar un fallido (`POST /packages/{id}/retry`).

PHP envia:

```json
{
  "id_sede": 3,
  "ubigeo_destino": "150122",
  "paquete": { "peso_kg": 3, "largo_cm": 30, "ancho_cm": 22, "alto_cm": 10 },
  "vehiculos": [
    { "id": 1, "nivel": 1, "peso_max_total_kg": 20, "lado_max_cm": 40, "max_paquetes": 20 },
    { "id": 2, "nivel": 2, "peso_max_total_kg": 200, "lado_max_cm": 125, "max_paquetes": 20 },
    { "id": 3, "nivel": 3, "peso_max_total_kg": 1000, "lado_max_cm": 150, "max_paquetes": 20 }
  ],
  "lotes_candidatos": [
    { "id": 101, "id_tipo_vehiculo": 1, "cantidad_paquetes": 12, "peso_total_kg": 15, "created_at": "2026-10-21T08:00:00-05:00" },
    { "id": 102, "id_tipo_vehiculo": 1, "cantidad_paquetes": 5, "peso_total_kg": 8, "created_at": "2026-10-21T09:00:00-05:00" }
  ]
}
```

| Campo | Regla |
|---|---|
| `id_sede`, `ubigeo_destino` | Sede de origen y distrito de destino del paquete. |
| `paquete` | Peso (0.1 a 50 kg) y medidas (10 a 150 cm). |
| `vehiculos` | Tipos de vehiculo vigentes, sin ids repetidos. |
| `lotes_candidatos` | Lotes `EN_PREPARACION` de la misma sede y la misma zona de destino (PHP ya filtra por zona, regla R3). Sin ids repetidos. |

Algoritmo (enunciado, pag. 11-12, reglas R2 a R6):

1. Vehiculo: el de menor nivel cuyo peso maximo y lado maximo admiten el paquete (R4).
2. Lote: el **mas antiguo** (`created_at`, luego `id`) del mismo vehiculo con espacio para un paquete
   mas (maximo 20, R2) y peso disponible (R5). Prioridad FIFO estricta (R6).
3. Si ningun lote tiene espacio, `CREAR_LOTE`.

Respuestas 200:

```json
{ "accion": "USAR_LOTE", "id_tipo_vehiculo": 1, "id_lote": 101 }
{ "accion": "CREAR_LOTE", "id_tipo_vehiculo": 1, "id_lote": null }
```

PHP vuelve a validar la respuesta (vehiculo y lote esperados) antes de guardar.

| Codigo | Cuando |
|---|---|
| 401 | `X-API-Key` ausente o incorrecta. |
| 422 | Datos invalidos o campos desconocidos, o ningun vehiculo admite el paquete. |

## #14 - Ordenamiento de ruta

`POST /api/v1/optimize-route` (header `X-API-Key`). PHP lo llama al despachar un lote
(`POST /batches/{id}/dispatch`).

PHP envia:

```json
{
  "id_sede": 3,
  "paradas": [
    { "id_paquete": 5021, "ubigeo_destino": "150122" },
    { "id_paquete": 5022, "ubigeo_destino": "150104" },
    { "id_paquete": 5023, "ubigeo_destino": "150140" }
  ]
}
```

| Campo | Regla |
|---|---|
| `id_sede` | Entero positivo. Sede desde donde sale el lote; Python obtiene sus coordenadas del dataset. |
| `paradas` | Entre 1 y 20 paquetes del mismo lote, sin `id_paquete` repetidos. |
| `id_paquete` | Entero positivo. Python lo conserva en la respuesta. |
| `ubigeo_destino` | Texto de seis digitos. Python obtiene las coordenadas del distrito del dataset. |
| `lat`, `lng` | Opcionales. Punto que el operador marco en el mapa; si vienen se usan en lugar del centroide del distrito. Van juntos, como numeros, dentro de Lima y Callao (lat -12.60 a -11.50, lng -77.30 a -76.55). PHP solo los envia cuando el paquete los tiene. |

Ejemplo de parada con punto: `{ "id_paquete": 5021, "ubigeo_destino": "150122", "lat": -12.121234, "lng": -77.030987 }`.

Respuesta 200 (ids de paquetes en el orden de entrega):

```json
{ "orden": [5023, 5022, 5021], "algoritmo": "greedy-nearest-neighbor" }
```

Algoritmo (enunciado, pag. 12, seccion 8): vecino mas cercano desde la sede. Las coordenadas se
convierten a kilometros con `x = lng * 111.32 * cos(lat_sede)` e `y = lat * 110.57` y se usa la
distancia euclidiana. Ante un empate gana la parada que llego primero en `paradas`; asi el resultado
es reproducible. La ruta es una aproximacion, no la optima garantizada.

| Codigo | Cuando |
|---|---|
| 401 | `X-API-Key` ausente o incorrecta. |
| 422 | Datos invalidos: sin paradas, mas de 20, ids repetidos, `ubigeo` mal formado, campos desconocidos, `lat` sin `lng` (o al reves), coordenadas como texto o fuera de Lima y Callao. |
| 422 | `id_sede` o `ubigeo_destino` que no existen en el dataset. |

## Si Python no responde (lo resuelve PHP)

Enunciado, pag. 6, "Aislamiento y Respaldo de Python": la asignacion de lotes y la optimizacion de
rutas tienen logica de respaldo en PHP, sin bloquear el flujo principal.

| Llamada | Tiempo de espera | Reintentos | Si sigue fallando |
|---|---|---|---|
| Asignacion de lote (#13) | `ASSIGNMENT_TIMEOUT_SECONDS` | 1 | PHP aplica las mismas reglas FIFO (R2 a R6) y registra el paquete igual. La respuesta trae `asignacion_respaldo: true`. |
| Ruta (#14) | `ROUTE_TIMEOUT_SECONDS` o el de asignacion | 1 | PHP despacha con las paradas en orden de registro. La respuesta trae `ruta_optimizada: false`. |

Se reintenta ante tiempo agotado, error de red o 5xx. Un 401 o un 422 no se reintentan. PHP nunca
envia a Angular los detalles del error de Python (cuerpos, URL ni claves).
