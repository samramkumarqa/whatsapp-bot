from fastapi import (
    APIRouter,
    Request,
    Form,
    HTTPException,
)
from fastapi.concurrency import run_in_threadpool
from config import (
    DEBUG,
    TWILIO_AUTH_TOKEN,
)
import os
import logging
logger = logging.getLogger(__name__)
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
from twilio.request_validator import RequestValidator
validator = RequestValidator(TWILIO_AUTH_TOKEN)

from crm.customer_mapping import (
    save_mapping,
    get_customer_by_number,
    get_business_id
)

from conversations import (
    get_history,
    add_message,
    clear_history,
)

from unread_manager import increment_unread

from rag_handler import handle_rag

from whatsapp import send_message

from ai.lead_intelligence import refresh_customer_intelligence

from reminder_manager import (
    reminder_exists,
    upsert_reminder,
)

from crm.activity_manager import add_activity
from fastapi import APIRouter
router = APIRouter()

@router.post("/webhook")
async def receive_message(
    request: Request,
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...),
    # The sender's WhatsApp display name. Twilio includes this on WhatsApp
    # messages when the sender has one set; not every message has it, so
    # it's optional. Used as a best-effort auto-captured customer name -
    # see save_mapping()/get_customer_stats() for how it's stored/read.
    ProfileName: str = Form(None)
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
        await run_in_threadpool(
            save_mapping,
            customer_phone=from_number,
            business_phone=to_number,
            customer_name=(
                ProfileName.strip() if ProfileName else None
            )
        )

        business_user_id = await run_in_threadpool(
            get_customer_by_number,
            to_number
        )
        business_id = await run_in_threadpool(
            get_business_id,
            business_user_id
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

            await run_in_threadpool(
                clear_history,
                f"{business_id}:{from_number}"
            )

            await send_message(
                from_number,
                "✅ Conversation history cleared."
            )

            return {
                "status": "success"
            }

        conversation_id = (
            f"{business_id}:{from_number}"
        )

        history = await run_in_threadpool(
            get_history,
            conversation_id
        )

        # -----------------------------
        # Save user message
        # -----------------------------
        await run_in_threadpool(
            add_message,
            conversation_id,
            "user",
            user_text
        )

        await run_in_threadpool(
            increment_unread,
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
        await run_in_threadpool(
            add_message,
            conversation_id,
            "assistant",
            reply
        )

        # -----------------------------
        # Refresh CRM Intelligence
        # -----------------------------
        try:

            # NOTE: this is an `async def` function - it was previously
            # called without `await`, which meant `analysis` was actually
            # an unawaited coroutine object. `analysis.get(...)` below would
            # then raise AttributeError, get swallowed by the `except`
            # below, and get logged as "Lead Intelligence failed" - meaning
            # this entire block silently never ran for real incoming
            # WhatsApp messages (it did work correctly from api/ai.py and
            # api/chat.py, which already awaited it properly).
            analysis = await refresh_customer_intelligence(
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

            if not await run_in_threadpool(reminder_exists, from_number):

                await run_in_threadpool(
                    upsert_reminder,
                    from_number,
                    f"[{priority}] {next_action}",
                    follow_up_days
                )
                await run_in_threadpool(
                    add_activity,
                    from_number,

                    "Reminder",

                    "Follow-up Scheduled",

                    # No leading/trailing blank lines or indentation - the
                    # Customer Timeline renders this with
                    # white-space:pre-wrap, so stray blank lines/spaces
                    # here would show up as real empty space in the card.
                    f"{next_action}\n"
                    f"After {follow_up_days} day(s)\n"
                    f"Priority : {priority}"
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
