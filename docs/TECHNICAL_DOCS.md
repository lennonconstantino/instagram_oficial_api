# Documentação Técnica e Funcional
## Instagram Chatbot API — v1.0.0

---

## Sumário

1. [Arquitetura do Sistema](#arquitetura)
2. [Configuração e Variáveis de Ambiente](#configuracao)
3. [Modelos de Dados (Pydantic)](#modelos)
4. [Camada de Serviço — InstagramService](#servico)
5. [Repositório de Sessões](#repositorio)
6. [Handler do Chatbot](#handler)
7. [Routers e Endpoints](#routers)
8. [Segurança do Webhook](#seguranca)
9. [Fluxo de Dados Completo](#fluxo)
10. [Guia de Produção](#producao)
11. [Referência de Erros](#erros)

---

## 1. Arquitetura do Sistema {#arquitetura}

O sistema é dividido em camadas com responsabilidades bem definidas, seguindo o princípio de separação de preocupações:

```
┌─────────────────────────────────────────────────────┐
│                    Meta / Instagram                  │
│         (Graph API + Messenger API + Webhooks)       │
└────────────────────────┬────────────────────────────┘
                         │ HTTPS
┌────────────────────────▼────────────────────────────┐
│                 FastAPI Application                  │
│  ┌──────────────────────────────────────────────┐   │
│  │                   Routers                    │   │
│  │  /webhook  │  /instagram/*  │  /health       │   │
│  └──────┬─────────────┬────────────────┬────────┘   │
│         │             │                │            │
│  ┌──────▼──────┐ ┌────▼──────┐        │            │
│  │   Chatbot   │ │  Service  │        │            │
│  │   Handler   │ │(Graph API)│        │            │
│  └──────┬──────┘ └────┬──────┘        │            │
│         │             │                │            │
│  ┌──────▼──────┐      │                │            │
│  │  Session    │      │                │            │
│  │ Repository  │      │                │            │
│  └─────────────┘      │                │            │
└───────────────────────┼────────────────┼────────────┘
                        │                │
              Send API / Graph API     Health
```

### Componentes Principais

| Componente | Arquivo | Responsabilidade |
|---|---|---|
| `Settings` | `configs/config.py` | Carrega variáveis de ambiente com validação |
| `InstagramService` | `services/instagram.py` | Comunicação HTTP com a Meta API |
| `SessionRepository` | `repositories/session.py` | Persistência do estado de conversa por usuário |
| `ChatbotHandler` | `handlers/chatbot.py` | Lógica de conversa e roteamento de mensagens |
| `webhook router` | `routers/webhook.py` | Recebimento e validação de eventos da Meta |
| `instagram router` | `routers/instagram.py` | Endpoints da Graph API |

---

## 2. Configuração e Variáveis de Ambiente {#configuracao}

### Arquivo: `configs/config.py`

Utiliza `pydantic-settings` para carregar e validar variáveis de ambiente automaticamente.

```python
class Settings(BaseSettings):
    instagram_access_token: str   # Page Access Token
    instagram_app_id: str         # ID do App no Meta
    instagram_app_secret: str     # Secret para validação HMAC
    instagram_verify_token: str   # Token de verificação do webhook
    instagram_api_version: str    # Versão da API (padrão: v21.0)
```

### Variáveis Obrigatórias

| Variável | Tipo | Descrição |
|---|---|---|
| `INSTAGRAM_ACCESS_TOKEN` | `str` | Page Access Token de longa duração |
| `INSTAGRAM_APP_ID` | `str` | ID do App no Meta Developer Portal |
| `INSTAGRAM_APP_SECRET` | `str` | Secret usado na validação HMAC-SHA256 |
| `INSTAGRAM_VERIFY_TOKEN` | `str` | Token para verificação do webhook |

### Variáveis Opcionais

| Variável | Padrão | Descrição |
|---|---|---|
| `INSTAGRAM_API_VERSION` | `v21.0` | Versão da Graph API |

---

## 3. Modelos de Dados (Pydantic) {#modelos}

### Arquivo: `models/webhook.py`

#### Graph API — Modelos de Resposta

**`InstagramProfile`** — Dados do perfil Business/Creator
```
id, name, biography, followers_count, follows_count,
media_count, profile_picture_url, website, username
```

**`InstagramMedia`** — Post individual
```
id, caption, media_type, media_url, permalink,
thumbnail_url, timestamp, like_count, comments_count
```

**`PaginatedMedia`** — Resposta paginada de mídias
```
data: list[InstagramMedia]
next_cursor: Optional[str]   ← cursor para a próxima página
```

**`PublishMediaRequest`** — Payload para publicação
```
image_url: HttpUrl    ← URL pública acessível pela Meta
caption: Optional[str]
```

---

#### Webhook / Messenger API — Modelos de Evento

**`WebhookPayload`** — Payload raiz enviado pela Meta
```
object: str           ← sempre "instagram" para eventos IG
entry: list[WebhookEntry]
```

**`WebhookEntry`** — Entrada de evento
```
id: str
time: int
messaging: list[WebhookMessaging]
```

**`WebhookMessaging`** — Evento individual de mensagem
```
sender: WebhookSender       ← contém o PSID do usuário
recipient: WebhookRecipient ← contém o ID da página
timestamp: int
message: Optional[WebhookMessage]
postback: Optional[WebhookPostback]
```

**`WebhookMessage`** — Mensagem de texto ou mídia
```
mid: str                                ← Message ID
text: Optional[str]
attachments: Optional[list[WebhookMessageAttachment]]
```

**`WebhookPostback`** — Clique em botão ou quick reply
```
mid: str
payload: str    ← valor configurado no botão (ex: "PRODUTOS")
title: str      ← texto exibido ao usuário
```

---

#### Sessão do Usuário

**`UserSession`** — Estado de conversa
```
user_id: str
state: str = "initial"    ← estado atual do fluxo
data: dict = {}           ← dados arbitrários (ex: relato de suporte)
created_at: datetime
updated_at: datetime
```

**Estados disponíveis:**
- `initial` — aguardando interação, exibe menu
- `support_open` — aguardando descrição do problema pelo usuário

---

## 4. Camada de Serviço — InstagramService {#servico}

### Arquivo: `services/instagram.py`

Responsável por toda comunicação HTTP com a Meta API. Usa `httpx.AsyncClient` com timeout de 30 segundos.

### Métodos — Graph API

#### `get_profile(ig_user_id: str) → InstagramProfile`
Consulta dados públicos do perfil.
- **Endpoint:** `GET /{ig_user_id}?fields=...`
- **Campos retornados:** id, name, biography, followers_count, follows_count, media_count, profile_picture_url, website, username

#### `get_media(ig_user_id, limit, after) → PaginatedMedia`
Lista mídias do perfil com paginação por cursor.
- **Endpoint:** `GET /{ig_user_id}/media`
- **Parâmetros:** `limit` (1–50), `after` (cursor da página anterior)

#### `publish_image(ig_user_id, image_url, caption) → dict`
Publica uma imagem no feed. Processo em dois passos:
1. `POST /{ig_user_id}/media` — cria container e obtém `creation_id`
2. `POST /{ig_user_id}/media_publish` — publica o container

> ⚠️ A `image_url` deve ser uma URL HTTPS pública acessível pelos servidores da Meta.

#### `get_media_insights(media_id) → dict`
Retorna métricas de um post: `engagement`, `impressions`, `reach`, `saved`.

#### `get_account_insights(ig_user_id) → dict`
Retorna métricas da conta por período diário: `follower_count`, `impressions`, `reach`, `profile_views`.

---

### Métodos — Send API (Mensagens Diretas)

#### `send_text(recipient_id, text) → dict`
Envia mensagem de texto simples.
```json
{
  "recipient": { "id": "PSID" },
  "message": { "text": "Olá!" }
}
```

#### `send_quick_replies(recipient_id, text, options) → dict`
Envia mensagem com botões de resposta rápida.
```json
{
  "recipient": { "id": "PSID" },
  "message": {
    "text": "Como posso ajudar?",
    "quick_replies": [
      { "content_type": "text", "title": "Produtos", "payload": "PRODUTOS" }
    ]
  }
}
```

#### `send_generic_template(recipient_id, elements) → dict`
Envia carrossel de cards. Cada elemento pode ter: `title`, `subtitle`, `image_url`, `buttons`.

---

## 5. Repositório de Sessões {#repositorio}

### Arquivo: `repositories/session.py`

Gerencia o estado de conversa de cada usuário via dicionário em memória.

| Método | Descrição |
|---|---|
| `get(user_id)` | Retorna a sessão ou cria uma nova com estado `initial` |
| `save(session)` | Persiste a sessão e atualiza `updated_at` |
| `reset(user_id)` | Reinicia a sessão para o estado inicial |
| `delete(user_id)` | Remove a sessão completamente |

### Migração para Redis (Produção)

```python
import aioredis
import json

class SessionRepository:
    def __init__(self, redis: aioredis.Redis, ttl: int = 86400):
        self.redis = redis
        self.ttl = ttl  # 24 horas

    async def get(self, user_id: str) -> UserSession:
        data = await self.redis.get(f"session:{user_id}")
        if data:
            return UserSession.model_validate_json(data)
        return UserSession(user_id=user_id)

    async def save(self, session: UserSession) -> None:
        session.updated_at = datetime.utcnow()
        await self.redis.set(
            f"session:{user_id}",
            session.model_dump_json(),
            ex=self.ttl
        )
```

---

## 6. Handler do Chatbot {#handler}

### Arquivo: `handlers/chatbot.py`

Implementa a máquina de estados da conversa e despacha mensagens para os handlers corretos.

### Diagrama de Estados

```
          ┌─────────────────────────────────┐
          │           [initial]              │
          │                                  │
          │  "produtos" → show_products      │
          │  "suporte"  → [support_open]     │
          │  "horarios" → show_hours         │
          │  "atendente"→ transfer_to_agent  │
          │  <outro>    → handle_fallback    │
          └───────────────────┬─────────────┘
                              │ "suporte"
                   ┌──────────▼──────────┐
                   │   [support_open]     │
                   │                      │
                   │  <qualquer texto>    │
                   │  → handle_support   │
                   │  → volta a [initial]│
                   └─────────────────────┘
```

### Métodos Públicos

| Método | Trigger | Descrição |
|---|---|---|
| `handle_message(sender_id, text)` | Mensagem de texto | Despacha para o handler do estado atual |
| `handle_postback(sender_id, payload)` | Clique em botão | Roteia pelo payload (PRODUTOS, SUPORTE, HORARIOS) |

### Métodos Privados

| Método | Estado Alvo | Ação |
|---|---|---|
| `_handle_greeting` | — | Exibe menu com quick replies |
| `_show_products` | — | Lista produtos com texto formatado |
| `_show_hours` | — | Exibe horário de funcionamento |
| `_start_support` | `support_open` | Solicita descrição do problema |
| `_handle_support` | `initial` | Salva relato e volta ao menu |
| `_transfer_to_agent` | — | Mensagem de transferência para humano |
| `_handle_fallback` | — | Reapresenta menu para texto não reconhecido |

---

## 7. Routers e Endpoints {#routers}

### Webhook (`routers/webhook.py`)

#### `GET /webhook` — Verificação do Challenge

Chamado pela Meta ao cadastrar o webhook. Responde com `hub.challenge` se o `hub.verify_token` for válido.

**Query params:**
- `hub.mode` — deve ser `"subscribe"`
- `hub.verify_token` — deve coincidir com `INSTAGRAM_VERIFY_TOKEN`
- `hub.challenge` — string que deve ser retornada

**Respostas:**
- `200` — retorna o valor de `hub.challenge`
- `403` — verify token inválido

---

#### `POST /webhook` — Recebimento de Eventos

Recebe e processa eventos (mensagens e postbacks) enviados pela Meta.

**Headers obrigatórios:**
- `X-Hub-Signature-256: sha256=<hmac-hex>`

**Processamento:**
1. Valida assinatura HMAC-SHA256
2. Desserializa o payload via `WebhookPayload`
3. Itera sobre `entry[].messaging[]`
4. Despacha para `ChatbotHandler.handle_message` ou `handle_postback`
5. Retorna `{"status": "ok"}` imediatamente

> ⚠️ Erros individuais de processamento são capturados e logados — o webhook nunca retorna 5xx para evitar re-tentativas da Meta.

---

### Graph API (`routers/instagram.py`)

| Método | Rota | Parâmetros | Descrição |
|---|---|---|---|
| `GET` | `/instagram/profile/{ig_user_id}` | — | Perfil do usuário |
| `GET` | `/instagram/media/{ig_user_id}` | `limit`, `after` | Mídias paginadas |
| `POST` | `/instagram/media/{ig_user_id}/publish` | `body: PublishMediaRequest` | Publica imagem |
| `GET` | `/instagram/media/{media_id}/insights` | — | Métricas do post |
| `GET` | `/instagram/account/{ig_user_id}/insights` | — | Métricas da conta |

---

### Health (`routers/health.py`)

#### `GET /health`

Retorna o status da aplicação e o timestamp atual.

```json
{
  "status": "ok",
  "timestamp": "2025-02-25T14:30:00.000000"
}
```

---

## 8. Segurança do Webhook {#seguranca}

### Validação de Assinatura HMAC-SHA256

Cada requisição POST da Meta inclui o cabeçalho:
```
X-Hub-Signature-256: sha256=<hmac-hex>
```

A função `_verify_signature` calcula o HMAC esperado e compara com `hmac.compare_digest` (tempo constante, resistente a timing attacks):

```python
def _verify_signature(body: bytes, signature_header: str) -> bool:
    expected = hmac.new(
        settings.instagram_app_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)
```

### Boas Práticas de Segurança

- Nunca exponha `INSTAGRAM_APP_SECRET` em logs
- Use variáveis de ambiente ou cofres (AWS Secrets Manager, Vault)
- Sempre valide a assinatura antes de processar o payload
- Responda ao webhook em menos de 5 segundos (processe assincronamente para tarefas longas)
- Implemente rate limiting para evitar abuso dos endpoints da Graph API

---

## 9. Fluxo de Dados Completo {#fluxo}

### Cenário: Usuário envia "Suporte" pelo DM do Instagram

```
1. Usuário digita "Suporte" no DM do Instagram

2. Meta envia POST /webhook com payload:
   {
     "object": "instagram",
     "entry": [{
       "messaging": [{
         "sender": { "id": "USER_PSID" },
         "message": { "mid": "...", "text": "Suporte" }
       }]
     }]
   }

3. routers/webhook.py:
   - Valida X-Hub-Signature-256 (HMAC-SHA256)
   - Desserializa → WebhookPayload
   - Extrai sender_id = "USER_PSID", text = "Suporte"
   - Chama chatbot.handle_message("USER_PSID", "Suporte")

4. handlers/chatbot.py:
   - Carrega session = SessionRepository.get("USER_PSID")
   - session.state == "initial" → roteia para _start_support()
   - Atualiza session.state = "support_open"
   - Salva sessão

5. services/instagram.py:
   - POST /me/messages com texto pedindo descrição
   - Meta entrega a mensagem ao usuário

6. Usuário responde com a descrição do problema

7. routers/webhook.py:
   - Mesmo fluxo de validação
   - Chama chatbot.handle_message("USER_PSID", "<descrição>")

8. handlers/chatbot.py:
   - session.state == "support_open" → _handle_support()
   - Salva relato em session.data["last_support_report"]
   - Reseta session.state = "initial"
   - Envia confirmação + reapresenta menu
```

---

## 10. Guia de Produção {#producao}

### Infraestrutura Recomendada

```
Internet → Nginx/Load Balancer (HTTPS/TLS)
              ↓
         Gunicorn + Uvicorn Workers
              ↓
         FastAPI Application
              ↓
         Redis (sessões) + PostgreSQL (relatos/logs)
```

### Configuração do Gunicorn

```bash
gunicorn main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 30 \
  --access-logfile -
```

### Variáveis de Ambiente para Produção

```env
INSTAGRAM_ACCESS_TOKEN=<token-de-longa-duracao>
INSTAGRAM_APP_SECRET=<guardado-em-cofre>
INSTAGRAM_VERIFY_TOKEN=<string-aleatoria-longa>
REDIS_URL=redis://redis:6379/0
```

### Rate Limits da Meta

| Recurso | Limite |
|---|---|
| Send API | 200 mensagens/hora por usuário |
| Graph API | 200 req/hora por token |
| Publicação de mídia | 50 posts/dia |

Para cargas maiores, implemente uma fila com **Celery** ou **RQ**:

```python
# Processamento assíncrono para não bloquear o webhook
@router.post("/webhook")
async def receive_webhook(request: Request):
    body = await request.body()
    # Valida e enfileira — responde imediatamente
    task_queue.enqueue(process_webhook, body)
    return {"status": "ok"}
```

### Logs Estruturados

Configure logging em JSON para facilitar integração com ferramentas como Datadog, CloudWatch ou ELK:

```python
import structlog

log = structlog.get_logger()
log.info("webhook_received", sender_id=sender_id, message_type="text")
```

---

## 11. Referência de Erros {#erros}

### Erros HTTP da Aplicação

| Código | Quando ocorre | Solução |
|---|---|---|
| `400` | Payload do webhook malformado | Verifique o formato enviado pela Meta |
| `403` (challenge) | `hub.verify_token` inválido | Confira `INSTAGRAM_VERIFY_TOKEN` no `.env` e no painel |
| `403` (webhook) | Assinatura HMAC inválida | Verifique `INSTAGRAM_APP_SECRET` |
| `422` | Dados inválidos nos endpoints REST | Corrija os campos enviados na requisição |
| `500` | Erro interno não tratado | Verifique os logs da aplicação |

### Erros da Meta API

| Código | Descrição | Solução |
|---|---|---|
| `100` | Parâmetro inválido | Verifique o `ig_user_id` e campos da requisição |
| `190` | Token de acesso inválido ou expirado | Renove o `INSTAGRAM_ACCESS_TOKEN` |
| `200` | Permissão negada | Solicite a permissão necessária no App |
| `613` | Rate limit atingido | Implemente backoff exponencial e fila |
| `10` | Conta não é Business/Creator | A API só funciona com contas Business ou Creator |

### Tratamento de Erros no Webhook

O webhook nunca deve retornar `5xx`. Erros individuais são capturados e logados:

```python
try:
    await chatbot.handle_message(sender_id, text)
except Exception as exc:
    logger.error("Erro ao processar mensagem de %s: %s", sender_id, exc)
# Sempre retorna 200
return {"status": "ok"}
```

---

*Documentação gerada para Instagram Chatbot API v1.0.0 — Python 3.12+ | FastAPI | Pydantic v2*
