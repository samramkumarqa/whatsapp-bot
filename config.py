import os
from dotenv import load_dotenv

# Load .env once
load_dotenv()

# ----------------------------------------
# App
# ----------------------------------------

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# ----------------------------------------
# Twilio
# ----------------------------------------

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

# ----------------------------------------
# Admin login
# ----------------------------------------
# Gates every page/route in the app except /login, /logout, /webhook, and
# /health - see main.py's AdminAuthMiddleware. There's no per-business
# login yet (see the ongoing multi-tenancy work), so this is a single
# shared admin account rather than a user table.

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")

# ----------------------------------------
# AI Providers
# ----------------------------------------
# NOTE: only Groq is actually used anywhere in this codebase. Removed
# OPENAI_API_KEY / GOOGLE_API_KEY, which were loaded here but never
# referenced by any other module.

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ----------------------------------------
# Vector Database
# ----------------------------------------

CHROMA_DB = "./chroma_db"

# ----------------------------------------
# Logging
# ----------------------------------------

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")