from groq import AsyncGroq
from dotenv import load_dotenv
import os
load_dotenv()

client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a helpful customer support assistant for {business_name}.
Answer only based on this information:
- Business hours: Mon–Sat, 9am–7pm
- Location: 12 Main Street, Tiruchengode
- Services: Tailoring, alterations, custom stitching
- Pricing: Shirt ₹300, Pant ₹400, Full suit ₹1500
- Contact: +91-98765-43210

If the question is not about the business, say:
'I can only help with questions about our shop.
Type *menu* to see what I can help with.'
"""

async def handle_faq(user_message: str) -> str:
    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(business_name="Sri Tailors")},
            {"role": "user",   "content": user_message}
        ]
    )
    return response.choices[0].message.content