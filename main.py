"""NileChat Bot — main FastAPI server."""
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from db import get_pool, close_pool
from whatsapp import router as whatsapp_router
from messenger import router as messenger_router
from webchat import router as webchat_router
from admin import router as admin_router
from whatsapp_qr import router as whatsapp_qr_router
from messenger_oauth import router as messenger_oauth_router

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def start_tunnel():
    """Auto-start ngrok tunnel on boot if NGROK_AUTHTOKEN is set."""
    token = os.getenv("NGROK_AUTHTOKEN")
    if not token:
        return
    try:
        from pyngrok import ngrok, conf
        conf.get_default().auth_token = token
        tunnel = ngrok.connect(int(os.getenv("PORT", 8000)), "http")
        url = tunnel.public_url
        with open("tunnel_url.txt", "w") as f:
            f.write(url)
        logger.info("=" * 60)
        logger.info(f"NGROK TUNNEL: {url}")
        logger.info(f"WhatsApp webhook: {url}/webhook/whatsapp")
        logger.info(f"Messenger webhook: {url}/webhook/messenger")
        logger.info(f"Widget script:    {url}/widget.js")
        logger.info(f"Admin API:        {url}/admin/companies")
        logger.info(f"Messenger OAuth:  {url}/messenger-oauth/start?api_key=YOUR_KEY")
        logger.info(f"Dashboard:        {url}/dashboard")
        logger.info("=" * 60)
    except Exception as e:
        logger.warning(f"ngrok tunnel failed to start: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    logger.info("Database pool ready")
    yield
    await close_pool()


app = FastAPI(title="NileChat SaaS", lifespan=lifespan)
app.include_router(whatsapp_router)
app.include_router(messenger_router)
app.include_router(webchat_router)
app.include_router(admin_router)
app.include_router(whatsapp_qr_router)
app.include_router(messenger_oauth_router)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/widget.js")
async def serve_widget():
    return FileResponse("static/widget.js", media_type="application/javascript")


@app.get("/dashboard")
async def serve_dashboard():
    return FileResponse("static/dashboard.html", media_type="text/html")


@app.get("/")
async def health():
    tunnel_url = ""
    try:
        with open("tunnel_url.txt") as f:
            tunnel_url = f.read().strip()
    except Exception:
        pass
    return {"status": "ok", "bot": "NileChat SaaS", "tunnel": tunnel_url}


if __name__ == "__main__":
    import uvicorn
    start_tunnel()
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
