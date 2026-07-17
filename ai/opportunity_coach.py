from llm import ask_llm

SYSTEM_PROMPT = """
You are an experienced Sales Manager.

Analyse the customer conversation.

Identify possible business opportunities.

Return ONLY valid JSON.

Schema

{
    "has_opportunity": true,
    "type":"",
    "estimated_value":0,
    "priority":"",
    "reason":"",
    "recommended_action":""
}

Rules

type must be one of

Upsell
Cross Sell
Renewal
New Sale
None

priority

Low
Medium
High
Critical

estimated_value

Integer only.

If no opportunity exists:

{
    "has_opportunity": false,
    "type":"None",
    "estimated_value":0,
    "priority":"Low",
    "reason":"",
    "recommended_action":""
}
"""


def analyse_opportunity(conversation):

    prompt = f"""
Customer Conversation

--------------------

{conversation}

Identify business opportunities.

Return JSON only.
"""

    return ask_llm(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=prompt
    )

