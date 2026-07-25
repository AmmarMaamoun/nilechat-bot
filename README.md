# NileChat

**A multi-tenant AI customer service platform for Arabic-speaking businesses, powered by a dialect-specific LLM and deployable across web, WhatsApp, and Messenger from a single backend.**

---

## Introduction

Most chatbot platforms are built for English, or Modern Standard Arabic at best, and priced for enterprises. NileChat closes that gap: it gives an Arabic-speaking business a working, dialect-native AI support agent without hiring a developer.

One short onboarding step gets a business an AI agent that knows their business and is reachable on their website, WhatsApp, and Facebook Page. Underneath, it's a genuinely multi-tenant SaaS: one backend, one schema, every business isolated by tenant — the system scales by adding rows, not servers.

The project speaks to two audiences. For a **business owner**, it's a working Arabic-native support bot. For a **technical reviewer**, it's a compact but non-trivial system: real multi-tenancy, three separate messaging integrations, an LLM consumed through a non-standard streaming protocol, and the production-hygiene details that separate a prototype from something that could run a business.

## Architecture

Follow a single message through the system: a customer types something on a website, WhatsApp, or Messenger, and the same backend resolves who they're talking to, what that business knows, and what to reply.

```
                          ┌──────────────────────┐
   Web Widget  ─────────▶ │                      │
   (widget.js)            │                      │
                          │   FastAPI Backend    │ ───▶  Nile-Chat-12B
   WhatsApp Cloud API ───▶│      (main.py)       │       (HuggingFace Space,
   (Meta webhook)         │                      │        Gradio event API)
                          │  6 routers, 1 schema │
   WhatsApp QR Service ──▶│                      │
   (Node microservice)    │                      │ ───▶  PostgreSQL (Supabase)
                          │                      │       + pgvector
   Messenger ─────────────▶│                     │
   (Meta webhook + OAuth)  └──────────────────────┘
```

Each channel is an isolated router mounted on the same FastAPI app, converging on one `nilechat.reply()` pipeline — conversation history, system prompt, model call, persistence. The channels are just different doors into the same room.

### Component breakdown

Roughly the order a request passes through the codebase:

| Layer | Responsibility |
|---|---|
| `main.py` | FastAPI app assembly, router mounting, static asset serving, optional ngrok tunnel bootstrap |
| `nilechat.py` | Model client — conversation memory, per-tenant system prompt construction, response pipeline |
| `db.py` | Async PostgreSQL access layer (connection pooling, tenant/user/conversation/message queries) |
| `admin.py` | Tenant management API — create companies, update knowledge bases, issue embed snippets |
| `webchat.py` | Public web-widget API, authenticated by per-tenant `api_key` |
| `whatsapp.py` | WhatsApp Cloud API webhook — signature verification, message receipt, reply delivery with retry/backoff |
| `whatsapp_qr.py` + `whatsapp-service/index.js` | Self-serve WhatsApp connection for tenants without Cloud API access (see below) |
| `messenger.py` | Messenger webhook — per-page tenant resolution, signature verification |
| `messenger_oauth.py` | Facebook Login flow so a business can connect its own Page in one click |
| `schema.sql` | Full multi-tenant schema, including a `pgvector` column reserved for future semantic search |

### Notable design decisions

A few choices here weren't the default option, each answering a real constraint:

**Dual WhatsApp integration.** Most SMBs can't get WhatsApp Cloud API access, which requires Meta Business verification. Alongside the official webhook (`whatsapp.py`), a Node.js microservice (`whatsapp-service/`, built on `whatsapp-web.js`) runs one Puppeteer session per tenant behind a QR pairing flow — a business connects its existing number, no API approval needed.

**Non-standard model integration.** Nile-Chat-12B is served from a Gradio Space, not a completions endpoint. The client warms the Space, submits a job, and reads a server-sent-event stream for the result — implemented over async `httpx` so the request lifecycle isn't blocked while the model streams.

**Self-serve Messenger onboarding.** `messenger_oauth.py` implements the full Facebook Login exchange — redirect, code exchange, page discovery, webhook subscription, token storage — so a business connects its own Page with one click instead of copy-pasting a token.

**Webhook security.** Both WhatsApp and Messenger webhooks verify Meta's HMAC request signature before processing, and always return `200` on internal errors to avoid Meta's retry storms. WhatsApp sends carry their own retry/backoff on `429`.

