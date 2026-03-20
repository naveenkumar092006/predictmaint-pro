# config.py — Complete Configuration

import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'pmapp2024secure')

    # ── DATABASE — PostgreSQL with SQLite fallback ────────────────────────────
    # For PostgreSQL: set DATABASE_URL environment variable
    # Format: postgresql://user:password@host:port/dbname
    # Free PostgreSQL: supabase.com or neon.tech or render.com (free tier)
    DATABASE_URL = os.environ.get('DATABASE_URL', '')

    # SQLite fallback (works locally without any setup)
    if os.environ.get('RENDER') or os.environ.get('RAILWAY_ENVIRONMENT'):
        DATABASE = '/tmp/factory.db'
    else:
        _base = os.path.dirname(os.path.abspath(__file__))
        DATABASE = os.path.join(_base, 'instance', 'factory.db')

    # ── GMAIL OTP ─────────────────────────────────────────────────────────────
    MAIL_SERVER         = 'smtp.gmail.com'
    MAIL_PORT           = 587
    MAIL_USE_TLS        = True
    MAIL_USERNAME       = os.environ.get('MAIL_USERNAME', 'n2766363@gmail.com')
    MAIL_PASSWORD       = os.environ.get('MAIL_PASSWORD', 'qtsrepjdnvprvhfo')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME', 'n2766363@gmail.com')
    ALERT_RECIPIENT     = os.environ.get('ALERT_EMAIL',   'n2766363@gmail.com')

    # ── GEMINI AI ─────────────────────────────────────────────────────────────
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'YOUR_GEMINI_API_KEY')

    # ── TELEGRAM ─────────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8345194955:AAEZve-gH23_RCrCl1PJ0vKEU3mxLy7XQ-A')
    TELEGRAM_CHAT_ID   = os.environ.get('TELEGRAM_CHAT_ID',   '6828255111')

    # ── THRESHOLDS ────────────────────────────────────────────────────────────
    CRITICAL_FAILURE_PROB  = 0.60
    WARNING_FAILURE_PROB   = 0.30
    SIMULATION_INTERVAL_MS = 2000
    DASHBOARD_REFRESH_MS   = 5000
