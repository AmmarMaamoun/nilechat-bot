# Bite 3A — Messenger Setup Guide

## Step 1: Create a Facebook Page
1. Go to https://business.facebook.com → Pages → Create Page
2. Category: choose what fits your business
3. Click **Create Page**
4. ⚠️ Make sure the page is **Published** (Settings → Page Visibility → Public)

## Step 2: Create a Meta App
1. Go to https://developers.facebook.com → My Apps → Create App
2. App type: **Business**
3. App name: `NileChat Bot`
4. Connect to your Business Account
5. Click **Create App**

## Step 3: Add Messenger Product
1. In App Dashboard → Add Products → find **Messenger** → click **Set Up**
2. Under **Access Tokens** → select your Page → click **Generate Token**
3. Copy this token → paste into `.env` as `MESSENGER_PAGE_ACCESS_TOKEN`

## Step 4: Required Permissions
Your app needs:
- `pages_messaging` — to send/receive messages
- `pages_read_engagement` — to read page info

For development: granted automatically for your own page.
For production: submit for App Review.

## Step 5: Set Webhook (after server is running)
1. Use ngrok for local testing: `ngrok http 8000`
2. Messenger product → Webhooks → **Add Callback URL**
3. URL: `https://abc123.ngrok.io/webhook/messenger`
4. Verify token: match your `MESSENGER_VERIFY_TOKEN` in `.env`
5. Subscribe to: `messages`, `messaging_postbacks`

## Step 6: Subscribe Page to Webhook
1. In Messenger → Webhooks → select your Page from dropdown
2. Click **Subscribe**

## Notes
- Sender ID in Messenger = PSID (Page-Scoped ID) — NOT a phone number
- For testing, any Facebook user can message your page
