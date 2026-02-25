from fastapi import APIRouter
from datetime import datetime

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Health check para monitoramento e balanceadores de carga."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
