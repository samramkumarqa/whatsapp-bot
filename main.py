
# ==========================================================
# Standard Library
# ==========================================================

import asyncio
import logging
import os

# ==========================================================
# Third Party
# ==========================================================

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from twilio.request_validator import RequestValidator
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma


# ==========================================================
# Conversation
# ==========================================================

from conversations import (
    add_message,
    clear_history,
    get_history,
    init_db,
    get_last_customer_update
)
from tag_manager import init_tags
# ==========================================================
# AI / RAG
# ==========================================================

from rag_handler import handle_rag
from whatsapp import send_message
from lead_intelligence import refresh_customer_intelligence

# ==========================================================
# Website / Knowledge Base
# ==========================================================

from crawler import discover_links
from incremental_ingest import incremental_ingest
from ingest import ingest_docs
from website_ingest import load_website_chunks
from website_manager import (
    add_website as save_website,
    delete_website,
    get_websites,
)

from analytics import (
    get_customer_stats,
    get_conversation,
    get_customer_profile,
    get_stats,
    get_top_customers,
    get_sales_funnel,
    get_lead_score_dashboard
)

# ==========================================================
# Customer Mapping
# ==========================================================

from customer_mapping import (
    get_business_phone,
    get_business_settings,
    get_customer_by_number,
    get_number_by_customer,
    init_business_settings,
    init_customer_mapping,
    save_business_settings,
    save_customer_number,
    save_mapping,
    get_customers
)

# ==========================================================
# Leads
# ==========================================================

from lead_ai import detect_lead_status

from lead_manager import (
    get_lead,
    get_lead_timeline,
    init_leads,
    save_opportunity,
    update_lead,
    get_lead_categories
)

# ==========================================================
# Opportunities
# ==========================================================

from opportunity_ai import detect_opportunity

from opportunity_manager import (
    add_opportunity,
    get_opportunities,
    init_opportunities,
)

# ==========================================================
# Reminders
# ==========================================================

from reminder_manager import (
    create_reminder,
    get_reminders,
    init_reminders,
    reminder_exists,
    upsert_reminder,
)

# ==========================================================
# Unread Messages
# ==========================================================

from unread_manager import (
    clear_unread,
    increment_unread,
)

# ==========================================================
# Activity Manager
# ==========================================================
from activity_manager import init_activity, add_activity, get_activity, get_activity_timeline
# ==========================================================
# Timeline Manager
# ==========================================================
from timeline_manager import get_customer_timeline
# ==========================================================
# Environment & Initialization
# ==========================================================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)

init_db()
init_customer_mapping()
init_business_settings()
init_leads()
init_opportunities()
init_reminders()
init_tags()
init_activity()

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

validator = RequestValidator(
    os.getenv("TWILIO_AUTH_TOKEN")
)

templates = Jinja2Templates(
    directory="templates"
)

app = FastAPI()


LEAD_PRIORITY = {

    "New": 1,
    "Interested": 2,
    "Qualified": 3,
    "Proposal Sent": 4,
    "Closed Won": 5,
    "Closed Lost": 5

}
class LeadRequest(
    BaseModel
):
    customer_phone: str
    status: str
    notes: str

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

print("SID:", os.getenv("TWILIO_ACCOUNT_SID"))
print("TOKEN:", os.getenv("TWILIO_AUTH_TOKEN"))

templates = Jinja2Templates(
    directory="templates"
)

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

validator = RequestValidator(os.getenv("TWILIO_AUTH_TOKEN"))

app = FastAPI() 


class WebsiteRequest(BaseModel):
    user_id: str
    url: str
    crawl: bool = False
    max_pages: int = 50


