from fastapi import APIRouter

from analytics.analytics import (
    get_customer_stats,
    get_conversation,
    get_customer_profile,
    get_top_customers,
)

from crm.lead_manager import (
    get_lead,
    get_lead_timeline,
    update_lead,
)

from crm.opportunity_manager import (
    get_opportunities,
)

from crm.activity_manager import (
    get_activity,
    get_activity_timeline,
    add_activity,
)

from timeline_manager import get_customer_timeline

from unread_manager import clear_unread

router = APIRouter()

from pydantic import BaseModel

class LeadRequest(BaseModel):
    customer_phone: str
    status: str
    notes: str


@router.get("/customer-details/{user_id}")
async def customer_details(
    user_id: str
):

    return {
        "status": "success",
        "customers": get_customer_stats(
            user_id
        )
    }

@router.get("/customer-search/{user_id}")
async def customer_search(
    user_id: str,
    q: str = ""
):
    from analytics.analytics import get_customer_stats

    customers = get_customer_stats(user_id)

    if q:

        customers = [
            c for c in customers
            if q.lower() in c["phone"].lower()
        ]

    return {
        "status": "success",
        "customers": customers
    }

@router.get(
    "/conversation/{user_id}/{customer_phone}"
)
async def conversation_view(
    user_id: str,
    customer_phone: str
):
        conversation_id = (
            f"{user_id}:{customer_phone}"
        )

        clear_unread(
            conversation_id
        )

        return {
            "status": "success",
            "messages": get_conversation(
                user_id,
                customer_phone
            )
    }


@router.get("/lead/{customer_phone}")
async def lead_details(
    customer_phone: str
):

    return {
        "status": "success",
        "lead": get_lead(
            customer_phone
        )
    }


@router.get("/customer-profile/{user_id}/{customer_phone}")
async def customer_profile(user_id: str, customer_phone: str):

    return {
        "status": "success",
        "profile": get_customer_profile(
            user_id,
            customer_phone
        )
    }

@router.post("/lead")
async def save_lead(request: LeadRequest):

    current_lead = get_lead(request.customer_phone)

    update_lead(
        customer_phone=request.customer_phone,
        status=request.status,
        notes=request.notes,
        confidence=current_lead.get("confidence", 50),
        reason="Updated manually",
        updated_by="Manual"
    )

    add_activity(

        request.customer_phone,

        "Manual",

        "Lead Updated Manually",

        f"""

    Status : {request.status}

    Notes :

    {request.notes}
    """
    )

    return {
        "status": "success",
        "message": "Lead updated successfully",
        "lead": get_lead(request.customer_phone)
    }

@router.get("/lead-timeline/{customer_phone}")
async def lead_timeline(customer_phone: str):

    return {
        "status": "success",
        "timeline": get_lead_timeline(customer_phone)
    }


@router.get("/opportunities/{customer_phone}")
async def opportunities(customer_phone: str):

    return {
        "status": "success",
        "opportunities": get_opportunities(customer_phone)
    }

@router.get("/activity/{customer_phone}")

async def activity(customer_phone):

    return {

        "status":"success",

        "activity":get_activity(customer_phone)
    }

@router.get("/customer-timeline/{customer_phone}")
async def customer_timeline(customer_phone: str):

    return {
        "status": "success",
        "timeline": get_customer_timeline(
            customer_phone
        )
    }

@router.get("/customer-timeline/{customer_phone}")
async def customer_timeline(customer_phone: str):

    return {
        "status": "success",
        "timeline": get_activity_timeline(customer_phone)
    }

@router.get("/timeline/{customer_phone}")
async def customer_timeline(customer_phone: str):

    return {
        "status": "success",
        "timeline": get_customer_timeline(customer_phone)
    }