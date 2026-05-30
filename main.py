from fastapi import FastAPI, Request, Form
from dotenv import load_dotenv
from router import route_message
from faq_handler import handle_faq
from rag_handler import handle_rag
from whatsapp import send_message
import os
load_dotenv()

app = FastAPI()

@app.post("/webhook")
async def receive_message(
    From: str = Form(...),
    Body: str = Form(...)
):
    try:
        # Twilio sends From as "whatsapp:+91xxxxxxxxxx"
        # Strip the prefix for our send_message function
        from_number = From.replace("whatsapp:", "")
        user_text   = Body.strip()

        intent = await route_message(user_text)
        if intent == "RAG":
            reply = await handle_rag(user_text)
        else:
            reply = await handle_faq(user_text)

        await send_message(from_number, reply)

    except Exception as e:
        print(f"Error: {e}")

    return {"status": "ok"}