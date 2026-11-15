from fastapi import APIRouter

router = APIRouter(tags=["Salud"])

@router.get("/health")
def health() -> dict[str, str]:
    """Respuesta corta y sin API key para monitoreo"""
    return {"status": "ok"}