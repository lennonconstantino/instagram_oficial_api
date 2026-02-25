# Instagram Oficial API

> Integração completa com a **Meta API** para Instagram: Graph API (perfil, mídia, insights) + Messenger API (DMs, webhook, chatbot automatizado).
> Construído com **FastAPI**, **Pydantic v2** e **Python 3.12+**.

---

## Visão Geral

```
Usuário envia DM no Instagram
   ↓
Meta envia evento POST ao Webhook
   ↓
FastAPI recebe, valida assinatura HMAC-SHA256 e desserializa o payload
   ↓
ChatbotHandler processa a mensagem e atualiza a sessão do usuário
   ↓
InstagramService envia a resposta via Send API da Meta
```

---

## Funcionalidades

- **Webhook seguro** — verificação de challenge e validação de assinatura HMAC-SHA256
- **Chatbot de atendimento** — fluxo de conversa com estados, quick replies e menu interativo
- **Sessões em memória** — gerenciamento de estado por usuário (substituível por Redis)
- **Graph API** — consulta de perfil, listagem de mídias com paginação e publicação de imagens
- **Insights** — métricas de posts e da conta (engajamento, alcance, impressões)
- **Send API** — envio de texto, quick replies e carrosseis (Generic Template)

---

## Estrutura do Projeto

```
instagram_api/
├── requirements.txt
└── src/
    ├── .env.example
    ├── main.py                    ← Entry point FastAPI
    ├── configs/
    │   └── config.py              ← Variáveis de ambiente (pydantic-settings)
    ├── models/
    │   └── webhook.py             ← Schemas Pydantic (Graph API + Webhook + Session)
    ├── services/
    │   └── instagram.py           ← Graph API + Send API (httpx async)
    ├── repositories/
    │   └── session.py             ← SessionRepository em memória
    ├── handlers/
    │   └── chatbot.py             ← Lógica de conversa e estados
    └── routers/
        ├── webhook.py             ← GET/POST /webhook
        ├── instagram.py           ← Endpoints da Graph API
        └── health.py              ← GET /health
```

---

## Pré-requisitos

- Python 3.12+
- Conta **Business** ou **Creator** no Instagram
- App criado em [developers.facebook.com](https://developers.facebook.com)
- Página do Facebook conectada ao Instagram
- Permissões aprovadas: `instagram_manage_messages`, `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`
- HTTPS obrigatório para webhook (use **ngrok** em desenvolvimento)

---

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/instagram-chatbot-api.git
cd instagram-chatbot-api

# 2. Crie e ative o ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cd src
cp .env.example .env
# Edite o .env com suas credenciais
```

---

## Configuração

Edite `src/.env`:

```env
INSTAGRAM_ACCESS_TOKEN=seu_page_access_token_longa_duracao
INSTAGRAM_APP_ID=seu_app_id
INSTAGRAM_APP_SECRET=seu_app_secret
INSTAGRAM_VERIFY_TOKEN=string-aleatoria-segura
INSTAGRAM_API_VERSION=v21.0
```

> ⚠️ Nunca commite o `.env`. Ele já está no `.gitignore`.

---

## Executando

```bash
cd src
uvicorn main:app --reload --port 8000
```

Acesse a documentação interativa em: [http://localhost:8000/docs](http://localhost:8000/docs)

### Expor via ngrok (desenvolvimento)

```bash
ngrok http 8000
# Copie a URL HTTPS gerada, ex: https://abc123.ngrok.io
```

---

## Configuração no Painel da Meta

| # | Ação |
|---|------|
| 1 | Acesse **developers.facebook.com** → seu App → Configurações |
| 2 | Adicione o produto **Messenger** (cobre Instagram DMs) |
| 3 | Solicite as permissões: `instagram_manage_messages`, `instagram_basic` |
| 4 | Em **Webhooks**, insira a URL: `https://sua-url.ngrok.io/webhook` |
| 5 | Insira o mesmo valor de `INSTAGRAM_VERIFY_TOKEN` do `.env` |
| 6 | Assine os eventos: `messages`, `messaging_postbacks` |
| 7 | Conecte sua Página do Facebook ao app |

---

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/health` | Health check |
| `GET` | `/webhook` | Verificação do challenge pela Meta |
| `POST` | `/webhook` | Recebimento de mensagens e postbacks |
| `GET` | `/instagram/profile/{id}` | Dados do perfil |
| `GET` | `/instagram/media/{id}` | Lista de mídias com paginação |
| `POST` | `/instagram/media/{id}/publish` | Publicar imagem no feed |
| `GET` | `/instagram/media/{id}/insights` | Métricas de um post |
| `GET` | `/instagram/account/{id}/insights` | Métricas da conta |

---

## Fluxo do Chatbot

```
Qualquer mensagem
   └── _handle_greeting()      → menu com quick replies

"Produtos" / payload PRODUTOS
   └── _show_products()        → lista de produtos

"Suporte" / payload SUPORTE
   └── _start_support()        → solicita descrição
   └── _handle_support()       → salva relato + volta ao menu

"Horários" / payload HORARIOS
   └── _show_hours()           → horário de funcionamento

"Atendente"
   └── _transfer_to_agent()    → mensagem de transferência

Texto não reconhecido
   └── _handle_fallback()      → reapresenta menu
```

---

## Obtendo o Access Token

```bash
# Trocar token de curto prazo por longa duração (60 dias)
curl "https://graph.facebook.com/v21.0/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id={APP_ID}
  &client_secret={APP_SECRET}
  &fb_exchange_token={SHORT_TOKEN}"

# Descobrir o Instagram Business Account ID
curl "https://graph.facebook.com/v21.0/me/accounts?access_token={TOKEN}"
```

---

## Checklist para Produção

### Sessões
- [ ] Substituir `SessionRepository` in-memory por **Redis** (`aioredis`) com TTL de 24h

### Tokens
- [ ] Usar **Page Access Token de longa duração** (não expira)
- [ ] Armazenar tokens em cofre (AWS Secrets Manager, HashiCorp Vault)

### Infraestrutura
- [ ] HTTPS obrigatório (Nginx, Caddy ou load balancer)
- [ ] Responder ao webhook em **< 5 segundos** (processe assincronamente)
- [ ] Rate limit da Meta: **200 req/hora por token** — implemente fila (Celery, RQ)
- [ ] Logs estruturados em JSON com `correlation_id`

### Monitoramento
- [ ] Health check em `/health` integrado ao balanceador
- [ ] Alertas para erros 403 (assinatura inválida)

---

## Integrando IA (opcional)

Para respostas mais inteligentes no fallback, integre um LLM no `handlers/chatbot.py`:

```python
from openai import AsyncOpenAI

client = AsyncOpenAI()

async def _handle_fallback(self, sender_id: str, text: str) -> None:
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Você é um atendente simpático e prestativo."},
            {"role": "user", "content": text},
        ]
    )
    await self.service.send_text(sender_id, response.choices[0].message.content)
```

---

## Referências

- [Messenger API for Instagram](https://developers.facebook.com/docs/messenger-platform/instagram)
- [Instagram Graph API](https://developers.facebook.com/docs/instagram-api)
- [Webhook Setup](https://developers.facebook.com/docs/messenger-platform/webhooks)
- [Send API Reference](https://developers.facebook.com/docs/messenger-platform/reference/send-api)
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

---

## Licença

MIT License — veja [LICENSE](LICENSE) para detalhes.