**Pooler-aware persistence.** Supabase's transaction-mode pooler requires `statement_cache_size=0` on `asyncpg` — a detail that silently breaks otherwise-correct code if missed.

## Technology

A small, deliberate stack — no heavy framework beyond what each piece above needs:

- **Backend:** Python 3.11, FastAPI, Uvicorn
- **AI Model:** Nile-Chat-12B (`MBZUAI-Paris/Nile-Chat-12B`) via HuggingFace Spaces
- **Database:** PostgreSQL via Supabase, with the `pgvector` extension
- **WhatsApp (self-serve path):** Node.js, `whatsapp-web.js`, Puppeteer
- **Messenger / WhatsApp Cloud:** Meta Graph API v19.0
- **Dev tunneling:** ngrok

## Dependencies

Every dependency here maps to a component described above.

Python (`requirements.txt`):

| Package | Purpose |
|---|---|
| `fastapi` | Web framework and routing |
| `uvicorn[standard]` | ASGI server |
| `httpx` | Async HTTP client — used for the model's SSE stream and all Graph API calls |
| `asyncpg` | Async PostgreSQL driver |
| `pgvector` | Vector type support for the `messages.embedding` column |
| `pydantic` | Request/response validation |
| `python-dotenv` | Environment variable loading |

Node (`whatsapp-service/package.json`):

| Package | Purpose |
|---|---|
| `whatsapp-web.js` | Unofficial WhatsApp Web client — drives the QR pairing session |
| `express` | HTTP API for the microservice (`/connect`, `/qr`, `/status`, `/send`) |
| `qrcode` | Renders the pairing QR as a base64 image for the dashboard |
| `axios` | Forwards inbound WhatsApp messages to the Python backend |
| `dotenv` | Shares the root `.env` with the Node process |

## Usage

What this looks like in practice — first for the operator, then for the customer.

**As a platform operator**, provision a tenant through the admin API:

```
POST /admin/companies
Header: x-admin-key: <ADMIN_API_KEY>
Body:   { "name": "...", "knowledge_base": "...", "welcome_message": "..." }
```

The response includes a generated `api_key` and a ready-to-paste widget snippet. From there:

- **Web:** drop the returned `<script>` tag before `</body>` on the business's site.
- **WhatsApp:** call `POST /admin/companies/{id}/connect-whatsapp`, then poll `GET /admin/companies/{id}/whatsapp-qr` and scan the returned code.
- **Messenger:** send the business to `GET /messenger-oauth/start?api_key=...` to connect their Page via Facebook Login.

**As an end customer**, none of that setup is visible — just a chat bubble, or a normal WhatsApp or Messenger conversation. Tenant, model, and memory are resolved transparently, so the same question asked a day apart still gets a consistent, grounded reply.

Full endpoint reference lives in-code in each router.

## Running locally

```bash
pip install -r requirements.txt
cd whatsapp-service && npm install && cd ..
cp .env.example .env   # fill in HF, Supabase, Meta, and ngrok credentials
```

Provider-specific setup (Supabase project + pgvector, WhatsApp Cloud API/WABA, Meta App + Messenger) is documented step by step in [`docs/`](docs/). Apply `schema.sql` once via the Supabase SQL Editor, then start both services:

```bash
python main.py                              # FastAPI backend, port 8000
cd whatsapp-service && node index.js         # WhatsApp QR microservice, port 3001
```

The dashboard is served at `/dashboard`; if `NGROK_AUTHTOKEN` is set, `main.py` opens a public tunnel automatically on boot and logs the webhook URLs to register with Meta.

## Why this project stands out

- **Real multi-tenancy, not a single-bot demo.** One schema, one deployment, unlimited businesses — isolation enforced at the data layer, not by separate instances.
- **Solves a real adoption barrier.** The dual WhatsApp path exists because most small businesses can't clear Meta's Business verification — a product decision, not just a technical one.
- **Integrates a model with no conventional API.** Turning a Gradio Space's queue/event-stream protocol into a clean async function is a non-trivial integration problem.
- **Production-conscious throughout:** signature verification, retry-with-backoff, a documented pooler fix, and no live credential ever committed to the repo.
- **Three integration surfaces, one backend** — REST/OAuth API, official webhook, and browser-automation client — a broader systems exercise than any single channel alone.

In short: a working answer to an underserved market, built with multi-tenant depth that scales past a single demo.
