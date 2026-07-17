import logging

from reminder_manager import upsert_reminder
from crm.opportunity_manager import add_opportunity
from crm.activity_manager import add_activity
from whatsapp import send_message

logger = logging.getLogger(__name__)


async def create_followup(customer_phone, params):
    """
    Create a follow-up reminder.
    """

    try:

        days = params.get("days", 1)

        title = params.get(
            "title",
            "AI Follow-up"
        )

        note = params.get(
            "note",
            "Automatically created by Automation Engine."
        )

        upsert_reminder(
            customer_phone,
            title,
            days,
            note
        )

        logger.info(
            f"Follow-up created for {customer_phone}"
        )

    except Exception:

        logger.exception(
            "Failed creating follow-up"
        )


async def create_opportunity(customer_phone, params):
    """
    Create CRM opportunity.
    """

    try:

        add_opportunity(

            customer_phone,

            params.get(
                "type",
                "General Opportunity"
            ),

            params.get(
                "confidence",
                80
            ),

            params.get(
                "reason",
                "Automation Engine"
            ),

            params.get(
                "estimated_value",
                0
            )

        )

        logger.info(
            f"Opportunity created for {customer_phone}"
        )

    except Exception:

        logger.exception(
            "Failed creating opportunity"
        )


async def log_activity(customer_phone, params):
    """
    Add CRM activity.
    """

    try:

        add_activity(

            customer_phone,

            params.get(
                "category",
                "Automation"
            ),

            params.get(
                "title",
                "Automation Triggered"
            ),

            params.get(
                "details",
                ""
            )

        )

    except Exception:

        logger.exception(
            "Activity logging failed"
        )


async def send_whatsapp_message(customer_phone, params):
    """
    Send WhatsApp message.
    """

    try:

        message = params.get("message")

        if message:

            await send_message(
                customer_phone,
                message
            )

    except Exception:

        logger.exception(
            "WhatsApp send failed"
        )


ACTION_REGISTRY = {

    "create_followup": create_followup,

    "create_opportunity": create_opportunity,

    "log_activity": log_activity,

    "send_whatsapp": send_whatsapp_message

}