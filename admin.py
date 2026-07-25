"""Admin API — create and manage companies (SaaS tenants)."""
import os
import logging
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from dotenv import load_dotenv
from db import create_company, get_company_by_id, update_company_knowledge, list_companies

load_dotenv()
logger = logging.getLogger(__name__)

ADMIN_KEY = os.getenv("ADMIN_API_KEY", "nilechat_admin_secret")

router = APIRouter(prefix="/admin", tags=["admin"])


def _check_admin(x_admin_key: str):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")


class CompanyCreate(BaseModel):
    name: str
    knowledge_base: str | None = None
    welcome_message: str | None = None


class KnowledgeUpdate(BaseModel):
    knowledge_base: str
    welcome_message: str | None = None


@router.get("/companies")
async def get_companies(x_admin_key: str = Header(...)):
    _check_admin(x_admin_key)
    return await list_companies()


@router.post("/companies", status_code=201)
async def add_company(body: CompanyCreate, x_admin_key: str = Header(...)):
    _check_admin(x_admin_key)
    company = await create_company(body.name, body.knowledge_base, body.welcome_message)
    tunnel = ""
    try:
        with open("tunnel_url.txt") as f:
            tunnel = f.read().strip()
    except Exception:
        pass
    return {
        **company,
        "embed_snippet": (
            f'<script src="{tunnel}/widget.js" '
            f'data-api-key="{company["api_key"]}"></script>'
        ),
    }


@router.put("/companies/{company_id}/knowledge")
async def update_knowledge(company_id: int, body: KnowledgeUpdate, x_admin_key: str = Header(...)):
    _check_admin(x_admin_key)
    company = await get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    await update_company_knowledge(company_id, body.knowledge_base, body.welcome_message)
    return {"status": "updated", "company_id": company_id}


@router.get("/companies/{company_id}")
async def get_company(company_id: int, x_admin_key: str = Header(...)):
    _check_admin(x_admin_key)
    company = await get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    tunnel = ""
    try:
        with open("tunnel_url.txt") as f:
            tunnel = f.read().strip()
    except Exception:
        pass
    return {
        **company,
        "embed_snippet": (
            f'<script src="{tunnel}/widget.js" '
            f'data-api-key="{company["api_key"]}"></script>'
        ),
    }
