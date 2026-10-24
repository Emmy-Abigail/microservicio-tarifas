# Estructura del proyecto Python

Estructura propuesta con FastAPI para asignacion de lotes y calculo de rutas. El precio y la persistencia en MySQL quedan en PHP.

```text
microservicio-tarifas/
|-- app/
|   |-- main.py                    # Crear FastAPI y registrar los endpoints.
|   |-- api/
|   |   |-- dependencies.py        # Validar la clave interna X-API-Key.
|   |   |-- decimal_json.py        # Lectura JSON decimal reutilizable por router.
|   |   |-- assignments.py         # POST /api/v1/batch-assignments/evaluate.
|   |   |-- routes.py              # POST /api/v1/optimize-route.
|   |   `-- health.py              # GET /health.
|   |-- schemas/
|   |   |-- assignments.py         # Validar entrada y salida de asignacion.
|   |   `-- routes.py              # Validar entrada y salida de rutas.
|   |-- services/
|   |   |-- batch_assignment.py    # Elegir vehiculo y recomendar lote.
|   |   `-- route_optimizer.py     # Calcular el orden de las paradas.
|   |-- core/
|   |   `-- config.py              # Leer variables de entorno.
|   `-- data/
|       |-- geography.json         # Sedes, distritos, zonas y coordenadas.
|       `-- geography.py           # Cargar y consultar ese dataset.
|-- tests/
|   |-- test_batch_assignment.py   # Pruebas de asignacion.
|   |-- test_route_optimizer.py    # Pruebas de rutas.
|   |-- test_geography.py          # Pruebas del dataset.
|   `-- test_api.py                # Pruebas de endpoints.
|-- docs/
|   `-- integration-contract.md    # JSON de peticiones y respuestas PHP-Python.
|-- .env.example                   # Variables de configuracion de ejemplo.
|-- .gitignore                     # Archivos que no se suben a Git.
|-- pyproject.toml                 # Dependencias y configuracion del proyecto.
|-- Dockerfile                     # Construccion y arranque del contenedor.
|-- docker-compose.yml             # Arranque de la API en localhost:8000.
|-- .dockerignore                  # Excluir entorno local y secretos del contexto Docker.
`-- README.md                      # Instalacion, arranque y pruebas.
```

Agregar `__init__.py` en `app/` y sus subcarpetas de codigo; pueden estar vacios.

Los endpoints van en `api/`, las validaciones en `schemas/` y la logica de calculo en `services/`. Python devuelve sus resultados a PHP, que crea los lotes y guarda los cambios.
