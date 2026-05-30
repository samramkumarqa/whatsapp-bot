from twilio.rest import Client
from dotenv import load_dotenv
import os
load_dotenv()

client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

FROM_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

async def send_message(to: str, text: str):
    client.messages.create(
        from_=FROM_NUMBER,
        to=f"whatsapp:{to}",
        body=text
    )