@app.post("/webhook")
async def receive_message(
    request: Request,
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...)
):
    signature = request.headers.get("X-Twilio-Signature")

    form_data = {
        "From": From,
        "Body": Body
    }

    # -----------------------------
    # Validate Twilio
    # -----------------------------
    if DEBUG:
        logger.warning("⚠ DEBUG MODE - Twilio validation skipped")
        is_valid = True
    else:
        is_valid = validator.validate(
            str(request.url).replace(
                "http://",
                "https://"
            ),
            form_data,
            signature
        )

    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid Twilio Signature"
        )

    if not From.startswith("whatsapp:"):
        raise HTTPException(
            status_code=400,
            detail="Only WhatsApp supported"
        )

    try:

        from_number = From.replace("whatsapp:", "")
        to_number = To.replace("whatsapp:", "")
        user_text = Body.strip()

        # -----------------------------
        # Save mapping
        # -----------------------------
        save_mapping(
            customer_phone=from_number,
            business_phone=to_number
        )

        business_user_id = get_customer_by_number(
            to_number
        )

        if not business_user_id:

            await send_message(
                from_number,
                "This business is not configured yet."
            )

            return {
                "status": "success"
            }

        logger.info(
            f"Incoming customer={from_number} "
            f"business={to_number}"
        )

        # -----------------------------
        # Reset command
        # -----------------------------
        if user_text.lower() == "reset":

            clear_history(
                f"{business_user_id}:{from_number}"
            )

            await send_message(
                from_number,
                "✅ Conversation history cleared."
            )

            return {
                "status": "success"
            }

        conversation_id = (
            f"{business_user_id}:{from_number}"
        )

        history = get_history(
            conversation_id
        )

        # -----------------------------
        # Save user message
        # -----------------------------
        add_message(
            conversation_id,
            "user",
            user_text
        )

        increment_unread(
            conversation_id
        )

        # -----------------------------
        # Generate AI Reply
        # -----------------------------
        reply = await handle_rag(
            user_text,
            history,
            user_id=business_user_id
        )

        # -----------------------------
        # Save assistant reply
        # -----------------------------
        add_message(
            conversation_id,
            "assistant",
            reply
        )

        # -----------------------------
        # Refresh CRM Intelligence
        # -----------------------------
        try:

            analysis = refresh_customer_intelligence(
                business_user_id,
                from_number
            )

            logger.info(
                f"Lead Intelligence: {analysis}"
            )

            next_action = analysis.get(
                "next_action",
                "Follow up"
            )

            follow_up_days = analysis.get(
                "follow_up_days",
                1
            )

            priority = analysis.get(
                "priority",
                "Medium"
            )

            if not reminder_exists(from_number):

                upsert_reminder(
                    from_number,
                    f"[{priority}] {next_action}",
                    follow_up_days
                )
                add_activity(

                    from_number,

                    "Reminder",

                    "Follow-up Scheduled",

                    f"""

                {next_action}

                After {follow_up_days} day(s)

                Priority : {priority}
                """
                )

        except Exception as e:

            logger.exception(
                f"Lead Intelligence failed: {e}"
            )

        # -----------------------------
        # Send WhatsApp Reply
        # -----------------------------
        await send_message(
            from_number,
            reply
        )

        return {
            "status": "success"
        }

    except Exception as e:

        logger.exception(
            f"Webhook error: {e}"
        )

        return {
            "status": "error",
            "message": str(e)
        }


@app.post("/reindex/{user_id}")
async def reindex(user_id: str):

    try:
        await asyncio.to_thread(
            incremental_ingest,
            user_id
        )

        return {
            "status": "success",
            "message": f"Reindexed {user_id}"
        }

    except Exception as e:

        logger.exception(e)

        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/business-settings")
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
@app.get("/business-settings/{user_id}")
async def get_settings(
    user_id: str
):

    return {
        "status": "success",
        "settings": get_business_settings(
            user_id
        )
    }


