import logging
import os


from fastapi import FastAPI
from twilio.request_validator import RequestValidator

from conversations import init_db
from crm.customer_mapping import (
    init_customer_mapping,
    init_business_settings,
)
from crm.lead_manager import init_leads
from crm.opportunity_manager import init_opportunities
from reminder_manager import init_reminders
from crm.tag_manager import init_tags
from crm.activity_manager import init_activity
from crm.followup_manager import init_followups

from api.dashboard import router as dashboard_router
from api.webhook import router as webhook_router
from api.ai import router as ai_router
from api.settings import router as settings_router
from api.website import router as website_router
from api.chat import router as chat_router
from api.misc import router as misc_router
from api.customer import router as customer_router
from automation.service import initialize_scheduler
from automation.database import init_automation_db
from api.automation import router as automation_router
from automation.database import init_automation_db
from api.reminders import router as reminders_router
from automation.scheduler import start_scheduler

# ==========================================================
# Environment & Initialization
# ==========================================================
from config import (
    DEBUG,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
)
app = FastAPI()

init_db()
init_customer_mapping()
init_business_settings()
init_leads()
init_opportunities()
init_reminders()
init_tags()
init_activity()
init_followups()
init_automation_db()

@app.on_event("startup")
async def startup():
    initialize_scheduler()


LEAD_PRIORITY = {
    "New": 1,
    "Interested": 2,
    "Qualified": 3,
    "Proposal Sent": 4,
    "Closed Won": 5,
    "Closed Lost": 5

}



validator = RequestValidator(TWILIO_AUTH_TOKEN)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logging.info("TWILIO_ACCOUNT_SID loaded: %s", bool(os.getenv("TWILIO_ACCOUNT_SID")))
app.include_router(webhook_router)
app.include_router(customer_router)
app.include_router(ai_router)
app.include_router(settings_router)
app.include_router(website_router)
app.include_router(chat_router)
app.include_router(misc_router)
app.include_router(dashboard_router)
app.include_router(automation_router)
app.include_router(reminders_router)

