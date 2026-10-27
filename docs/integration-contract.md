# Contrato de integracion PHP-Python

JSON de peticiones y respuestas PHP-Python.

## #14 - Ordenamiento de ruta

`POST /api/v1/optimize-route` (header `X-API-Key`)

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

Algoritmo: vecino mas cercano desde la sede. Las coordenadas se convierten a kilometros con
`x = lng * 111.32 * cos(lat_sede)` e `y = lat * 110.57` y se usa la distancia euclidiana.
Ante un empate gana la parada que llego primero en `paradas`; asi el resultado es reproducible.
La ruta es una aproximacion, no la optima garantizada.

Errores (forma `{ "error": "...", "detalle": "..." }`):

| Codigo | Cuando |
|---|---|
| 401 | `X-API-Key` ausente o incorrecta. |
| 422 | Datos invalidos: sin paradas, mas de 20, ids repetidos, `ubigeo` mal formado, campos desconocidos, `lat` sin `lng` (o al reves), coordenadas como texto o fuera de Lima y Callao. |
| 422 | `id_sede` o `ubigeo_destino` que no existen en el dataset. |

La **respuesta propuesta** (`orden` + `algoritmo`) debe confirmarse con el equipo de PHP.
