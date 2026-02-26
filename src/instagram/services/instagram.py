import httpx
import logging
from typing import Optional

from src.core.config.settings import settings as app_settings
from src.instagram.models.webhook import InstagramProfile, InstagramMedia, PaginatedMedia

logger = logging.getLogger(__name__)


class InstagramService:
    """
    Combina a Graph API (perfil, mídia, insights) com
    a Messenger/Send API (envio de DMs via webhook).
    """

    def __init__(
        self,
        base_url: str = app_settings.instagram.base_url,
        token: str = app_settings.instagram.access_token,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.base_url = base_url
        self.token = token
        # Usa Bearer Token para não expor a credencial na URL (logs)
        headers = {"Authorization": f"Bearer {token}"}
        self.client = client or httpx.AsyncClient(timeout=30, headers=headers)

    # ─── Helpers ──────────────────────────────────────────────────────────────

    async def _get(self, path: str, params: dict = {}) -> dict:
        # params = {"access_token": self.token, **params} # Removido para usar Bearer
        try:
            response = await self.client.get(f"{self.base_url}{path}", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Erro GET {path}: {e.response.status_code} - {e.response.text}"
            )
            raise

    async def _post(self, path: str, data: dict = {}) -> dict:
        # data = {"access_token": self.token, **data} # Removido para usar Bearer
        try:
            response = await self.client.post(f"{self.base_url}{path}", data=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Erro POST {path}: {e.response.status_code} - {e.response.text}"
            )
            raise

    async def _post_json(self, path: str, payload: dict) -> dict:
        try:
            response = await self.client.post(
                f"{self.base_url}{path}",
                json=payload,
                # params={"access_token": self.token}, # Removido para usar Bearer
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Erro POST JSON {path}: {e.response.status_code} - {e.response.text}"
            )
            raise

    # ─── Graph API: Perfil ─────────────────────────────────────────────────────

    async def get_profile(self, ig_user_id: str) -> InstagramProfile:
        fields = "id,name,biography,followers_count,follows_count,media_count,profile_picture_url,website,username"
        data = await self._get(f"/{ig_user_id}", {"fields": fields})
        return InstagramProfile(**data)

    # ─── Graph API: Mídia ──────────────────────────────────────────────────────

    async def get_media(
        self,
        ig_user_id: str,
        limit: int = 10,
        after: Optional[str] = None,
    ) -> PaginatedMedia:
        fields = "id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,like_count,comments_count"
        params: dict = {"fields": fields, "limit": limit}
        if after:
            params["after"] = after

        data = await self._get(f"/{ig_user_id}/media", params)
        medias = [InstagramMedia(**item) for item in data.get("data", [])]
        next_cursor = data.get("paging", {}).get("cursors", {}).get("after")
        return PaginatedMedia(data=medias, next_cursor=next_cursor)

    async def publish_image(
        self,
        ig_user_id: str,
        image_url: str,
        caption: Optional[str] = None,
    ) -> dict:
        # Passo 1: criar container de mídia
        payload: dict = {"image_url": image_url}
        if caption:
            payload["caption"] = caption

        container = await self._post(f"/{ig_user_id}/media", payload)
        creation_id = container["id"]

        # Passo 2: publicar o container
        return await self._post(
            f"/{ig_user_id}/media_publish",
            {"creation_id": creation_id},
        )

    # ─── Graph API: Insights ───────────────────────────────────────────────────

    async def get_media_insights(self, media_id: str) -> dict:
        metrics = "engagement,impressions,reach,saved"
        return await self._get(f"/{media_id}/insights", {"metric": metrics})

    async def get_account_insights(self, ig_user_id: str) -> dict:
        params = {
            "metric": "follower_count,impressions,reach,profile_views",
            "period": "day",
        }
        return await self._get(f"/{ig_user_id}/insights", params)

    # ─── Send API: Mensagens Diretas ───────────────────────────────────────────

    async def send_text(self, recipient_id: str, text: str) -> dict:
        """Envia uma mensagem de texto simples via DM."""
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text},
        }
        return await self._post_json("/me/messages", payload)

    async def send_quick_replies(
        self,
        recipient_id: str,
        text: str,
        options: list[dict],
    ) -> dict:
        """
        Envia mensagem com quick replies.

        Exemplo de options:
            [{"title": "Produtos", "payload": "PRODUTOS"},
             {"title": "Suporte",  "payload": "SUPORTE"}]
        """
        quick_replies = [
            {"content_type": "text", "title": opt["title"], "payload": opt["payload"]}
            for opt in options
        ]
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text, "quick_replies": quick_replies},
        }
        return await self._post_json("/me/messages", payload)

    async def send_generic_template(
        self,
        recipient_id: str,
        elements: list[dict],
    ) -> dict:
        """
        Envia um carrossel de cards (Generic Template).

        Cada elemento deve conter: title, subtitle (opcional),
        image_url (opcional), buttons (opcional).
        """
        payload = {
            "recipient": {"id": recipient_id},
            "message": {
                "attachment": {
                    "type": "template",
                    "payload": {
                        "template_type": "generic",
                        "elements": elements,
                    },
                }
            },
        }
        return await self._post_json("/me/messages", payload)

    # ─── Lifecycle ─────────────────────────────────────────────────────────────

    async def close(self):
        await self.client.aclose()
