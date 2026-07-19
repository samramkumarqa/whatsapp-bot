from fastapi import APIRouter
from pydantic import BaseModel
from database.db import get_conversation_connection
from crm.customer_mapping import (
    save_business_settings,
    get_business_settings,
    save_customer_number,
    get_business_phone_by_user,
    get_customers,
)

from conversations import get_last_customer_update

router = APIRouter()

class BusinessSettingsRequest(
    BaseModel
):
    user_id: str
    business_name: str
    welcome_message: str
    ai_instructions: str

class CustomerNumberRequest(
    BaseModel
):
    user_id: str
    whatsapp_number: str
    business_id: str | None = None

@router.post("/business-settings")
async def save_settings(
    request: BusinessSettingsRequest
):

    save_business_settings(
        request.user_id,
        request.business_name,
        request.welcome_message,
        request.ai_instructions
    )

    return {
        "status": "success"
    }
@router.get("/business-settings/{user_id}")
async def get_settings(
    user_id: str
):

    return {
        "status": "success",
        "settings": get_business_settings(
            user_id
        )
    }

@router.post("/customer-number")
async def save_number(
    request: CustomerNumberRequest
):

    save_customer_number(
        request.user_id,
        request.whatsapp_number,
        "business_001"
    )

    return {
        "status": "success"
    }

@router.get("/customer-number/{user_id}")
async def get_number(
    user_id: str
):

    number = get_business_phone_by_user(
        user_id
    )

    return {
    "status":"success",
    "configured": number is not None,
    "whatsapp_number": number
}


@router.get("/customers/{user_id}")
async def customers(user_id: str):
    return {
        "status": "success",
        "customers": get_customers(user_id)
    }

@router.get("/customers-last/{user_id}")
async def customers_last(user_id: str):
    return {
    "status": "success",
    "last_update": get_last_customer_update(user_id)
}

@router.get("/conversation-last/{user_id}/{customer_phone}")
async def conversation_last(user_id: str, customer_phone: str):

    conn = get_conversation_connection()

    row = conn.execute(
        """
        SELECT MAX(created_at)
        FROM conversations
        WHERE phone=?
        """,
        (f"{user_id}:{customer_phone}",)
    ).fetchone()

    conn.close()

    return {
        "last_message": row[0] or ""
    }