# One container: FastAPI backend (public) + WhatsApp QR service (internal).
# Mount a persistent volume at /data — it holds the SQLite database and
# every client's WhatsApp login.
FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends chromium nodejs npm fonts-noto-core ca-certificates \
 && rm -rf /var/lib/apt/lists/*

ENV PUPPETEER_SKIP_DOWNLOAD=true \
    CHROME_PATH=/usr/bin/chromium \
    DB_PATH=/data/nilechat.db \
    WA_AUTH_DIR=/data/wa_auth \
    WA_SERVICE_URL=http://localhost:3001 \
    PYTHON_BACKEND_URL=http://localhost:8000 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY whatsapp-service/package*.json whatsapp-service/
RUN cd whatsapp-service && npm install --omit=dev

COPY . .
RUN chmod +x start.sh

EXPOSE 8000
CMD ["./start.sh"]
