from fastapi import FastAPI, Request, Form, HTTPException
from dotenv import load_dotenv
from twilio.request_validator import RequestValidator
from rag_handler import handle_rag
from whatsapp import send_message
from ingest import ingest_docs
from website_ingest import load_website_chunks
from pydantic import BaseModel
from conversations import init_db
from crawler import discover_links
from incremental_ingest import incremental_ingest
from fastapi.templating import Jinja2Templates
from fastapi import Request
from customer_mapping import init_customer_mapping
from unread_manager import increment_unread
from unread_manager import clear_unread
from conversations import (
    add_message,
    get_history,
    clear_history
)
from lead_ai import detect_lead_status
from lead_manager import (
    get_lead,
    update_lead
)
from website_manager import (
    get_websites,
    add_website as save_website,
    delete_website
)

from customer_mapping import (
    save_mapping,
    save_customer_number,
    get_customer_by_number,
    get_number_by_customer,
    get_business_phone,
    save_business_settings,
    get_business_settings,
    init_business_settings
)
from customer_mapping import (
    init_business_settings
)
from lead_manager import init_leads
init_leads()

init_business_settings()
from opportunity_manager import (
    init_opportunities
)
from reminder_manager import (
    init_reminders
)
import os
import logging
import asyncio

load_dotenv()
init_db()
init_customer_mapping()
init_opportunities()
init_reminders()

from pydantic import BaseModel
from lead_manager import get_lead_timeline

from opportunity_ai import detect_opportunity
from lead_manager import save_opportunity

from opportunity_manager import (
    get_opportunities
)
from reminder_manager import (
        create_reminder
    )
from reminder_manager import (
    get_reminders
)

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

    # Twilio validation
    if DEBUG:
        logger.warning("⚠️ DEBUG MODE: Skipping Twilio validation")
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
        logger.warning(
            f"Invalid Twilio signature from {request.client.host}"
        )

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

        from_number = From.replace(
            "whatsapp:",
            ""
        )

        to_number = To.replace(
            "whatsapp:",
            ""
        )

        user_text = Body.strip()

        # Save customer -> business mapping
        save_mapping(
            customer_phone=from_number,
            business_phone=to_number
        )

        # Find business owner from Twilio number
        business_user_id = get_customer_by_number(
            to_number
        )

        if not business_user_id:

            logger.warning(
                f"No business mapped to {to_number}"
            )

            await send_message(
                from_number,
                "This business is not configured yet."
            )

            return {"status": "success"}

        logger.info(
            f"Incoming customer={from_number} business={to_number}"
        )

        # Reset command
        if user_text.lower() == "reset":

            clear_history(
                f"{business_user_id}:{from_number}"
            )

            await send_message(
                from_number,
                "✅ Conversation history cleared."
            )

            return {"status": "success"}

        # Unique conversation per customer + business
        conversation_id = (
            f"{business_user_id}:{from_number}"
        )

        history = get_history(
            conversation_id
        )

        add_message(
            conversation_id,
            "user",
            user_text
        )
        increment_unread(
            conversation_id
        )

        try:

            ai_result = detect_lead_status(user_text)
            from opportunity_ai import detect_opportunity
            from opportunity_manager import add_opportunity

            opp = detect_opportunity(
                user_text
            )

            if (
                opp["type"] != "None"
                and
                opp["confidence"] >= 70
            ):

                add_opportunity(
                    from_number,
                    opp["type"],
                    opp["confidence"],
                    opp["reason"]
                )

                logger.info(
                    f"Opportunity Found: {opp}"
                )

            opportunity = detect_opportunity(
                user_text
            )

            if (
                opportunity["type"]
                != "None"
            ):

                save_opportunity(
                    from_number,
                    opportunity["type"],
                    opportunity["confidence"],
                    opportunity["reason"]
                )

                logger.info(
                    f"Opportunity Detected: "
                    f"{opportunity['type']}"
                )


            ai_status = ai_result.get("status", "New")
            confidence = ai_result.get("confidence", 50)
            reason = ai_result.get("reason", "")

            current_lead = get_lead(from_number)

            current_status = current_lead.get(
                "status",
                "New"
            )

            current_updated_by = current_lead.get(
                "updated_by",
                "Manual"
            )

            should_update = False

            # Higher lead stage
            if (
                LEAD_PRIORITY.get(ai_status, 0)
                >
                LEAD_PRIORITY.get(current_status, 0)
            ):
                should_update = True

            # Same stage but old record was manual
            elif (
                ai_status == current_status
                and current_updated_by != "AI"
            ):
                should_update = True

            if should_update:

                logger.info(
                    f"AI_RESULT => "
                    f"status={ai_status}, "
                    f"confidence={confidence}, "
                    f"reason={reason}"
                )

                update_lead(
                    from_number,
                    ai_status,
                    f"AI Auto Update: {user_text}",
                    confidence,
                    reason,
                    "AI"
                )

            if ai_status == "Interested":

                create_reminder(
                    from_number,
                    "Follow up with interested lead",
                    2
                )

            elif ai_status == "Qualified":

                create_reminder(
                    from_number,
                    "Send proposal or demo",
                    1
                )

            elif ai_status == "Proposal Sent":

                create_reminder(
                    from_number,
                    "Check proposal status",
                    3
                )


                saved = get_lead(from_number)

                logger.info(
                    f"DB_AFTER_SAVE => {saved}"
                )

                logger.info(
                    f"Lead updated "
                    f"{current_status} "
                    f"-> "
                    f"{ai_status}"
                )

            print(
                f"AI Lead Status = {ai_status}"
            )

        except Exception as e:

            logger.exception(
                f"Lead AI failed: {e}"
            )

            ai_status = None

        reply = await handle_rag(
            user_text,
            history,
            user_id=business_user_id
        )

        add_message(
            conversation_id,
            "assistant",
            reply
        )

        await send_message(
            from_number,
            reply
        )

        return {"status": "success"}

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

    from incremental_ingest import incremental_ingest

    try:
        await asyncio.to_thread(incremental_ingest, user_id)

        return {
            "status": "success",
            "message": f"Reindexed {user_id}"
        }

    except Exception as e:
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

