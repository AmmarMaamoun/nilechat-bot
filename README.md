# NileChat

**A multi-tenant AI customer service platform for Arabic-speaking businesses, powered by a dialect-specific LLM and deployable across web, WhatsApp, and Messenger from a single backend.**

---

## Introduction

Most small and mid-sized businesses in the Arabic-speaking world face the same wall when they try to add AI-driven customer support: the available chatbot platforms are built for English, for Modern Standard Arabic at best, and for enterprises with the budget and technical staff to integrate them. NileChat exists to close that gap. It gives a business owner a working, on-brand AI support agent — one that actually replies the way a local customer expects to be spoken to — without hiring a developer or waiting on a platform's enterprise sales team.

The aim is straightforward: let one business, through one short onboarding step, get an AI agent that knows their business and is reachable everywhere their customers already are — their website, their WhatsApp number, their Facebook Page — instead of forcing customers onto yet another proprietary app. Underneath that simplicity is a genuinely multi-tenant SaaS architecture: a single backend and a single database schema serve every business on the platform, isolated cleanly by tenant, so the system scales by adding rows, not servers.

This project is aimed at two audiences at once, and is worth reading closely by both. For a **business or agency owner**, it's a working answer to "can I get an Arabic-native AI support bot without building one myself." For a **technical reviewer** — a recruiter, a tech lead, a fellow engineer — it's a compact but non-trivial systems project: real multi-tenancy, three separate messaging integrations (one of them entirely unofficial and self-serve), a large language model consumed through a non-standard streaming protocol, and the production-hygiene details that separate a weekend prototype from something that could actually run a business's customer support. The sections below walk through how it's built, why it's built that way, and how to run it yourself.

## Architecture

To see how NileChat actually delivers on that, it helps to follow a single message through the system: a customer types something on a website, in WhatsApp, or in Messenger, and — regardless of which channel it came from — the same backend resolves who they're talking to, what that business knows, and what the AI should say back.

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

Each channel is an isolated router mounted onto the same FastAPI app, all converging on a single `nilechat.reply()` pipeline that resolves conversation history, applies the tenant's system prompt, calls the model, and persists the exchange. Nothing about the AI logic, the database, or the tenant model is duplicated per channel — the channels are just different doors into the same room.

### Component breakdown

Reading top to bottom, this is roughly the order a request passes through the codebase:

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

A few decisions in this codebase weren't the "default" choice, and each one exists because the obvious approach didn't hold up against a real constraint:

**Dual WhatsApp integration.** Most SMBs in the target market don't have WhatsApp Business Cloud API access, which requires Meta Business verification. Alongside the official Cloud API webhook (`whatsapp.py`), the platform ships a second path: a Node.js microservice (`whatsapp-service/`) built on `whatsapp-web.js`, running one headless Puppeteer session per tenant behind a QR-code pairing flow. A business connects its existing WhatsApp number the same way it would on WhatsApp Web, no API approval required.

**Non-standard model integration.** Nile-Chat-12B is served from a public Gradio Space rather than a completions endpoint. There's no simple request/response call available — the client warms the Space, submits a job, and consumes a server-sent-event stream to recover the final generation. This is handled directly over `httpx` rather than a synchronous client library, so the async request lifecycle isn't blocked while the model streams.

**Self-serve Messenger onboarding.** Rather than requiring a business to hand over a page access token manually, `messenger_oauth.py` implements the full Facebook Login exchange: redirect → code exchange → page discovery → webhook subscription → token storage, all triggered from a single "Connect" action in the dashboard.

**Webhook security.** Both WhatsApp and Messenger webhooks verify Meta's request signature (`X-Hub-Signature-256` / `X-Hub-Signature`) via HMAC before processing a payload, and both always return `200` on internal errors to prevent Meta's retry storms — while WhatsApp Cloud API sends carry their own retry/backoff loop for `429` responses.

**Pooler-aware persistence.** Async PostgreSQL access runs through Supabase's transaction-mode pooler, which requires `statement_cache_size=0` on `asyncpg` — a detail that silently breaks otherwise-correct code if missed.

## Technology

Every design decision above is implemented with a fairly small, deliberate set of tools rather than a heavy framework stack:

- **Backend:** Python 3.11, FastAPI, Uvicorn
- **AI Model:** Nile-Chat-12B (`MBZUAI-Paris/Nile-Chat-12B`) via HuggingFace Spaces
- **Database:** PostgreSQL via Supabase, with the `pgvector` extension
- **WhatsApp (self-serve path):** Node.js, `whatsapp-web.js`, Puppeteer
- **Messenger / WhatsApp Cloud:** Meta Graph API v19.0
- **Dev tunneling:** ngrok

## Dependencies

Each dependency below earns its place in one of the components already described — nothing here is boilerplate scaffolding.

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

With the architecture in mind, here's what actually happens on screen — first from the seat of the business operator setting a tenant up, then from the seat of their customer.

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

**As an end customer**, none of that setup is visible — the experience is channel-native: a chat bubble on the website, a normal WhatsApp conversation, or a normal Messenger conversation. The tenant, model, and conversation memory are all resolved transparently on the backend, so the same question asked twice, a day apart, still gets a reply grounded in the same knowledge base and the same conversation history.

Full endpoint reference lives in-code in each router; the admin, web-chat, and OAuth surfaces are summarized in the table above.

## Running locally

Everything described so far is running code, not a diagram. To bring it up on your own machine:

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

Taken together, the pieces above add up to more than "a chatbot with a database." A few things are worth calling out explicitly for anyone evaluating this as a piece of engineering work:

- **Real multi-tenancy, not a single-bot demo.** One schema, one deployment, unlimited businesses — isolation is enforced at the data layer (`api_key`, `company_id` scoping), not by spinning up separate instances.
- **Solves a real adoption barrier.** The dual WhatsApp path (Cloud API + QR fallback) exists because most small businesses can't clear Meta's Business verification — this is a deliberate product decision, not just a technical exercise.
- **Integrates a model with no conventional API.** Reverse-engineering a Gradio Space's queue/event-stream protocol into a clean async function is a non-trivial integration problem most projects don't encounter.
- **Production-conscious details throughout:** webhook signature verification, retry-with-backoff on outbound sends, a documented pooler compatibility fix, and secrets kept out of version control from the start (`.env` is gitignored; nothing in this repository's history contains a live credential).
- **Spans three distinct integration surfaces** — a public REST/OAuth API, an official messaging platform webhook, and a browser-automation-based unofficial client — under one coherent backend, which is a broader systems-integration exercise than any single channel would demonstrate alone.

In short: NileChat is a working answer to a real, underserved market need, built with the kind of multi-tenant architecture and integration depth that scales past a single demo — which is exactly what makes it worth a closer look, whether you're the business it could support or the reviewer deciding whether its author can build one.