@app.post("/chat")
async def local_chat(
    phone: str,
    message: str
):

    try:

        logger.info(
            f"Local Chat: {phone}"
        )

        # Save user message
        add_message(
            phone,
            "user",
            message
        )

        # Load updated conversation
        history = get_history(phone)

        # Generate AI reply
        reply = await handle_rag(
            message,
            history,
            user_id=phone
        )

        # Save assistant reply
        add_message(
            phone,
            "assistant",
            reply
        )

        analysis = None

        try:

            analysis = refresh_customer_intelligence(
                user_id=phone,
                customer_phone=phone
            )

            logger.info(
                f"Lead Intelligence: {analysis}"
            )

        except Exception as e:

            logger.exception(
                f"Lead Intelligence failed: {e}"
            )

        return {
            "status": "success",
            "reply": reply,
            "analysis": analysis
        }

    except Exception as e:

        logger.exception(
            f"Local chat error: {e}"
        )

        return {
            "status": "error",
            "message": str(e)
        }
    
@app.post("/reset/{phone}")
async def reset_chat(phone: str):

    logger.info(
        f"Conversation reset: {phone}"
    )

    clear_history(phone)

    return {
        "status": "success",
        "message": f"History cleared for {phone}"
    }


@app.get("/health")
async def health_check():

    return {
        "status": "alive"
    }

@app.get("/websites")
async def websites():

    sites = get_websites()

    return {
        "status": "success",
        "count": len(sites),
        "websites": sorted(sites)
    }


@app.post("/website")
async def add_site(request: WebsiteRequest):

    try:

        logger.info(
            f"Adding website(s) for {request.user_id}"
        )

        added_urls = []

        # ------------------------------------
        # Crawl entire website
        # ------------------------------------

        if request.crawl:

            discovered_urls = discover_links(
                request.url,
                max_pages=request.max_pages
            )

            logger.info(
                f"Discovered {len(discovered_urls)} pages"
            )

            for url in discovered_urls:

                logger.info(
                    f"Discovered: {url}"
                )

                if save_website(
                    request.user_id,
                    url
                ):
                    added_urls.append(url)

        # ------------------------------------
        # Single page
        # ------------------------------------

        else:

            if save_website(
                request.user_id,
                request.url
            ):
                added_urls.append(request.url)

        # ------------------------------------
        # Nothing new
        # ------------------------------------

        if not added_urls:

            return {
                "status": "exists",
                "message": "Website(s) already exist."
            }

        # ------------------------------------
        # Background Reindex
        # ------------------------------------

        logger.info(
            f"Starting background indexing for {request.user_id}"
        )

        schedule_reindex(request.user_id)

        return {

            "status": "success",

            "added_count": len(added_urls),

            "added_urls": added_urls,

            "message": "Background indexing started."

        }

    except Exception as e:

        logger.exception(
            f"Website add failed: {e}"
        )

        return {

            "status": "error",

            "message": str(e)

        }

@app.delete("/website")
async def remove_site(
    request: WebsiteRequest
):

    try:

        removed = delete_website(
            request.user_id,
            request.url
        )

        if not removed:
            return {
                "status": "not_found",
                "message": "Website not found"
            }

        schedule_reindex(request.user_id)

        return {
            "status": "success",
            "message": "Website removed and reindex started"
        }

    except Exception as e:

        logger.exception(
            f"Delete website error: {e}"
        )

        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/")
async def dashboard(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html"
    )

@app.get("/websites/{user_id}")
async def list_websites(user_id: str):

    websites = get_websites(user_id)

    return {
        "status": "success",
        "count": len(websites),
        "websites": websites
    }

@app.post("/customer-number")
async def save_number(
    request: CustomerNumberRequest
):

    save_customer_number(
        request.user_id,
        request.whatsapp_number
    )

    return {
        "status": "success"
    }

@app.get("/customer-number/{user_id}")
async def get_number(
    user_id: str
):

    number = get_number_by_customer(
        user_id
    )

    return {
    "status":"success",
    "configured": number is not None,
    "whatsapp_number": number
}

