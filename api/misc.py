from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.templating import Jinja2Templates

from reminder_manager import get_reminders
from crm.lead_manager import get_lead_categories
from analytics.analytics import (
    get_opportunity_dashboard,
    get_reminder_dashboard,
)

router = APIRouter()

templates = Jinja2Templates(directory="templates")

@router.get("/")
async def dashboard(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html"
    )

@router.get("/analytics")
async def analytics_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="analytics.html"
    )

@router.get("/follow-ups")
async def followups_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="followups.html"
    )

@router.get("/settings")
async def settings_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="settings.html"
    )

@router.get("/health")
async def health_check():

    return {
        "status": "alive"
    }

@router.get("/reminders")
async def reminders():

    return {
        "status": "success",
        "reminders": await run_in_threadpool(get_reminders)
    }

@router.get("/lead-categories")
async def lead_categories():

    categories = await run_in_threadpool(get_lead_categories)

    return {
        "status": "success",
        **categories
    }

@router.get("/opportunity-dashboard/{user_id}")
async def opportunity_dashboard(user_id: str):

    return {
        "status": "success",
        "dashboard": await run_in_threadpool(get_opportunity_dashboard, user_id)
    }

@router.get("/reminder-dashboard/{user_id}")
async def reminder_dashboard(user_id: str):

    return {
        "status": "success",
        "dashboard": await run_in_threadpool(get_reminder_dashboard, user_id)
    }