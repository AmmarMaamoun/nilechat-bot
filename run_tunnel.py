"""Keep ngrok tunnel alive. Token read from .env"""
import os
import time
from dotenv import load_dotenv
from pyngrok import ngrok, conf

load_dotenv()
token = os.getenv("NGROK_AUTHTOKEN")
if token:
    conf.get_default().auth_token = token

tunnel = ngrok.connect(8000, "http")
print(f"NGROK URL: {tunnel.public_url}", flush=True)

with open("tunnel_url.txt", "w") as f:
    f.write(tunnel.public_url)

print("Tunnel running. Press Ctrl+C to stop.", flush=True)
try:
    while True:
        time.sleep(30)
except KeyboardInterrupt:
    ngrok.kill()
