from dotenv import load_dotenv
from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.core.config.settings import settings
from src.core.di.container import Container
from src.instagram.routers.webhook import router as webhook_router
from src.instagram.routers.instagram import router as instagram_router
from src.instagram.routers.health import router as health_router
from src.core.utils.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa o container de injeção de dependência
    container = Container()
    app.container = container
    logger.info("Instagram API iniciada.")
    yield
    logger.info("Instagram API encerrada.")


app = FastAPI(
    title="Instagram Chatbot API",
    description=(
        "Integração completa com a Meta API: "
        "Graph API (perfil, mídia, insights) + "
        "Messenger API (DMs, webhook, chatbot)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(webhook_router)
app.include_router(instagram_router)


if __name__ == "__main__":
    load_dotenv()
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.debug,
    )
