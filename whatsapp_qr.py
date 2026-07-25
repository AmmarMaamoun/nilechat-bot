"""WhatsApp QR channel — receives messages from the Node.js whatsapp-web.js service."""
import logging
import os
import httpx
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from dotenv import load_dotenv
from db import get_company_by_id
from nilechat import reply as nilechat_reply

load_dotenv()
logger = logging.getLogger(__name__)

WA_SERVICE_URL = os.getenv("WA_SERVICE_URL", "http://localhost:3001")
ADMIN_KEY      = os.getenv("ADMIN_API_KEY", "nilechat_admin_secret")

router = APIRouter(tags=["whatsapp-qr"])


def _check_admin(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")


class QRMessage(BaseModel):
    company_id: int
    phone: str
    message: str


class ConnectRequest(BaseModel):
    company_id: int


@router.post("/webhook/whatsapp-qr")
async def receive_qr_message(body: QRMessage):
    """Receive message from Node.js WhatsApp service → NileChat → return reply."""
    company = await get_company_by_id(body.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    logger.info(f"[WA-QR] Company {body.company_id} | From {body.phone}: {body.message}")

    bot_reply = await nilechat_reply(
        user_text=body.message,
        phone=f"waqr_{body.phone}",
        platform="whatsapp",
        company_id=company["id"],
        company_name=company["name"],
        knowledge_base=company["knowledge_base"],
    )

    return {"reply": bot_reply}


@router.post("/admin/companies/{company_id}/connect-whatsapp")
async def connect_whatsapp(company_id: int, x_admin_key: str = Header(...)):
    _check_admin(x_admin_key)
    company = await get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{WA_SERVICE_URL}/connect/{company_id}")
        return r.json()


@router.get("/admin/companies/{company_id}/whatsapp-qr")
async def get_whatsapp_qr(company_id: int, x_admin_key: str = Header(...)):
    _check_admin(x_admin_key)
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{WA_SERVICE_URL}/qr/{company_id}")
        return r.json()


@router.get("/admin/companies/{company_id}/whatsapp-status")
async def get_whatsapp_status(company_id: int, x_admin_key: str = Header(...)):
    _check_admin(x_admin_key)
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{WA_SERVICE_URL}/status/{company_id}")
        return r.json()


@router.post("/admin/companies/{company_id}/disconnect-whatsapp")
async def disconnect_whatsapp(company_id: int, x_admin_key: str = Header(...)):
    _check_admin(x_admin_key)
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{WA_SERVICE_URL}/disconnect/{company_id}")
        return r.json()