@app.post("/add-website")
async def add_website_endpoint(request: WebsiteRequest):
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_chroma import Chroma

        # Fix — pass actual URL from request
        chunks = load_website_chunks(single_url=request.url)

        if not chunks:
            return {
                "status": "error",
                "message": f"Could not extract content from {request.url}"
            }

        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        vectorstore = Chroma(
            persist_directory="chroma_db",
            embedding_function=embeddings
        )

        vectorstore.add_documents(chunks)

        return {
            "status": "success",
            "message": f"Added {request.url} ({len(chunks)} chunks)"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/chat")
async def local_chat(
    phone: str,
    message: str
):
    try:

        # Load conversation history
        history = get_history(phone)

        # Save user message
        add_message(
            phone,
            "user",
            message
        )
        

        # Run RAG
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

        return {
            "status": "success",
            "reply": reply
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

    clear_history(phone)

    return {
        "status": "success",
        "message": f"History cleared for {phone}"
    }

@app.get("/health")
async def health_check():
    return {"status": "alive"}

@app.get("/history/{phone}")
async def view_history(phone: str):

    return get_history(phone)

@app.get("/websites")
async def websites():

    sites = get_websites()

    return {
        "count": len(sites),
        "websites": sorted(sites)
    }

@app.post("/website")
async def add_site(
    request: WebsiteRequest
):

    try:

        added_urls = []

        # Crawl mode
        if request.crawl:

            discovered_urls = discover_links(
                request.url,
                max_pages=50
            )

            for url in discovered_urls:

                print(f"DISCOVERED: {url}")

                if save_website(
                    request.user_id,
                    url
                ):
                    added_urls.append(url)

        # Single URL mode
        else:

            if save_website(
                request.user_id,
                request.url
            ):
                added_urls.append(request.url)

        # Background rebuild
        asyncio.create_task(
            asyncio.to_thread(
                incremental_ingest,
                request.user_id
            )
        )

        return {
            "status": "success",
            "added_count": len(added_urls),
            "added_urls": added_urls
        }

    except Exception as e:

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

        # Re-index this user's websites
        asyncio.create_task(
            asyncio.to_thread(
                incremental_ingest,
                request.user_id
            )
        )

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
        "status": "success",
        "whatsapp_number": number
    }

@app.get("/conversation-last/{user_id}/{customer_phone}")
async def conversation_last(user_id: str, customer_phone: str):

    import sqlite3
    conn = sqlite3.connect(CONVERSATION_DB)

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

    import sqlite3

    conn = sqlite3.connect("data/app.db")

    cursor = conn.execute(
        """
        SELECT customer_phone
        FROM customer_mapping
        WHERE business_phone = (
            SELECT whatsapp_number
            FROM customer_numbers
            WHERE user_id = ?
        )
        """,
        (user_id,)
    )

    customers = [
        row[0]
        for row in cursor.fetchall()
    ]

    conn.close()

    return {
        "status": "success",
        "customers": customers
    }

@app.get("/stats/{user_id}")
async def stats(user_id: str):

    import sqlite3

    websites = len(
        get_websites(user_id)
    )

    conn = sqlite3.connect("data/app.db")

    cursor = conn.execute(
        """
        SELECT whatsapp_number
        FROM customer_numbers
        WHERE user_id = ?
        """,
        (user_id,)
    )

    row = cursor.fetchone()

    customer_count = 0

    if row:

        business_phone = row[0]

        cursor = conn.execute(
            """
            SELECT COUNT(*)
            FROM customer_mapping
            WHERE business_phone = ?
            """,
            (business_phone,)
        )

        customer_count = cursor.fetchone()[0]

    conn.close()

    return {
        "websites": websites,
        "customers": customer_count
    }

from analytics import (
    get_customer_stats,
    get_conversation,
    get_customer_profile
)

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

    from analytics import get_top_customers

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

@app.get(
    "/customer-profile/{user_id}/{customer_phone}"
)
async def customer_profile(
    user_id: str,
    customer_phone: str
):

    profile = get_customer_profile(
        user_id,
        customer_phone
    )

    lead = get_lead(
        customer_phone
    )

    return {
        "status": "success",
        "profile": {

            "first_seen":
                profile["first_seen"],

            "last_seen":
                profile["last_seen"],

            "message_count":
                profile["message_count"],

            "lead_status":
                lead["status"],

            "confidence":
                lead["confidence"],

            "reason":
                lead["reason"],

            "updated_by":
                lead["updated_by"],

            "notes":
                lead["notes"],

            "lead_score": 
                lead["lead_score"]
        }
    }

@app.post("/lead")
async def save_lead(
    request: LeadRequest
):

    from lead_manager import update_lead

    update_lead(
        request.customer_phone,
        request.status,
        request.notes,
        100,
        "Updated manually",
        "Manual"
    )


    return {
        "status": "success"
    }

@app.get("/lead-timeline/{customer_phone}")
async def lead_timeline(customer_phone: str):

    timeline = get_lead_timeline(
        customer_phone
    )

    return {
        "status": "success",
        "timeline": timeline
    }


@app.get(
    "/opportunities/{customer_phone}"
)
async def opportunities(
    customer_phone: str
):

    return {
        "status":"success",
        "opportunities":
        get_opportunities(
            customer_phone
        )
    }

@app.get("/reminders")
async def reminders():

    return {
        "status": "success",
        "reminders": get_reminders()
    }

@app.get("/lead-categories")
async def lead_categories():

    import sqlite3

    conn = sqlite3.connect("data/app.db")

    cursor = conn.execute("""
        SELECT
            customer_phone,
            status,
            lead_score
        FROM leads
    """)

    rows = cursor.fetchall()

    conn.close()

    hot = []
    warm = []
    cold = []

    for row in rows:

        lead = {
            "customer_phone": row[0],
            "status": row[1],
            "lead_score": row[2]
        }

        if row[2] >= 80:
            hot.append(lead)

        elif row[2] >= 50:
            warm.append(lead)

        else:
            cold.append(lead)

    return {
        "hot": hot,
        "warm": warm,
        "cold": cold
    }

