(function () {
  const script = document.currentScript;
  const API_KEY = script.getAttribute("data-api-key");
  const BASE_URL = script.src.replace("/widget.js", "");

  if (!API_KEY) { console.error("NileChat: data-api-key missing"); return; }

  // Generate or restore session ID
  const SESSION_KEY = "nilechat_session_" + API_KEY;
  let sessionId = sessionStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2);
    sessionStorage.setItem(SESSION_KEY, sessionId);
  }

  // ── Styles ────────────────────────────────────────────────────────────────
  const style = document.createElement("style");
  style.textContent = `
    #nc-widget * { box-sizing: border-box; font-family: 'Segoe UI', Tahoma, sans-serif; }
    #nc-bubble {
      position: fixed; bottom: 24px; right: 24px; z-index: 9999;
      width: 56px; height: 56px; border-radius: 50%;
      background: #0a7cff; color: #fff; border: none; cursor: pointer;
      box-shadow: 0 4px 16px rgba(0,0,0,.25);
      font-size: 26px; display: flex; align-items: center; justify-content: center;
      transition: transform .2s;
    }
    #nc-bubble:hover { transform: scale(1.1); }
    #nc-panel {
      position: fixed; bottom: 90px; right: 24px; z-index: 9998;
      width: 340px; max-height: 520px;
      background: #fff; border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0,0,0,.18);
      display: flex; flex-direction: column; overflow: hidden;
      transition: opacity .2s, transform .2s;
    }
    #nc-panel.nc-hidden { opacity: 0; pointer-events: none; transform: translateY(12px); }
    #nc-header {
      background: #0a7cff; color: #fff; padding: 14px 16px;
      font-weight: 700; font-size: 15px; display: flex;
      justify-content: space-between; align-items: center;
    }
    #nc-header span { font-size: 12px; opacity: .8; }
    #nc-close { background: none; border: none; color: #fff; font-size: 20px; cursor: pointer; }
    #nc-messages {
      flex: 1; overflow-y: auto; padding: 12px;
      display: flex; flex-direction: column; gap: 8px;
      background: #f5f7fa;
    }
    .nc-msg {
      max-width: 80%; padding: 9px 13px; border-radius: 14px;
      font-size: 14px; line-height: 1.45; word-break: break-word;
    }
    .nc-msg.nc-bot {
      background: #fff; color: #222; border: 1px solid #e0e0e0;
      align-self: flex-start; border-bottom-left-radius: 4px;
      direction: rtl; text-align: right;
    }
    .nc-msg.nc-user {
      background: #0a7cff; color: #fff;
      align-self: flex-end; border-bottom-right-radius: 4px;
    }
    .nc-typing { display: flex; gap: 4px; align-items: center; padding: 8px 12px; }
    .nc-dot { width: 7px; height: 7px; border-radius: 50%; background: #aaa; animation: nc-bounce .9s infinite; }
    .nc-dot:nth-child(2) { animation-delay: .15s; }
    .nc-dot:nth-child(3) { animation-delay: .3s; }
    @keyframes nc-bounce { 0%,60%,100%{transform:translateY(0)} 30%{transform:translateY(-5px)} }
    #nc-input-row {
      display: flex; gap: 8px; padding: 10px 12px;
      border-top: 1px solid #eee; background: #fff;
    }
    #nc-input {
      flex: 1; border: 1px solid #ddd; border-radius: 20px;
      padding: 8px 14px; font-size: 14px; outline: none;
      resize: none; direction: rtl;
    }
    #nc-input:focus { border-color: #0a7cff; }
    #nc-send {
      background: #0a7cff; color: #fff; border: none;
      border-radius: 50%; width: 38px; height: 38px;
      cursor: pointer; font-size: 16px; display: flex;
      align-items: center; justify-content: center;
      flex-shrink: 0;
    }
    #nc-send:disabled { background: #ccc; cursor: default; }
    #nc-powered { text-align: center; font-size: 10px; color: #bbb; padding: 4px 0 8px; background: #fff; }
  `;
  document.head.appendChild(style);

  // ── DOM ───────────────────────────────────────────────────────────────────
  const wrap = document.createElement("div");
  wrap.id = "nc-widget";
  wrap.innerHTML = `
    <button id="nc-bubble" title="تكلم معانا">💬</button>
    <div id="nc-panel" class="nc-hidden">
      <div id="nc-header">
        <div>
          <div id="nc-company-name">جار التحميل...</div>
          <span>مساعد خدمة العملاء</span>
        </div>
        <button id="nc-close">✕</button>
      </div>
      <div id="nc-messages"></div>
      <div id="nc-input-row">
        <button id="nc-send">➤</button>
        <textarea id="nc-input" rows="1" placeholder="اكتب رسالتك..."></textarea>
      </div>
      <div id="nc-powered">Powered by NileChat</div>
    </div>
  `;
  document.body.appendChild(wrap);

  const panel = document.getElementById("nc-panel");
  const bubble = document.getElementById("nc-bubble");
  const closeBtn = document.getElementById("nc-close");
  const messages = document.getElementById("nc-messages");
  const input = document.getElementById("nc-input");
  const sendBtn = document.getElementById("nc-send");
  const companyNameEl = document.getElementById("nc-company-name");

  // ── Init — load welcome message ───────────────────────────────────────────
  fetch(`${BASE_URL}/chat/welcome?api_key=${API_KEY}`)
    .then(r => r.ok ? r.json() : null)
    .then(data => {
      if (!data) return;
      companyNameEl.textContent = data.company;
      addMsg(data.welcome, "bot");
    })
    .catch(() => { addMsg("أهلاً! كيف أقدر أساعدك؟", "bot"); });

  // ── Toggle panel ──────────────────────────────────────────────────────────
  bubble.addEventListener("click", () => {
    panel.classList.toggle("nc-hidden");
    if (!panel.classList.contains("nc-hidden")) input.focus();
  });
  closeBtn.addEventListener("click", () => panel.classList.add("nc-hidden"));

  // ── Message helpers ───────────────────────────────────────────────────────
  function addMsg(text, who) {
    const div = document.createElement("div");
    div.className = `nc-msg nc-${who}`;
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  function showTyping() {
    const div = document.createElement("div");
    div.className = "nc-msg nc-bot";
    div.innerHTML = '<div class="nc-typing"><div class="nc-dot"></div><div class="nc-dot"></div><div class="nc-dot"></div></div>';
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  // ── Send ──────────────────────────────────────────────────────────────────
  async function send() {
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    sendBtn.disabled = true;
    addMsg(text, "user");
    const typing = showTyping();

    try {
      const res = await fetch(`${BASE_URL}/chat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: API_KEY, session_id: sessionId, message: text }),
      });
      const data = await res.json();
      typing.remove();
      addMsg(data.reply || "معلش، حصل خطأ. حاول تاني.", "bot");
    } catch {
      typing.remove();
      addMsg("مفيش اتصال. حاول تاني.", "bot");
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  sendBtn.addEventListener("click", send);
  input.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 80) + "px";
  });
})();
