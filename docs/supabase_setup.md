# Bite 1B — Supabase Setup Guide

## Step 1: Create Supabase Project
1. Go to https://supabase.com and sign in
2. Click **New Project**
3. Set name: `nilechat-bot`
4. Choose region: **EU West** (closest to Egypt)
5. Set a strong database password — save it
6. Click **Create new project** and wait ~2 minutes
## Step 2: Enable pgvector Extension
1. In your project dashboard → **Database** → **Extensions**
2. Search for `vector`
3. Toggle **Enable** on `vector` (pgvector)

## Step 3: Get Your Connection String
1. Go to **Project Settings** → **Database**
2. Scroll to **Connection string** → select **URI**
3. Copy it — it looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.abcdefgh.supabase.co:5432/postgres
   ```
4. Replace `[YOUR-PASSWORD]` with your actual password

## Step 4: Add to .env
```env
DATABASE_URL=postgresql://postgres:YourPassword@db.yourref.supabase.co:5432/postgres
```

## .env Format
```env
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
```
