from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from analytics.analytics import (
    get_customer_stats,
    search_customers,
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
from crm.customer_mapping import get_business_id, set_customer_name
from unread_manager import clear_unread

router = APIRouter()

from pydantic import BaseModel

class LeadRequest(BaseModel):
    customer_phone: str
    status: str
    notes: str

class CustomerNameRequest(BaseModel):
    customer_phone: str
    name: str


@router.get("/customer-details/{user_id}")
async def customer_details(
    user_id: str
):

    return {
        "status": "success",
        "customers": await run_in_threadpool(
            get_customer_stats,
            user_id
        )
    }

@router.get("/customer-search/{user_id}")
async def customer_search(
    user_id: str,
    q: str = ""
):
    # Matches phone number, customer name, or message content anywhere in
    # the conversation history - see analytics/customer_stats.py.
    customers = await run_in_threadpool(
        search_customers,
        user_id,
        q
    )

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

    business_id = await run_in_threadpool(get_business_id, user_id)

    conversation_id = (
        f"{business_id}:{customer_phone}"
    )

    await run_in_threadpool(clear_unread, conversation_id)

    return {
        "status": "success",
        "messages": await run_in_threadpool(
            get_conversation,
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
        "lead": await run_in_threadpool(
            get_lead,
            customer_phone
        )
    }


@router.get("/customer-profile/{user_id}/{customer_phone}")
async def customer_profile(user_id: str, customer_phone: str):

    return {
        "status": "success",
        "profile": await run_in_threadpool(
            get_customer_profile,
            user_id,
            customer_phone
        )
    }

@router.post("/customer-name")
async def save_customer_name(request: CustomerNameRequest):

    name = request.name.strip()

    await run_in_threadpool(
        set_customer_name,
        request.customer_phone,
        name if name else None
    )

    return {
        "status": "success",
        "name": name
    }

@router.post("/lead")
async def save_lead(request: LeadRequest):

    current_lead = await run_in_threadpool(get_lead, request.customer_phone)

    await run_in_threadpool(
        update_lead,
        customer_phone=request.customer_phone,
        status=request.status,
        notes=request.notes,
        confidence=current_lead.get("confidence", 50),
        reason="Updated manually",
        updated_by="Manual"
    )

    await run_in_threadpool(
        add_activity,
        request.customer_phone,

        "Manual",

        "Lead Updated Manually",

        # No leading/trailing blank lines or indentation - the Customer
        # Timeline renders this with white-space:pre-wrap, so stray blank
        # lines/spaces here would show up as real empty space in the card.
        f"Status : {request.status}\n"
        f"Notes : {request.notes}"
    )

    return {
        "status": "success",
        "message": "Lead updated successfully",
        "lead": await run_in_threadpool(get_lead, request.customer_phone)
    }

@router.get("/lead-timeline/{customer_phone}")
async def lead_timeline(customer_phone: str):

    return {
        "status": "success",
        "timeline": await run_in_threadpool(get_lead_timeline, customer_phone)
    }


@router.get("/opportunities/{customer_phone}")
async def opportunities(customer_phone: str):

    return {
        "status": "success",
        "opportunities": await run_in_threadpool(get_opportunities, customer_phone)
    }

@router.get("/activity/{customer_phone}")

async def activity(customer_phone):

    return {

        "status":"success",

        "activity": await run_in_threadpool(get_activity, customer_phone)
    }

@router.get("/customer-timeline/{customer_phone}")
async def customer_timeline(customer_phone: str):

    return {
        "status": "success",
        "timeline": await run_in_threadpool(
            get_customer_timeline,
            customer_phone
        )
    }

@router.get("/activity-timeline/{customer_phone}")
async def activity_timeline(customer_phone: str):

    return {
        "status": "success",
        "timeline": await run_in_threadpool(get_activity_timeline, customer_phone)
    }

# NOTE: this file previously also defined GET /timeline/{customer_phone}
# (customer_timeline_3) here - an exact duplicate of GET
# /customer-timeline/{customer_phone} above, both calling the same
# get_customer_timeline(). Nothing in the frontend called /timeline, so it
# was removed rather than kept as a second name for the same endpoint.