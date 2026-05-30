from groq import AsyncGroq
from dotenv import load_dotenv
import os
load_dotenv()

client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

ROUTER_PROMPT = """You are a message classifier. Given a user message,
reply with exactly one word:
- FAQ   → if it's about shop hours, location, pricing, services, contact
- RAG   → if it's asking about a document, product catalogue, manual, or policy
- FAQ   → if you are unsure

Message: {message}"""

async def route_message(message: str) -> str:
    response = await client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": ROUTER_PROMPT.format(message=message)}],
        max_tokens=5
    )
    intent = response.choices[0].message.content.strip().upper()
    return "RAG" if "RAG" in intent else "FAQ"