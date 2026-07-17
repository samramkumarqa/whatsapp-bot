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
# AI Providers
# ----------------------------------------

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# ----------------------------------------
# Vector Database
# ----------------------------------------

CHROMA_DB = "./chroma_db"

# ----------------------------------------
# Logging
# ----------------------------------------

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")