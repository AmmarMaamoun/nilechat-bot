# Bite 2A — WhatsApp Business API Setup (Egypt)

## Step 1: Get a Dedicated Phone Number
- **Do NOT use a number already registered on personal WhatsApp**
- Options:
  - Buy a new SIM (Vodafone/Orange/Etisalat Egypt) — cheapest
  - Use a virtual number (Twilio, DIDWW) — works but may have Egyptian calling restrictions
- Recommendation: new Egyptian SIM, keep it for business only

## Step 2: Create a Meta Business Account
1. Go to https://business.facebook.com
2. Create a Business account if you don't have one
3. Verify your business (basic info is enough for free tier)

## Step 3: Register via Meta Embedded Signup
1. Go to https://developers.facebook.com → Create App
2. App type: **Business**
3. Add product: **WhatsApp**
4. Click **Start using the API** → follow Embedded Signup flow
5. Add your phone number → verify with OTP
6. **⚠️ You have 14 days to complete business verification after adding the number**

## Step 4: Generate Permanent Token
1. Meta Business Suite → System Users → Create system user (Admin)
2. Assign WhatsApp app to this system user
3. Generate token with these permissions:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`
4. Copy token → paste into `.env` as `WHATSAPP_TOKEN`

## Step 5: Get Phone Number ID
1. WhatsApp → API Setup in Meta Developers
2. Copy **Phone number ID** → paste into `.env` as `WHATSAPP_PHONE_NUMBER_ID`

## Step 6: Set Webhook (after server is running)
1. Use ngrok for local testing: `ngrok http 8000`
2. Copy the HTTPS URL (e.g. `https://abc123.ngrok.io`)
3. Meta Developers → WhatsApp → Configuration → Webhook
4. URL: `https://abc123.ngrok.io/webhook/whatsapp`
5. Verify token: match your `WHATSAPP_VERIFY_TOKEN` in `.env`
6. Subscribe to: `messages`

## Egypt Notes
- Egyptian numbers work fine with WhatsApp Cloud API
- Format: `201XXXXXXXXX` (country code 20 + number without leading 0)
- No special restrictions for receiving messages
