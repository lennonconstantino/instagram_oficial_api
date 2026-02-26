from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html
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
    """
    Lifespan context manager for the FastAPI application.

    This function is responsible for initializing and cleaning up resources
    before and after the application starts and shuts down.

    Args:
        app (FastAPI): The FastAPI application instance.
    """
    container = Container()
    app.container = container

    logger.info("Instagram API iniciada.")
    yield
    logger.info("Instagram API encerrada.")

# Create FastAPI app
is_production = settings.api.environment == "production"

app = FastAPI(
    title="Instagram Chatbot API",
    description=(
        "Integração completa com a Meta Instagram API: "
        "Graph API (perfil, mídia, insights) + "
        "Messenger API (DMs, webhook, chatbot)."
    ),
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.api.debug,
    docs_url=None if is_production else "/docs",
    redoc_url=None,  # Disable default Redoc to use custom CDN
    openapi_url=None if is_production else "/openapi.json",    
)

app.include_router(health_router)
app.include_router(webhook_router)
app.include_router(instagram_router)

if not is_production:
    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        """Redoc documentation."""
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=app.title + " - ReDoc",
            redoc_js_url="https://unpkg.com/redoc@latest/bundles/redoc.standalone.js",
        )

if __name__ == "__main__":
    load_dotenv()
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.debug,
    )
