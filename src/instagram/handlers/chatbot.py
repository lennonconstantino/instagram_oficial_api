from src.instagram.services.instagram import InstagramService
from src.instagram.repositories.session import SessionRepository


MENU_OPTIONS = [
    {"title": "Produtos",  "payload": "PRODUTOS"},
    {"title": "Suporte",   "payload": "SUPORTE"},
    {"title": "Horários",  "payload": "HORARIOS"},
]

MENU_TEXT = "Olá! 👋 Como posso te ajudar hoje? Escolha uma das opções abaixo:"

PRODUCTS_TEXT = (
    "🛍️ *Nossos Produtos*\n\n"
    "• Produto A — R$ 99,90\n"
    "• Produto B — R$ 149,90\n"
    "• Produto C — R$ 199,90\n\n"
    "Para falar com um atendente, responda *atendente*."
)

HOURS_TEXT = (
    "🕐 *Horário de Atendimento*\n\n"
    "Segunda a Sexta: 09h – 18h\n"
    "Sábado: 09h – 13h\n"
    "Domingo e Feriados: Fechado"
)


class ChatbotHandler:
    """
    Gerencia o fluxo de conversa via DM do Instagram.

    Estados disponíveis:
        initial      → exibe menu principal
        support_open → aguarda descrição do problema do usuário
    """

    def __init__(self, service: InstagramService, sessions: SessionRepository):
        self.service = service
        self.sessions = sessions

    # ─── Dispatcher principal ──────────────────────────────────────────────────

    async def handle_message(self, sender_id: str, text: str) -> None:
        session = await self.sessions.get(sender_id)
        normalized = text.strip().lower()

        # Encaminha para o handler do estado atual
        if session.state == "support_open":
            await self._handle_support(sender_id, text, session)
            return

        # Palavras-chave / postback payloads
        if normalized in ("produtos", "produto"):
            await self._show_products(sender_id)
        elif normalized in ("suporte", "ajuda"):
            await self._start_support(sender_id, session)
        elif normalized in ("horarios", "horário", "horarios"):
            await self._show_hours(sender_id)
        elif normalized == "atendente":
            await self._transfer_to_agent(sender_id)
        else:
            await self._handle_greeting(sender_id)

    async def handle_postback(self, sender_id: str, payload: str) -> None:
        """Processa cliques em quick replies ou botões de template."""
        routing = {
            "PRODUTOS":  self._show_products,
            "SUPORTE":   self._start_support_postback,
            "HORARIOS":  self._show_hours,
        }
        handler = routing.get(payload)
        if handler:
            await handler(sender_id)
        else:
            await self._handle_fallback(sender_id, payload)

    # ─── Handlers de estado ────────────────────────────────────────────────────

    async def _handle_greeting(self, sender_id: str) -> None:
        await self.service.send_quick_replies(
            sender_id,
            MENU_TEXT,
            MENU_OPTIONS,
        )

    async def _show_products(self, sender_id: str, *_) -> None:
        await self.service.send_text(sender_id, PRODUCTS_TEXT)

    async def _show_hours(self, sender_id: str, *_) -> None:
        await self.service.send_text(sender_id, HOURS_TEXT)

    async def _start_support(self, sender_id: str, session=None) -> None:
        if session is None:
            session = await self.sessions.get(sender_id)
        session.state = "support_open"
        await self.sessions.save(session)
        await self.service.send_text(
            sender_id,
            "📝 Certo! Por favor, descreva o seu problema em detalhes "
            "e nossa equipe entrará em contato em breve.",
        )

    async def _start_support_postback(self, sender_id: str) -> None:
        await self._start_support(sender_id)

    async def _handle_support(self, sender_id: str, text: str, session) -> None:
        # Aqui você poderia salvar o relato em banco de dados / abrir um ticket
        session.state = "initial"
        session.data["last_support_report"] = text
        await self.sessions.save(session)
        await self.service.send_text(
            sender_id,
            "✅ Relato recebido! Nossa equipe analisará sua solicitação "
            "e entrará em contato em até 24 horas úteis. "
            "Há mais algo em que posso ajudar?",
        )
        await self._handle_greeting(sender_id)

    async def _transfer_to_agent(self, sender_id: str) -> None:
        await self.service.send_text(
            sender_id,
            "👤 Transferindo para um atendente humano. "
            "Aguarde um momento, por favor.",
        )

    async def _handle_fallback(self, sender_id: str, text: str) -> None:
        """
        Fallback para mensagens não reconhecidas.

        💡 Dica: integre um LLM aqui para respostas mais inteligentes.
        Veja o README para um exemplo com OpenAI.
        """
        await self.service.send_text(
            sender_id,
            "Não entendi muito bem. 🤔 Veja o que posso fazer por você:",
        )
        await self._handle_greeting(sender_id)
