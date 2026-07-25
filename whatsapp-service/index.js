/**
 * NileChat WhatsApp QR Service
 * Each company connects their own WhatsApp number by scanning a QR code.
 * Receives messages → forwards to Python backend → sends reply back.
 */
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const express = require('express');
const qrcode = require('qrcode');
const axios = require('axios');
require('dotenv').config({ path: '../.env' });

const app = express();
app.use(express.json());

const PORT = process.env.WA_SERVICE_PORT || 3001;
const PYTHON_BACKEND = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';

// Store active clients per company
const clients = {};   // companyId → WhatsApp Client
const qrCodes = {};   // companyId → base64 QR image
const status  = {};   // companyId → 'connecting' | 'ready' | 'disconnected'

// ── Start / connect a company's WhatsApp ──────────────────────────────────
function createClient(companyId) {
  if (clients[companyId]) {
    clients[companyId].destroy().catch(() => {});
  }

  status[companyId]  = 'connecting';
  qrCodes[companyId] = null;

  const client = new Client({
    authStrategy: new LocalAuth({ clientId: `company-${companyId}` }),
    puppeteer: {
      headless: true,
      executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
    },
  });

  client.on('qr', async (qr) => {
    qrCodes[companyId] = await qrcode.toDataURL(qr);
    status[companyId]  = 'qr_ready';
    console.log(`[Company ${companyId}] QR ready`);
  });

  client.on('ready', () => {
    status[companyId]  = 'ready';
    qrCodes[companyId] = null;
    console.log(`[Company ${companyId}] WhatsApp connected ✅`);
  });

  client.on('disconnected', (reason) => {
    status[companyId] = 'disconnected';
    console.log(`[Company ${companyId}] Disconnected: ${reason}`);
  });

  client.on('message', async (msg) => {
    if (msg.fromMe) return;
    if (msg.from.endsWith('@g.us')) return; // skip group messages

    const phone = msg.from.replace('@c.us', '');
    const text  = msg.body;
    console.log(`[Company ${companyId}] Message from ${phone}: ${text}`);

    try {
      const res = await axios.post(`${PYTHON_BACKEND}/webhook/whatsapp-qr`, {
        company_id: companyId,
        phone,
        message: text,
      }, { timeout: 120000 });

      const reply = res.data?.reply;
      if (reply) {
        await msg.reply(reply);
        console.log(`[Company ${companyId}] Replied to ${phone}`);
      }
    } catch (err) {
      console.error(`[Company ${companyId}] Error calling backend:`, err.message);
    }
  });

  client.initialize();
  clients[companyId] = client;
  return client;
}

// ── Routes ────────────────────────────────────────────────────────────────

// Start connection for a company — call this when business clicks "Connect WhatsApp"
app.post('/connect/:companyId', (req, res) => {
  const { companyId } = req.params;
  createClient(companyId);
  res.json({ status: 'connecting', message: 'Client initializing, poll /qr for QR code' });
});

// Get QR code (base64 image) — poll every 2 seconds until status is qr_ready
app.get('/qr/:companyId', (req, res) => {
  const { companyId } = req.params;
  const s = status[companyId];
  const qr = qrCodes[companyId];

  if (s === 'ready') return res.json({ status: 'ready' });
  if (s === 'qr_ready' && qr) return res.json({ status: 'qr_ready', qr });
  if (!s) return res.json({ status: 'not_started' });
  res.json({ status: s });
});

// Connection status
app.get('/status/:companyId', (req, res) => {
  const { companyId } = req.params;
  res.json({ status: status[companyId] || 'not_started' });
});

// Disconnect
app.post('/disconnect/:companyId', async (req, res) => {
  const { companyId } = req.params;
  if (clients[companyId]) {
    await clients[companyId].destroy().catch(() => {});
    delete clients[companyId];
    status[companyId] = 'disconnected';
  }
  res.json({ status: 'disconnected' });
});

// Send message (called from Python if needed)
app.post('/send', async (req, res) => {
  const { company_id, to, message } = req.body;
  const client = clients[company_id];
  if (!client || status[company_id] !== 'ready') {
    return res.status(400).json({ error: 'Client not ready' });
  }
  try {
    await client.sendMessage(`${to}@c.us`, message);
    res.json({ sent: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Health check
app.get('/health', (req, res) => {
  const summary = {};
  for (const id of Object.keys(status)) summary[id] = status[id];
  res.json({ ok: true, sessions: summary });
});

app.listen(PORT, () => {
  console.log(`WhatsApp QR Service running on port ${PORT}`);
});
