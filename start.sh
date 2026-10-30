#!/bin/sh
# Start the WhatsApp service in the background and the API in the foreground.
set -e
mkdir -p "$(dirname "$DB_PATH")" "$WA_AUTH_DIR"

# Backend always talks to itself on 8000; the platform's $PORT is the public one.
PUBLIC_PORT="${PORT:-8000}"
export PYTHON_BACKEND_URL="http://localhost:${PUBLIC_PORT}"

python seed_demo.py

(cd whatsapp-service && node index.js) &

exec uvicorn main:app --host 0.0.0.0 --port "$PUBLIC_PORT"
