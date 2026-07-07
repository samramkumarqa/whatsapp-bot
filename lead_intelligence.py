
import json
from dotenv import load_dotenv
from llm import ask_llm
from tag_manager import save_tags
load_dotenv()
import logging
logger = logging.getLogger(__name__)
from analytics import get_conversation
from lead_manager import update_lead_intelligence


AI_VERSION = "v1"

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
    "tags":[],
    "ai_version":""
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

Return between 3 and 6 useful CRM tags.

Prefer choosing from the following standard CRM tags whenever possible:

Lead Status
- Hot Lead
- Warm Lead
- Cold Lead

Intent
- Pricing Inquiry
- Product Inquiry
- Purchase Ready
- General Inquiry
- Support
- Complaint

Buying Behaviour
- Returning Customer
- New Customer
- Decision Maker
- Needs Approval
- Budget Concern
- Competitor Mentioned
- Timing Concern

Sales
- Proposal Sent
- Demo Requested
- Follow-up Required
- Upsell Opportunity
- Cross Sell Opportunity

Relationship
- VIP Customer
- High Value Customer

Rules

- Return ONLY a JSON array.
- Use short CRM-friendly tags.
- Do not invent similar words if one of the standard tags fits.
- Maximum 6 tags.
- Minimum 3 tags.

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
    ],

    "ai_version": AI_VERSION
}

def analyse_conversation(conversation_text):

    prompt = f"""
Customer Conversation

---------------------

{conversation_text}

Analyse the entire conversation.

Estimate missing information using context.

Choose 3 to 6 meaningful CRM tags.

Avoid creating new tag names when a standard CRM tag already applies.

Return VALID JSON ONLY.

Do not include markdown.

Do not explain your reasoning.
"""

    VALID_INTENTS = {
        "Pricing Inquiry",
        "Product Inquiry",
        "Complaint",
        "Support",
        "Purchase Ready",
        "Returning Customer",
        "General Inquiry"
    }

    VALID_BUYING_STAGES = {
        "Awareness",
        "Interested",
        "Considering",
        "Ready to Buy",
        "Customer"
    }

    VALID_SENTIMENTS = {
        "Positive",
        "Neutral",
        "Negative"
    }

    VALID_OBJECTIONS = {
        "Price",
        "Competitor",
        "Timing",
        "Need Approval",
        "None"
    }

    VALID_PRIORITIES = {
        "Low",
        "Medium",
        "High",
        "Critical"
    }

    try:

        response = ask_llm(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt
        )

        if isinstance(response, dict):
            result = response

        else:

            start = response.find("{")
            end = response.rfind("}") + 1

            if start == -1 or end == 0:
                raise ValueError("JSON not found")

            result = json.loads(response[start:end])

        # Fill missing keys
        for key, value in DEFAULT_RESPONSE.items():
            result.setdefault(key, value)

        # Ensure AI version always exists
        result.setdefault("ai_version", AI_VERSION)

        # Normalize string fields
        result["intent"] = str(result["intent"]).strip()
        result["buying_stage"] = str(result["buying_stage"]).strip()
        result["sentiment"] = str(result["sentiment"]).strip()
        result["objection"] = str(result["objection"]).strip()
        result["priority"] = str(result["priority"]).strip()
        result["summary"] = str(result["summary"]).strip()
        result["next_action"] = str(result["next_action"]).strip()

        # Validate enum values
        if result["intent"] not in VALID_INTENTS:
            result["intent"] = DEFAULT_RESPONSE["intent"]

        if result["buying_stage"] not in VALID_BUYING_STAGES:
            result["buying_stage"] = DEFAULT_RESPONSE["buying_stage"]

        if result["sentiment"] not in VALID_SENTIMENTS:
            result["sentiment"] = DEFAULT_RESPONSE["sentiment"]

        if result["objection"] not in VALID_OBJECTIONS:
            result["objection"] = DEFAULT_RESPONSE["objection"]

        if result["priority"] not in VALID_PRIORITIES:
            result["priority"] = DEFAULT_RESPONSE["priority"]

        # Numeric safety
        result["lead_score"] = max(
            0,
            min(100, int(result["lead_score"]))
        )

        result["confidence"] = max(
            0,
            min(100, int(result["confidence"]))
        )

        result["probability"] = max(
            0,
            min(100, int(result["probability"]))
        )

        result["follow_up_days"] = max(
            0,
            int(result["follow_up_days"])
        )

        # Normalize tags
        if not isinstance(result["tags"], list):
            result["tags"] = [str(result["tags"])]

        result["tags"] = sorted(
            {
                tag.strip()
                for tag in result["tags"]
                if tag and tag.strip()
            }
        )

        return result

    except Exception:

        logger.exception("Lead Intelligence Error")

        return DEFAULT_RESPONSE.copy()



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

    save_tags(
        customer_phone,
        analysis.get("tags", [])
    )
    logger.info(
        f"Updated AI tags for {customer_phone}: "
        f"{analysis.get('tags', [])}"
    )
    return analysis