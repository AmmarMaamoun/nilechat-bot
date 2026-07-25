"""Bites 2B + 2C + 2D — WhatsApp webhook + reply sender."""
import hashlib
import hmac
import os
import logging
import asyncio
import httpx
from fastapi import APIRouter, Request, HTTPException, Query
from dotenv import load_dotenv
from nilechat import reply as nilechat_reply

load_dotenv()
logger = logging.getLogger(__name__)

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET")

router = APIRouter(prefix="/webhook/whatsapp", tags=["whatsapp"])

GRAPH_API_URL = "https://graph.facebook.com/v19.0"


def _verify_signature(body: bytes, signature_header: str) -> bool:
    """Bite 2B: verify Meta webhook signature."""
    if not WHATSAPP_APP_SECRET:
        logger.warning("WHATSAPP_APP_SECRET not set — skipping signature check")
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        WHATSAPP_APP_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature_header)


async def send_whatsapp_message(to: str, text: str) -> bool:
    """Bite 2C: send text reply via WhatsApp Cloud API with retry logic."""
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        raise EnvironmentError("WHATSAPP_TOKEN or WHATSAPP_PHONE_NUMBER_ID missing")

    url = f"{GRAPH_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    for attempt in range(1, 4):  # max 3 attempts
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning(f"Rate limited — waiting {wait}s (attempt {attempt})")
                    await asyncio.sleep(wait)
                    continue

                response.raise_for_status()
                logger.info(f"WhatsApp message sent to {to}")
                return True

        except httpx.HTTPStatusError as e:
            logger.error(f"WhatsApp API error {e.response.status_code}: {e.response.text}")
            return False
        except httpx.RequestError as e:
            logger.error(f"Network error on attempt {attempt}: {e}")
            if attempt == 3:
                return False
            await asyncio.sleep(1)

    return False


@router.get("")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Bite 2B: webhook verification handshake from Meta."""
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("")
async def receive_message(request: Request):
    """Bite 2D: receive WhatsApp message → NileChat → send reply."""
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not _verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()
    logger.info(f"WhatsApp webhook: {data}")

    try:
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return {"status": "ok"}

        msg = messages[0]
        if msg.get("type") != "text":
            return {"status": "ok"}  # phase 1: text only

        sender = msg["from"]
        text = msg["text"]["body"]
        logger.info(f"WhatsApp from {sender}: {text}")

        # Bite 2D: NileChat with memory
        bot_reply = await nilechat_reply(
            user_text=text,
            phone=sender,
            platform="whatsapp",
        )

        await send_whatsapp_message(sender, bot_reply)

    except Exception as e:
        logger.exception(f"Error processing WhatsApp message: {e}")
        # Always return 200 so Meta doesn't retry flood

    return {"status": "ok"}
