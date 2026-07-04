
import json
from dotenv import load_dotenv
from llm import ask_llm

load_dotenv()


SYSTEM_PROMPT = """
You are an expert CRM Sales Assistant.

Analyse the customer's conversation.

Return ONLY valid JSON.

Schema

{
    "intent":"",
    "buying_stage":"",
    "sentiment":"",
    "objection":"",
    "lead_score":0,
    "priority":"",
    "confidence":0,
    "probability":0,
    "next_action":"",
    "follow_up_days":0,
    "summary":"",
    "tags":[]
}

Rules

Intent MUST be one of

- Pricing Inquiry
- Product Inquiry
- Complaint
- Support
- Purchase Ready
- Returning Customer
- General Inquiry

Buying Stage MUST be one of

- Awareness
- Interested
- Considering
- Ready to Buy
- Customer

Sentiment MUST be one of

- Positive
- Neutral
- Negative

Objection MUST be one of

- Price
- Competitor
- Timing
- Need Approval
- None

Priority MUST be one of

- Low
- Medium
- High
- Critical

Lead Score
0-100

Confidence
0-100

Probability
0-100

follow_up_days
Integer only.

tags
Return a list of useful CRM tags.

Example

[
    "Hot Lead",
    "Pricing Inquiry",
    "Needs Follow-up"
]

Return JSON only.

Do NOT explain.

Do NOT use markdown.

Do NOT wrap JSON inside ``` blocks.
"""


DEFAULT_RESPONSE = {

    "intent": "General Inquiry",

    "buying_stage": "Interested",

    "sentiment": "Neutral",

    "objection": "None",

    "lead_score": 40,

    "priority": "Medium",

    "confidence": 20,

    "probability": 20,

    "next_action": "Manual Review",

    "follow_up_days": 1,

    "summary": "AI analysis failed.",

    "tags": [
        "Manual Review"
    ]
}


def analyse_conversation(conversation_text):

    prompt = f"""
Customer Conversation

---------------------

{conversation_text}

Analyse ONLY the customer's buying behaviour.

Estimate missing information using the conversation context.

Return VALID JSON ONLY.

Do not include markdown.
"""

    try:

        response = ask_llm(

            system_prompt=SYSTEM_PROMPT,

            user_prompt=prompt

        )

        if isinstance(response, dict):
            result = response

        else:

            # Sometimes LLM returns extra text before/after JSON.
            start = response.find("{")
            end = response.rfind("}") + 1

            if start == -1 or end == 0:
                raise ValueError("JSON not found")

            json_text = response[start:end]

            result = json.loads(json_text)

        # Fill missing keys
        for key, value in DEFAULT_RESPONSE.items():
            result.setdefault(key, value)

        # Safety checks
        result["lead_score"] = max(0, min(100, int(result["lead_score"])))
        result["confidence"] = max(0, min(100, int(result["confidence"])))
        result["probability"] = max(0, min(100, int(result["probability"])))
        result["follow_up_days"] = max(0, int(result["follow_up_days"]))

        if not isinstance(result["tags"], list):
            result["tags"] = [str(result["tags"])]

        return result

    except Exception as e:

        print("Lead Intelligence Error:", e)

        return DEFAULT_RESPONSE.copy()

from analytics import get_conversation
from lead_manager import update_lead_intelligence


def refresh_customer_intelligence(
    user_id,
    customer_phone
):
    """
    Analyse the full conversation and update CRM.
    """

    messages = get_conversation(
        user_id,
        customer_phone
    )

    conversation_text = ""

    for msg in messages:

        role = (
            "Customer"
            if msg["role"] == "user"
            else "Assistant"
        )

        conversation_text += (
            f"{role}: {msg['content']}\n"
        )

    analysis = analyse_conversation(
        conversation_text
    )

    update_lead_intelligence(
        customer_phone,
        analysis
    )

    return analysis