from twilio.rest import Client
from dotenv import load_dotenv
import asyncio
import os
load_dotenv()

client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

FROM_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

async def send_message(
    to,
    text
):

    MAX_LENGTH = 1500

    chunks = [

        text[i:i + MAX_LENGTH]

        for i in range(
            0,
            len(text),
            MAX_LENGTH
        )
    ]

    loop = asyncio.get_running_loop()

    for chunk in chunks:

        await loop.run_in_executor(
            None,
            lambda c=chunk:
                client.messages.create(
                    from_=FROM_NUMBER,
                    to=f"whatsapp:{to}",
                    body=c
                )
        )

        await asyncio.sleep(1)