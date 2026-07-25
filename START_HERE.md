# NileChat Bot — Quick Start

## 1. Install dependencies
```bash
pip install -r requirements.txt
```

## 2. Set up environment
```bash
copy .env.example .env
# Edit .env and fill in your keys
```

## 3. Set up Supabase database
- Follow: `supabase_setup.md`
- Run `schema.sql` in Supabase SQL Editor

## 4. Test API connection (no DB needed)
```bash
python test_nilechat.py
```

## 5. Test database connection
```bash
python test_db_connection.py
```

## 6. Test full pipeline
```bash
python nilechat.py
```

## 7. Run the server
```bash
python main.py
# Server starts on http://localhost:8000
```

## 8. Expose with ngrok (for webhook testing)
```bash
ngrok http 8000
# Copy the HTTPS URL for Meta webhook config
```

## Webhook URLs
| Platform   | URL                                |
|------------|------------------------------------|
| WhatsApp   | `https://YOUR_URL/webhook/whatsapp` |
| Messenger  | `https://YOUR_URL/webhook/messenger`|

## Files
| File                    | Purpose                                    |
|-------------------------|--------------------------------------------|
| `test_nilechat.py`      | Bite 1A: test HuggingFace API              |
| `test_db_connection.py` | Bite 1B: test Supabase connection          |
| `schema.sql`            | Bite 1C+1D: tables + pgvector              |
| `db.py`                 | Database layer (users/conversations/msgs)  |
| `nilechat.py`           | Bite 1E+1F: AI brain + memory              |
| `whatsapp.py`           | Bite 2B+2C+2D: WhatsApp webhook + sender   |
| `messenger.py`          | Bite 3B+3C+3D: Messenger webhook + sender  |
| `main.py`               | FastAPI server (mounts all routes)         |
| `supabase_setup.md`     | Bite 1B: Supabase step-by-step guide       |
| `whatsapp_setup.md`     | Bite 2A: WhatsApp WABA setup guide         |
| `messenger_setup.md`    | Bite 3A: Facebook Page + App setup guide   |
