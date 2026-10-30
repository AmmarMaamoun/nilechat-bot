"""Messenger OAuth — businesses connect their Facebook Page with one click."""
import os
import logging
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

FB_APP_ID     = os.getenv("FB_APP_ID", "2864718540535265")
FB_APP_SECRET = os.getenv("MESSENGER_APP_SECRET", "")
BASE_URL      = os.getenv("BASE_URL", "http://localhost:8000")

GRAPH = "https://graph.facebook.com/v19.0"

router = APIRouter(prefix="/messenger-oauth", tags=["messenger-oauth"])


@router.get("/start")
async def oauth_start(api_key: str):
    """Redirect business to Facebook Login to connect their page."""
    redirect_uri = f"{BASE_URL}/messenger-oauth/callback"
    scope = "pages_messaging,pages_manage_metadata,pages_read_engagement"
    state = api_key  # use api_key as state to identify company on callback
    url = (
        f"https://www.facebook.com/v19.0/dialog/oauth"
        f"?client_id={FB_APP_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scope}"
        f"&state={state}"
        f"&response_type=code"
    )
    return RedirectResponse(url)


@router.get("/callback")
async def oauth_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """Facebook redirects here after business grants permission."""
    if error or not code:
        return HTMLResponse("<h2>❌ Connection cancelled. Close this window and try again.</h2>")

    api_key = state
    redirect_uri = f"{BASE_URL}/messenger-oauth/callback"

    async with httpx.AsyncClient(timeout=15) as client:
        # Exchange code for user access token
        token_res = await client.get(f"{GRAPH}/oauth/access_token", params={
            "client_id": FB_APP_ID,
            "client_secret": FB_APP_SECRET,
            "redirect_uri": redirect_uri,
            "code": code,
        })
        token_data = token_res.json()
        user_token = token_data.get("access_token")
        if not user_token:
            raise HTTPException(status_code=400, detail=f"Token error: {token_data}")

        # Get pages the user manages
        pages_res = await client.get(f"{GRAPH}/me/accounts", params={"access_token": user_token})
        pages = pages_res.json().get("data", [])
        if not pages:
            return HTMLResponse("<h2>❌ No Facebook Pages found on this account.</h2>")

    # Store in DB (for now store first page — later let them choose)
    page = pages[0]
    page_token = page["access_token"]
    page_id    = page["id"]
    page_name  = page["name"]

    # Subscribe page to our app webhook
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(
            f"{GRAPH}/{page_id}/subscribed_apps",
            data={
                "subscribed_fields": "messages,messaging_postbacks",
                "access_token": page_token,
            }
        )

    # Save page token to company record via DB
    from db import set_company_messenger
    await set_company_messenger(api_key, page_id, page_token)

    return HTMLResponse(f"""
    <html><body style="font-family:sans-serif;text-align:center;padding:60px;background:#f0f2f5">
    <div style="background:#fff;border-radius:16px;padding:40px;max-width:400px;margin:auto;box-shadow:0 4px 24px rgba(0,0,0,.1)">
      <div style="font-size:48px">✅</div>
      <h2 style="color:#1a9e4a;margin:16px 0 8px">تم الربط بنجاح!</h2>
      <p style="color:#555">صفحة <strong>{page_name}</strong> متصلة الآن بالبوت.</p>
      <p style="color:#888;font-size:13px;margin-top:12px">ممكن تقفل هذه الصفحة وترجع للداشبورد.</p>
    </div>
    </body></html>
    """)
