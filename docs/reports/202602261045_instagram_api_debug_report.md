# Report de Debug — Instagram Chatbot API

**Data:** 2026-02-26 10:45  
**Projeto:** `instagram_oficial_api`  
**Stack:** FastAPI · Python 3.12 · httpx · Pydantic v2 · Meta Graph API  

---

## Sumário Executivo

Durante a sessão de debug foram identificados e corrigidos **três problemas distintos** que impediam o funcionamento do chatbot de DMs no Instagram. Os problemas envolveram configuração de URL base da API, token de acesso inválido e processamento incorreto de eventos de echo do webhook.

---

## Problema 1 — Erro 401: Invalid OAuth Access Token

### Local
`src/core/config/settings.py` → classe `InstagramSettings` → propriedade `base_url`

### Problema
O serviço estava enviando requisições para `graph.facebook.com`, mas o token de acesso utilizado era do tipo **Instagram User Token** (`IGAAL...`), que só é aceito pelo endpoint `graph.instagram.com`. A combinação gerava o erro:

```
HTTP/1.1 401 Unauthorized
{"error": {"message": "Invalid OAuth access token - Cannot parse access token", "code": 190}}
```

### Solução
Alteração da propriedade `base_url` na classe `InstagramSettings`:

```python
# Antes
@property
def base_url(self) -> str:
    return f"https://graph.facebook.com/{self.api_version}"

# Depois
@property
def base_url(self) -> str:
    return f"https://graph.instagram.com/{self.api_version}"
```

### Diagrama — Fluxo de Autenticação

```mermaid
sequenceDiagram
    participant App as FastAPI App
    participant FB as graph.facebook.com
    participant IG as graph.instagram.com

    Note over App,FB: ❌ Situação ANTES (401)
    App->>FB: POST /me/messages<br/>Bearer IGAAL...
    FB-->>App: 401 Cannot parse access token

    Note over App,IG: ✅ Situação DEPOIS (200)
    App->>IG: POST /me/messages<br/>Bearer IGAAL...
    IG-->>App: 200 OK
```

---

## Problema 2 — Erro 400: Usuário Não Encontrado (Echo Loop)

### Local
`src/instagram/routers/webhook.py` → handler `receive_webhook`  
`src/instagram/models/webhook.py` → classe `WebhookMessage`

### Problema
A Meta envia dois tipos de evento de mensagem para o webhook:

1. **Mensagem recebida** — `sender.id` = usuário externo
2. **Echo** — `sender.id` = sua própria conta (`is_echo: true`), confirmando que a mensagem foi enviada

O código não filtrava os eventos de echo, então ao receber a confirmação de uma mensagem enviada, tentava responder para **a própria conta** como se fosse um usuário, gerando:

```
HTTP/1.1 400 Bad Request
{"error": {"message": "Não foi possível encontrar o usuário solicitado.", "error_subcode": 2534014}}
```

Adicionalmente, eventos de **read receipt** (confirmação de leitura) também chegavam sem `message` nem `postback`, causando erros desnecessários.

### Solução

**Passo 1** — Adicionar campo `is_echo` ao modelo Pydantic:

```python
# src/instagram/models/webhook.py
class WebhookMessage(BaseModel):
    mid: str
    text: Optional[str] = None
    attachments: Optional[list[WebhookMessageAttachment]] = None
    is_echo: Optional[bool] = None  # ← campo adicionado
```

**Passo 2** — Filtrar echoes e eventos sem ação no router:

```python
# src/instagram/routers/webhook.py
for messaging in entry.messaging:
    # Ignorar ecos da própria conta
    if messaging.message and messaging.message.is_echo:
        continue

    # Ignorar read receipts e outros eventos sem mensagem/postback
    if not messaging.message and not messaging.postback:
        continue

    sender_id = messaging.sender.id
    # ... processamento normal
```

### Diagrama — Fluxo de Eventos do Webhook

