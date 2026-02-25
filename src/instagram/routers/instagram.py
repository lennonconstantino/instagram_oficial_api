from fastapi import APIRouter, Depends, Query
from typing import Optional
from dependency_injector.wiring import inject, Provide

from src.core.di.container import Container
from src.instagram.models.webhook import InstagramProfile, PaginatedMedia, PublishMediaRequest
from src.instagram.services.instagram import InstagramService

router = APIRouter(prefix="/instagram", tags=["Instagram Graph API"])


@router.get("/profile/{ig_user_id}", response_model=InstagramProfile)
@inject
async def get_profile(
    ig_user_id: str,
    service: InstagramService = Depends(Provide[Container.instagram.provided.instagram_service]),
):
    """Retorna dados do perfil Business/Creator."""
    return await service.get_profile(ig_user_id)


@router.get("/media/{ig_user_id}", response_model=PaginatedMedia)
@inject
async def get_media(
    ig_user_id: str,
    limit: int = Query(10, ge=1, le=50),
    after: Optional[str] = Query(None),
    service: InstagramService = Depends(Provide[Container.instagram.provided.instagram_service]),
):
    """Lista posts do perfil com paginação por cursor."""
    return await service.get_media(ig_user_id, limit=limit, after=after)


@router.post("/media/{ig_user_id}/publish")
@inject
async def publish_media(
    ig_user_id: str,
    body: PublishMediaRequest,
    service: InstagramService = Depends(Provide[Container.instagram.provided.instagram_service]),
):
    """Publica uma imagem no feed via URL pública."""
    return await service.publish_image(
        ig_user_id,
        str(body.image_url),
        body.caption,
    )


@router.get("/media/{media_id}/insights")
@inject
async def get_media_insights(
    media_id: str,
    service: InstagramService = Depends(Provide[Container.instagram.provided.instagram_service]),
):
    """Retorna métricas de um post (engajamento, impressões, alcance, salvamentos)."""
    return await service.get_media_insights(media_id)


@router.get("/account/{ig_user_id}/insights")
@inject
async def get_account_insights(
    ig_user_id: str,
    service: InstagramService = Depends(Provide[Container.instagram.provided.instagram_service]),
):
    """Retorna métricas gerais da conta (seguidores, alcance, impressões, visualizações)."""
    return await service.get_account_insights(ig_user_id)
