"""Redraw the README diagrams: python docs/diagrams/draw_diagrams.py (needs Google Chrome for PNG export)."""
from pathlib import Path

from draw_architecture import Diagram

OUT = Path(__file__).parent

# ---------------- Architecture ----------------
d = Diagram("NileChat · Architecture", "one container, four channels, one reply pipeline")

d.group(30, 110, 250, 760, "Customers", icon="▤")
d.node("web", 155, 390, "web", "Website widget\nwidget.js")
d.node("waqr", 155, 210, "phone", "WhatsApp\n(QR-paired number)")
d.node("wacloud", 155, 570, "phone", "WhatsApp\nCloud API")
d.node("msgr", 155, 750, "phone", "Facebook\nMessenger")

d.group(360, 90, 830, 800, "Docker container · start.sh", style="blue", icon="▣")
d.node("node", 520, 230, "worker", "whatsapp-service\nNode + whatsapp-web.js")
d.node("api", 760, 480, "server", "FastAPI backend\nmain.py · 6 routers")
d.node("reply", 1010, 480, "ai", "nilechat.reply()\nprompt + memory")
d.node("db", 760, 780, "db", "SQLite (WAL)\n/data/nilechat.db")
d.node("dash", 760, 200, "web", "Admin dashboard\n/dashboard")
d.node("sess", 520, 780, "bucket", "WhatsApp sessions\n/data/wa_auth")

d.group(1270, 90, 300, 520, "AI model", style="green", icon="✦")
d.node("nile", 1420, 220, "ai", "Nile-Chat-12B\nHF Space (default)")
d.node("cc", 1420, 470, "ai", "Any /chat/completions\nprovider (optional)")

d.group(1270, 660, 300, 230, "Meta", style="tan", icon="☁")
d.node("graph", 1420, 770, "cloud", "Graph API v19.0")

d.edge("web", "api", "POST /chat/message")
d.edge("waqr", "node", "message")
d.edge("node", "api", "/webhook/whatsapp-qr")
d.edge("wacloud", "api", "signed webhook")
d.edge("msgr", "api", "signed webhook")
d.edge("dash", "api", "x-admin-key")
d.edge("api", "reply")
d.edge("api", "db", "users · conversations · messages")
d.edge("node", "sess", "", dashed=True)
d.edge("reply", "nile", "Gradio job + SSE")
d.edge("reply", "cc", "LLM_PROVIDER", dashed=True)
d.edge("api", "graph", "", dashed=True, color="#7fb0ff")

d.note(870, 405, "every channel → same pipeline", color="#6fdc8c", size=17, rotate=-2)
d.note(300, 905, "no Meta approval needed: scan a QR", color="#6fdc8c", size=17, rotate=-1)
d.note(1290, 640, "swap model with one env var", color="#6fdc8c", size=15, rotate=-2)
d.note(840, 905, "Cloud API path not tied to a company yet", color="#ff6b6b", size=17, rotate=-1)
d.save("architecture", out_dir=OUT)

# ---------------- Message workflow ----------------
w = Diagram("NileChat · Message workflow", "what happens between a customer's question and the bot's answer")

w.group(30, 150, 230, 300, "Customer", icon="▤")
w.node("cust", 145, 300, "phone", "Customer message\nweb / WhatsApp / Messenger")

w.group(320, 150, 1250, 300, "FastAPI backend", style="blue", icon="▣")
w.node("route", 440, 300, "shield", "Channel router: verify,\nfind company by key / page")
w.node("user", 680, 300, "db", "User + conversation\nget or create")
w.node("hist", 920, 300, "redis", "Last messages\ncache → SQLite")
w.node("prompt", 1160, 300, "worker", "System prompt\ncompany knowledge base")
w.node("model", 1420, 300, "ai", "LLM call\nNile-Chat-12B")

w.group(320, 560, 1250, 300, "Save and answer", style="green", icon="✓")
w.node("save", 1420, 710, "db", "Save question\n+ answer")
w.node("cache", 1040, 710, "redis", "Update memory\nlast 10 turns")
w.node("send", 560, 710, "phone", "Reply sent back\non the same channel")

w.edge("cust", "route", "1")
w.edge("route", "user", "2")
w.edge("user", "hist", "3")
w.edge("hist", "prompt", "4")
w.edge("prompt", "model", "5")
w.edge("model", "save", "6 reply text")
w.edge("save", "cache", "7")
w.edge("cache", "send", "8")

w.note(340, 520, "bad Meta signature → 401", color="#6fdc8c", size=16, rotate=-2)
w.note(980, 135, "Egyptian Arabic only · don't invent prices", color="#6fdc8c", size=16, rotate=-1)
w.note(1020, 520, "temperature 0.2 = stick to facts", color="#6fdc8c", size=16, rotate=-2)
w.note(560, 900, "model can still guess when the FAQ is thin → keep the knowledge base rich", color="#ff6b6b", size=17, rotate=-1)
w.save("workflow", out_dir=OUT)

# ---------------- Onboarding ----------------
o = Diagram("NileChat · Onboarding a business", "from new company to a live bot on three channels")

o.group(30, 330, 260, 280, "Operator", icon="▤")
o.node("op", 160, 470, "person", "Operator\n(admin key)")

o.group(360, 330, 300, 280, "Admin API", style="blue", icon="▣")
o.node("create", 510, 470, "server", "POST /admin/companies\nname + knowledge base")

o.group(740, 90, 830, 230, "Website", style="green", icon="▭")
o.node("snippet", 900, 205, "web", "embed_snippet\n<script data-api-key>")
o.node("site", 1380, 205, "web", "Chat bubble live\non the business site")

o.group(740, 360, 830, 230, "WhatsApp (QR)", style="green", icon="▭")
o.node("connect", 900, 475, "worker", "connect-whatsapp\nstart session")
o.node("qr", 1140, 475, "phone", "Poll whatsapp-qr\nshow QR")
o.node("paired", 1380, 475, "phone", "Owner scans\nnumber answers")

o.group(740, 630, 830, 230, "Messenger", style="green", icon="▭")
o.node("oauth", 900, 745, "shield", "/messenger-oauth/start\nFacebook Login")
o.node("page", 1140, 745, "cloud", "Subscribe page\nsave page token")
o.node("live", 1380, 745, "phone", "Page messages\nanswered")

o.edge("op", "create", "1")
o.edge("create", "snippet", "2 api_key")
o.edge("snippet", "site", "paste before </body>")
o.edge("create", "connect", "3")
o.edge("connect", "qr")
o.edge("qr", "paired")
o.edge("create", "oauth", "4")
o.edge("oauth", "page", "code → token")
o.edge("page", "live")

o.note(380, 660, "one key per company =\ndata kept apart", color="#6fdc8c", size=17, rotate=-2)
o.note(60, 900, "sessions saved on disk → reconnect after restart", color="#6fdc8c", size=16, rotate=-1)
o.note(1020, 900, "connects the first page found → let owner pick", color="#ff6b6b", size=16, rotate=-1)
o.save("onboarding", out_dir=OUT)
