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
# Business-owner login (WhatsApp/SMS OTP via Twilio Verify)
# ----------------------------------------
# Optional, unlike the admin vars above - /business-login shows a clear
# in-page error rather than crashing the app if TWILIO_VERIFY_SERVICE_SID
# isn't set yet (see verify.py). Create a Verify Service at
# https://console.twilio.com/us1/develop/verify/services and paste its
# SID into .env once ready.
#
# OTP_CHANNEL defaults to "sms" because Twilio Verify's WhatsApp channel
# requires a registered *production* WhatsApp sender (not available on
# the Sandbox) plus Meta-approved Authentication Templates - see
# verify.py's module docstring. Switch this to "whatsapp" once that
# sender is approved; nothing else in the code needs to change.
TWILIO_VERIFY_SERVICE_SID = os.getenv("TWILIO_VERIFY_SERVICE_SID")
OTP_CHANNEL = os.getenv("OTP_CHANNEL", "sms")

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
# Overridable via CHROMA_DB_PATH so production can point this at a
# persistent disk mount instead of the repo-relative default used locally.

CHROMA_DB = os.getenv("CHROMA_DB_PATH", "./chroma_db")

# ----------------------------------------
# Logging
# ----------------------------------------

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")