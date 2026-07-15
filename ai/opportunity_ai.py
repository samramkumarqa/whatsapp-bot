from groq import Groq
from dotenv import load_dotenv
import json
import os

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


def detect_opportunity(message):

    prompt = f"""
You are a sales opportunity detector.

Possible opportunities:

Upsell
Cross Sell
Enterprise Deal
Proposal Request
Follow Up Required

Customer message:

{message}

Return JSON:

{{
    "type":"Upsell",
    "confidence":90,
    "reason":"Customer requested additional service"
}}

If no opportunity exists:

{{
    "type":"None",
    "confidence":0,
    "reason":"No opportunity"
}}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role":"user",
                "content":prompt
            }
        ],
        temperature=0
    )

    try:

        return json.loads(
            response.choices[0]
            .message.content
        )

    except:

        return {
            "type":"None",
            "confidence":0,
            "reason":"Parse error"
        }