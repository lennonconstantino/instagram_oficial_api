import hashlib
import hmac
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.core.config import settings
from src.instagram.handlers.chatbot import ChatbotHandler
from src.instagram.models.webhook import WebhookPayload
from src.instagram.repositories.session import SessionRepository
from src.instagram.services.instagram import InstagramService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Webhook"])

# Instâncias compartilhadas (singleton simples)
_service = InstagramService()
_sessions = SessionRepository()
_chatbot = ChatbotHandler(service=_service, sessions=_sessions)


# ─── Dependências ──────────────────────────────────────────────────────────────

def get_chatbot() -> ChatbotHandler:
    return _chatbot


# ─── Verificação de assinatura HMAC-SHA256 ─────────────────────────────────────

def _verify_signature(body: bytes, signature_header: str | None) -> bool:
    """
    Valida o cabeçalho X-Hub-Signature-256 enviado pela Meta.
    Formato: sha256=<hmac-hex>
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        settings.instagram_app_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)


# ─── GET /webhook — verificação do challenge pela Meta ────────────────────────

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.instagram_verify_token:
        logger.info("Webhook verificado com sucesso.")
        return int(hub_challenge)

    logger.warning("Falha na verificação do webhook.")
    raise HTTPException(status_code=403, detail="Verify token inválido.")


# ─── POST /webhook — recebimento de eventos da Meta ───────────────────────────

@router.post("/webhook")
async def receive_webhook(
    request: Request,
    chatbot: ChatbotHandler = Depends(get_chatbot),
):
    body = await request.body()

    # Valida assinatura HMAC-SHA256
    signature = request.headers.get("X-Hub-Signature-256")
    if not _verify_signature(body, signature):
        logger.warning("Assinatura inválida recebida.")
        raise HTTPException(status_code=403, detail="Assinatura inválida.")

    try:
        payload = WebhookPayload.model_validate_json(body)
    except Exception as exc:
        logger.error("Payload inválido: %s", exc)
        raise HTTPException(status_code=400, detail="Payload inválido.")

    # Processa somente eventos do Instagram
    if payload.object != "instagram":
        return {"status": "ignored"}

    for entry in payload.entry:
        for messaging in entry.messaging:
            sender_id = messaging.sender.id

            try:
                if messaging.message and messaging.message.text:
                    await chatbot.handle_message(sender_id, messaging.message.text)

                elif messaging.postback:
                    await chatbot.handle_postback(sender_id, messaging.postback.payload)

            except Exception as exc:
                # Nunca deixe o webhook retornar 5xx, a Meta irá retentar
                logger.error("Erro ao processar mensagem de %s: %s", sender_id, exc)

    # A Meta exige resposta 200 em < 5 segundos
    return {"status": "ok"}
