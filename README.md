# NileChat SaaS — AI Customer Service Platform

Multi-tenant customer service bot powered by **NileChat** (Egyptian Arabic LLM by MBZUAI-Paris).  
Each business gets their own bot trained on their knowledge base, deployable on 3 channels.

---

## Channels

| Channel | How it works |
|---|---|
| **Web Widget** | One `<script>` tag on any website → floating chat bubble |
| **WhatsApp** | Business scans QR code → connects their existing number |
| **Messenger** | Business clicks "Connect" → Facebook OAuth → page auto-linked |

---

## Architecture

```
dashboard.html  ←→  FastAPI (main.py)  ←→  NileChat (HuggingFace Space)
                           ↕                        ↕
                     Supabase DB          Node.js WhatsApp Service
                     (companies,          (whatsapp-web.js, port 3001)
                      users, messages)
```

---

## Project Structure

```
nilechat-bot/
├── main.py               # FastAPI app entry point, mounts all routers
├── nilechat.py           # NileChat LLM client (HuggingFace Gradio API)
├── db.py                 # Async PostgreSQL layer (asyncpg + Supabase)
├── schema.sql            # Full DB schema — run once in Supabase SQL Editor
├── admin.py              # Admin REST API (create/manage companies)
├── webchat.py            # Web widget chat API
├── messenger.py          # Messenger webhook (multi-tenant)
├── messenger_oauth.py    # Facebook OAuth flow for connecting pages
├── whatsapp.py           # WhatsApp Cloud API webhook
├── whatsapp_qr.py        # WhatsApp QR webhook handler (calls Node.js)
├── static/
│   ├── widget.js         # Embeddable chat widget (single <script> tag)
│   ├── dashboard.html    # Admin dashboard UI
│   └── preview.html      # Widget preview iframe
├── whatsapp-service/
│   ├── index.js          # Node.js WhatsApp QR microservice (port 3001)
│   └── package.json
├── requirements.txt      # Python dependencies
└── .env.example          # Environment variables template
```

---

## Setup

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/nilechat-bot.git
cd nilechat-bot
pip install -r requirements.txt
cd whatsapp-service && npm install && cd ..
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in all values in .env
```

### 3. Set up database

Run `schema.sql` in your **Supabase SQL Editor** (Dashboard → SQL Editor → New query → paste → Run).

### 4. Start services

```bash
# Terminal 1 — Python backend
python main.py

# Terminal 2 — Node.js WhatsApp service
cd whatsapp-service && node index.js
```

### 5. Open dashboard

```
http://localhost:8000/dashboard
```

---

## API Reference

### Admin API (requires `x-admin-key` header)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/admin/companies` | List all companies |
| `POST` | `/admin/companies` | Create company — returns `api_key` + embed snippet |
| `GET` | `/admin/companies/{id}` | Get single company |
| `PUT` | `/admin/companies/{id}/knowledge` | Update knowledge base |
| `POST` | `/admin/companies/{id}/connect-whatsapp` | Start WhatsApp QR session |
| `GET` | `/admin/companies/{id}/whatsapp-qr` | Get QR code (base64) |
| `GET` | `/admin/companies/{id}/whatsapp-status` | Check WhatsApp connection |

### Web Chat API (public, requires `api_key`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/chat/welcome?api_key=...` | Get company name + welcome message |
| `POST` | `/chat/message` | Send message, get AI reply |

### Messenger OAuth

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/messenger-oauth/start?api_key=...` | Start Facebook OAuth |
| `GET` | `/messenger-oauth/callback` | OAuth callback (set this as redirect URI in Meta App) |

---

## Embed Widget

```html
<script src="https://yourdomain.com/widget.js" data-api-key="YOUR_COMPANY_API_KEY"></script>
```

Paste before `</body>` on any website. A chat bubble appears in the bottom-right corner.

---

## Environment Variables

See `.env.example` for the full list with comments.

Key variables:

| Variable | Description |
|---|---|
| `HF_API_KEY` | HuggingFace token (free, read-only) |
| `DATABASE_URL` | Supabase PostgreSQL connection string (pooler, port 6543) |
| `ADMIN_API_KEY` | Protects the admin dashboard and API |
| `BASE_URL` | Public URL of this server (ngrok in dev, VPS domain in prod) |
| `WA_SERVICE_URL` | URL of the Node.js WhatsApp service (default: `http://localhost:3001`) |
| `FB_APP_ID` | Facebook App ID (for Messenger OAuth) |

---

## Tech Stack

- **Backend**: Python 3.11, FastAPI, asyncpg
- **AI**: NileChat 12B (`MBZUAI-Paris/Nile-Chat-12B`) via HuggingFace Gradio API
- **Database**: Supabase (PostgreSQL + pgvector)
- **WhatsApp**: `whatsapp-web.js` (Node.js) for QR-based connections
- **Messenger**: Meta Graph API v19.0 + Facebook Login OAuth
- **Tunnel (dev)**: pyngrok

---

## Notes for the Developer

- `statement_cache_size=0` is required in asyncpg for Supabase's PgBouncer pooler
- NileChat has no native system-prompt support — knowledge base is prepended directly to the user message
- Each company's WhatsApp session is stored in `.wwebjs_auth/session-{companyId}/` (excluded from git)
- The `embedding` column (384-dim vector) exists in the `messages` table for future semantic search
