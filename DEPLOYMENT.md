# PredictMaint Pro — Deployment Guide

## Option 1: Render.com (RECOMMENDED — Free)

1. Push code to GitHub
2. Go to https://render.com → New → Web Service
3. Connect your GitHub repo
4. Settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn wsgi:app --workers 2 --timeout 120 --bind 0.0.0.0:$PORT`
5. Environment Variables (click "Environment"):
   - `SECRET_KEY` → any random string
   - `RENDER` → `true`
   - `MAIL_USERNAME` → your Gmail
   - `MAIL_PASSWORD` → your Gmail App Password
   - `GEMINI_API_KEY` → your Gemini API key
   - `TELEGRAM_BOT_TOKEN` → your bot token
   - `TELEGRAM_CHAT_ID` → your chat ID
6. Click Deploy → Done!

## Option 2: Railway.app (Free tier)

1. Go to https://railway.app
2. New Project → Deploy from GitHub repo
3. Add environment variables (same as above)
4. Railway auto-detects Python and deploys!

## Option 3: PythonAnywhere (Free tier)

1. Go to https://www.pythonanywhere.com
2. Create free account
3. Open Bash console → git clone your repo
4. pip install -r requirements.txt
5. Set up Web App → Flask → point to wsgi.py

## Adding PostgreSQL (Render)

1. In Render dashboard → New → PostgreSQL
2. Copy the "Internal Database URL"
3. Add as env var: DATABASE_URL = <paste URL>
4. App auto-switches from SQLite to PostgreSQL!

## Login Credentials
- URL: https://your-app.onrender.com
- Username: admin
- Password: Admin@123
- Then enter OTP from your Gmail

## Important Notes
- ML models retrain on first deploy (~30 seconds)
- saved_models/ is in .gitignore — normal
- SQLite works fine for demo; PostgreSQL for production
