from fastapi import APIRouter
router = APIRouter()

from website_manager import get_websites
from analytics.analytics import (
    get_dashboard,
    get_stats,
    get_sales_funnel,
    get_lead_score_dashboard,
)

@router.get("/dashboard/{user_id}")
async def dashboard(user_id: str):

    return {
        "status": "success",
        "dashboard": get_dashboard(user_id)
    }

@router.get("/stats/{user_id}")
async def stats(user_id: str):

    websites = len(
        get_websites(user_id)
    )

    return {
        "status": "success",
        "websites": websites,
        **get_stats(user_id)
    }

@router.get("/dashboard-metrics/{user_id}")
async def dashboard_metrics(user_id: str):

    from analytics.analytics import get_dashboard_metrics

    return {
        "status": "success",
        **get_dashboard_metrics(user_id)
    }

@router.get("/sales-funnel/{user_id}")
async def sales_funnel(user_id: str):

    return {
        "status": "success",
        **get_sales_funnel(user_id)
    }

@router.get("/lead-score-dashboard/{user_id}")
async def lead_score_dashboard(user_id: str):

    return {
        "status": "success",
        **get_lead_score_dashboard(user_id)
    }