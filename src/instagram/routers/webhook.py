import hashlib
import hmac

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from dependency_injector.wiring import inject, Provide

from src.core.config.settings import settings
from src.instagram.handlers.chatbot import ChatbotHandler
from src.instagram.models.webhook import WebhookPayload
from src.core.di.container import Container
from src.core.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Webhook"])


# ─── Verificação de assinatura HMAC-SHA256 ─────────────────────────────────────

def _verify_signature(body: bytes, signature_header: str | None) -> bool:
    """
    Valida o cabeçalho X-Hub-Signature-256 enviado pela Meta.
    Formato: sha256=<hmac-hex>
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        settings.instagram.app_secret.encode(),
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
    if hub_mode == "subscribe" and hub_verify_token == settings.instagram.verify_token:
        logger.info("Webhook verificado com sucesso.")
        return int(hub_challenge)

    logger.warning("Falha na verificação do webhook.")
    raise HTTPException(status_code=403, detail="Verify token inválido.")


# ─── POST /webhook — recebimento de eventos da Meta ───────────────────────────

@router.post("/webhook")
@inject
async def receive_webhook(
    request: Request,
    chatbot: ChatbotHandler = Depends(Provide[Container.instagram.provided.chatbot_handler.call()]),
):
    body = await request.body()
    logger.info(f"Webhook payload: {body}")  # Adicione isso

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
            try:
                # Ignorar ecos da própria conta
                if messaging.message and messaging.message.is_echo:
                    continue
                
                # Ignorar eventos sem mensagem e sem postback (ex: read receipts)
                if not messaging.message and not messaging.postback:
                    continue
                    
                sender_id = messaging.sender.id

                if messaging.message and messaging.message.text:
                    await chatbot.handle_message(sender_id, messaging.message.text)

                elif messaging.postback:
                    await chatbot.handle_postback(sender_id, messaging.postback.payload)

            except Exception as e:
                logger.exception(f"Erro ao processar mensagem de {sender_id}: {e}")
                # Não propagar erro para o Facebook não reenviar o webhook infinitamente
                # mas logar o erro é crítico.

    return {"status": "processed"}
