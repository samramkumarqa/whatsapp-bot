from fastapi import APIRouter
from pydantic import BaseModel

from ai.manager_assistant import ask_manager
from followup_ai import generate_followup

from analytics.analytics import get_conversation

from crm.lead_manager import get_lead

from crm.followup_manager import (
    save_followup,
    get_followups
)

from analytics.analytics import get_dashboard

router = APIRouter()

class ManagerQuestion(BaseModel):
    user_id: str
    question: str

@router.get("/generate-followup/{user_id}/{customer_phone}")
async def generate_followup_message(
    user_id: str,
    customer_phone: str
):

    messages = get_conversation(
        user_id,
        customer_phone
    )

    conversation = ""

    for msg in messages:

        role = (
            "Customer"
            if msg["role"] == "user"
            else "Assistant"
        )

        conversation += (
            f"{role}: {msg['content']}\n"
        )

    lead = get_lead(customer_phone)

    followup = generate_followup(
        conversation,
        lead
    )
    save_followup(
        customer_phone,
        followup
    )

    return {
        "status": "success",
        "followup": followup
    }

@router.get("/followups/{customer_phone}")
async def followups(customer_phone: str):

    return {
        "status": "success",
        "followups": get_followups(customer_phone)
    }


@router.get("/executive-dashboard/{user_id}")
async def executive_dashboard(user_id: str):

    return {
        "status": "success",
        "dashboard": get_dashboard(user_id)
    }

@router.post("/manager-assistant")
def manager_assistant(question: ManagerQuestion):

    answer = ask_manager(
        question.user_id,
        question.question
    )

    return {
        "question": question.question,
        "answer": answer
    }
