"""Messenger webhook — multi-tenant: each company has their own Facebook page."""
import hashlib
import hmac
import os
import logging
import httpx
from fastapi import APIRouter, Request, HTTPException, Query
from dotenv import load_dotenv
from nilechat import reply as nilechat_reply
from db import get_company_by_messenger_page_id

load_dotenv()
logger = logging.getLogger(__name__)

VERIFY_TOKEN = os.getenv("MESSENGER_VERIFY_TOKEN")
APP_SECRET   = os.getenv("MESSENGER_APP_SECRET", "")

# Fallback global token (for the single Jadore page we set up manually)
GLOBAL_PAGE_TOKEN = os.getenv("MESSENGER_PAGE_ACCESS_TOKEN")
GLOBAL_PAGE_ID    = os.getenv("MESSENGER_PAGE_ID", "")  # optional, set if needed

GRAPH_API_URL = "https://graph.facebook.com/v19.0/me/messages"

router = APIRouter(prefix="/webhook/messenger", tags=["messenger"])


def _verify_signature(body: bytes, signature_header: str) -> bool:
    if not APP_SECRET:
        logger.warning("MESSENGER_APP_SECRET not set — skipping signature check")
        return True
    if not signature_header or not signature_header.startswith("sha1="):
        return False
    expected = hmac.new(APP_SECRET.encode(), body, hashlib.sha1).hexdigest()
    return hmac.compare_digest(f"sha1={expected}", signature_header)


async def _send_message(psid: str, text: str, page_token: str) -> bool:
    payload = {"recipient": {"id": psid}, "message": {"text": text}}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                GRAPH_API_URL, json=payload, params={"access_token": page_token}
            )
            r.raise_for_status()
            logger.info(f"Messenger message sent to PSID {psid}")
            return True
    except httpx.HTTPStatusError as e:
        logger.error(f"Messenger API error {e.response.status_code}: {e.response.text}")
        return False
    except httpx.RequestError as e:
        logger.error(f"Network error sending to Messenger: {e}")
        return False


@router.get("")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("")
async def receive_message(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature", "")

    if not _verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()
    logger.info(f"Messenger webhook: {data}")

    if data.get("object") != "page":
        return {"status": "ok"}

    try:
        for entry in data.get("entry", []):
            # recipient.id is the page ID
            page_id = entry.get("id", "")

            # Look up company by page ID — fall back to global token if not found
            company = await get_company_by_messenger_page_id(page_id)
            if company:
                page_token = company["messenger_page_token"]
                company_name   = company["name"]
                knowledge_base = company["knowledge_base"]
                company_id     = company["id"]
            else:
                page_token     = GLOBAL_PAGE_TOKEN
                company_name   = None
                knowledge_base = None
                company_id     = None

            if not page_token:
                logger.warning(f"No page token for page_id={page_id}. Skipping.")
                continue

            for messaging in entry.get("messaging", []):
                sender_psid = messaging.get("sender", {}).get("id")
                msg = messaging.get("message", {})

                if not sender_psid or not msg or msg.get("is_echo"):
                    continue

                text = msg.get("text")
                if not text:
                    continue

                logger.info(f"Messenger from PSID {sender_psid} (page {page_id}): {text}")

                bot_reply = await nilechat_reply(
                    user_text=text,
                    phone=f"messenger_{sender_psid}",
                    platform="messenger",
                    company_id=company_id,
                    company_name=company_name,
                    knowledge_base=knowledge_base,
                )

                await _send_message(sender_psid, bot_reply, page_token)

    except Exception as e:
        logger.exception(f"Error processing Messenger message: {e}")

    return {"status": "ok"}