@app.get("/conversation-last/{user_id}/{customer_phone}")
async def conversation_last(user_id: str, customer_phone: str):

    import sqlite3
    conn = sqlite3.connect("conversations.db")

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

@app.get("/customers/{user_id}")
async def customers(user_id: str):
    return {
        "status": "success",
        "customers": get_customers(user_id)
    }

@app.get("/customers-last/{user_id}")
async def customers_last(user_id: str):
    return {
    "status": "success",
    "last_update": get_last_customer_update(user_id)
}

@app.get("/stats/{user_id}")
async def stats(user_id: str):

    websites = len(
        get_websites(user_id)
    )

    return {
        "status": "success",
        "websites": websites,
        **get_stats(user_id)
    }



@app.get("/customer-details/{user_id}")
async def customer_details(
    user_id: str
):

    return {
        "status": "success",
        "customers": get_customer_stats(
            user_id
        )
    }

@app.get("/customer-search/{user_id}")
async def customer_search(
    user_id: str,
    q: str = ""
):
    from analytics import get_customer_stats

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

@app.get(
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

@app.get("/dashboard-metrics/{user_id}")
async def dashboard_metrics(user_id: str):

    from analytics import get_dashboard_metrics

    return {
        "status": "success",
        **get_dashboard_metrics(user_id)
    }

@app.get("/top-customers/{user_id}")
async def top_customers(
    user_id: str
):

    

    return {
        "status": "success",
        "customers": get_top_customers(
            user_id
        )
    }

@app.get("/lead/{customer_phone}")
async def lead_details(
    customer_phone: str
):

    return {
        "status": "success",
        "lead": get_lead(
            customer_phone
        )
    }

@app.get("/customer-profile/{user_id}/{customer_phone}")
async def customer_profile(user_id: str, customer_phone: str):

    return {
        "status": "success",
        "profile": get_customer_profile(
            user_id,
            customer_phone
        )
    }

@app.post("/lead")
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

@app.get("/lead-timeline/{customer_phone}")
async def lead_timeline(customer_phone: str):

    return {
        "status": "success",
        "timeline": get_lead_timeline(customer_phone)
    }


@app.get("/opportunities/{customer_phone}")
async def opportunities(customer_phone: str):

    return {
        "status": "success",
        "opportunities": get_opportunities(customer_phone)
    }


@app.get("/reminders")
async def reminders():

    return {
        "status": "success",
        "reminders": get_reminders()
    }


@app.get("/lead-categories")
async def lead_categories():

    return {
        "status": "success",
        **get_lead_categories()
    }

def schedule_reindex(user_id: str):

    logger.info(
        f"Scheduling background reindex for {user_id}"
    )
    asyncio.create_task(
        asyncio.to_thread(
            incremental_ingest,
            user_id
        )
    )

@app.get("/activity/{customer_phone}")

async def activity(customer_phone):

    return {

        "status":"success",

        "activity":get_activity(customer_phone)
    }

@app.get("/customer-timeline/{customer_phone}")
async def customer_timeline(customer_phone: str):

    return {
        "status": "success",
        "timeline": get_customer_timeline(
            customer_phone
        )
    }

@app.get("/customer-timeline/{customer_phone}")
async def customer_timeline(customer_phone: str):

    return {
        "status": "success",
        "timeline": get_activity_timeline(customer_phone)
    }

@app.get("/timeline/{customer_phone}")
async def customer_timeline(customer_phone: str):

    return {
        "status": "success",
        "timeline": get_customer_timeline(customer_phone)
    }

@app.get("/sales-funnel/{user_id}")
async def sales_funnel(user_id: str):

    return {
        "status": "success",
        **get_sales_funnel(user_id)
    }

@app.get("/lead-score-dashboard/{user_id}")
async def lead_score_dashboard(user_id: str):

    return {
        "status": "success",
        **get_lead_score_dashboard(user_id)
    }