import logging

from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.instagram.routers.webhook import router as webhook_router
from src.instagram.routers.instagram import router as instagram_router
from src.instagram.routers.health import router as health_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger(__name__).info("Instagram API iniciada.")
    yield
    logging.getLogger(__name__).info("Instagram API encerrada.")


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