```mermaid
sequenceDiagram
    participant U as Usuário Instagram
    participant M as Meta Platform
    participant W as Webhook /POST
    participant C as ChatbotHandler

    U->>M: Envia DM "Oii"
    M->>W: evento message<br/>sender=789442... (usuário)
    W->>C: handle_message(sender_id, "Oii")
    C->>M: POST /me/messages → resposta ao usuário
    M->>W: evento echo<br/>sender=17841449... (sua conta)<br/>is_echo=true
    W-->>W: ✅ ignorar (is_echo=true)
    M->>W: evento read receipt<br/>(sem message/postback)
    W-->>W: ✅ ignorar (sem message/postback)
```

### Diagrama — Lógica de Filtragem de Eventos

```mermaid
flowchart TD
    A[Evento recebido no webhook] --> B{messaging.message?}
    B -- Sim --> C{is_echo = true?}
    C -- Sim --> D[🚫 Ignorar — Echo]
    C -- Não --> E{tem texto?}
    E -- Sim --> F[✅ handle_message]
    E -- Não --> G[ignorar]
    B -- Não --> H{messaging.postback?}
    H -- Sim --> I[✅ handle_postback]
    H -- Não --> J[🚫 Ignorar — Read Receipt / outro]
```

---

## Visão Geral das Alterações

### Diagrama de Componentes

```mermaid
graph TD
    subgraph Meta Platform
        WH[Webhook Events]
        API[graph.instagram.com]
    end

    subgraph FastAPI App
        R[webhook.py<br/>Router]
        M[webhook.py<br/>Models]
        S[instagram.py<br/>Service]
        C[chatbot.py<br/>Handler]
        CFG[settings.py<br/>Config]
    end

    WH -->|POST /webhook| R
    R -->|valida com| M
    R -->|delega| C
    C -->|envia resposta| S
    S -->|POST /me/messages| API
    CFG -->|base_url| S

    style CFG fill:#f9a,stroke:#f00
    style M fill:#f9a,stroke:#f00
    style R fill:#f9a,stroke:#f00
```

> 🔴 Componentes modificados destacados em vermelho

---

## Tabela de Correções

| # | Arquivo | Alteração | Motivo |
|---|---------|-----------|--------|
| 1 | `src/core/config/settings.py` | `base_url` trocado de `graph.facebook.com` para `graph.instagram.com` | Token IGAAL só é aceito pela API do Instagram |
| 2 | `src/instagram/models/webhook.py` | Campo `is_echo: Optional[bool]` adicionado em `WebhookMessage` | Necessário para filtrar echoes no router |
| 3 | `src/instagram/routers/webhook.py` | Filtro de `is_echo` e eventos sem `message`/`postback` adicionados | Evitar tentativa de responder para a própria conta |

---

## Fluxo Final Corrigido

```mermaid
sequenceDiagram
    participant U as Usuário
    participant M as Meta
    participant F as FastAPI
    participant CH as ChatbotHandler
    participant IS as InstagramService

    U->>M: DM no Instagram
    M->>F: POST /webhook (message event)
    F->>F: Valida HMAC-SHA256
    F->>F: Desserializa WebhookPayload
    F->>F: Filtra is_echo / read receipts
    F->>CH: handle_message(sender_id, text)
    CH->>IS: send_quick_replies(sender_id, ...)
    IS->>M: POST graph.instagram.com/me/messages
    M-->>IS: 200 OK
    M->>F: POST /webhook (echo event, is_echo=true)
    F->>F: ✅ Ignorado
```

---

## Checklist Pós-Correção

- [x] 401 resolvido — endpoint correto (`graph.instagram.com`)
- [x] 400 resolvido — echoes filtrados no webhook
- [x] Read receipts ignorados corretamente
- [ ] Substituir `SessionRepository` in-memory por Redis (backlog)
- [ ] Implementar renovação automática do token (expira em 60 dias)
- [ ] Adicionar testes unitários para os filtros de webhook

---

*Gerado em 2026-02-26 10:45*
