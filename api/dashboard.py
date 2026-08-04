from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
router = APIRouter()
from database.db import fetchall_crm, fetchall_conversation
from website_manager import get_websites
from analytics.analytics import (
    get_dashboard,
    get_stats,
    get_sales_funnel,
    get_lead_score_dashboard,
)

# NOTE: these routes are `async def` but the functions they call (get_dashboard,
# get_stats, etc.) are synchronous sqlite3 code. Calling them directly would
# block FastAPI's event loop for the duration of every DB query. Running them
# via run_in_threadpool moves that work onto a worker thread instead.

@router.get("/dashboard/{user_id}")
async def dashboard(user_id: str):

    return {
        "status": "success",
        "dashboard": await run_in_threadpool(get_dashboard, user_id)
    }

@router.get("/stats/{user_id}")
async def stats(user_id: str):

    websites = len(
        await run_in_threadpool(get_websites, user_id)
    )

    stats_data = await run_in_threadpool(get_stats, user_id)

    return {
        "status": "success",
        "websites": websites,
        **stats_data
    }

@router.get("/dashboard-metrics/{user_id}")
async def dashboard_metrics(user_id: str):

    from analytics.analytics import get_dashboard_metrics

    metrics = await run_in_threadpool(get_dashboard_metrics, user_id)

    return {
        "status": "success",
        **metrics
    }

@router.get("/sales-funnel/{user_id}")
async def sales_funnel(user_id: str):

    funnel = await run_in_threadpool(get_sales_funnel, user_id)

    return {
        "status": "success",
        **funnel
    }

@router.get("/lead-score-dashboard/{user_id}")
async def lead_score_dashboard(user_id: str):

    lead_score = await run_in_threadpool(get_lead_score_dashboard, user_id)

    return {
        "status": "success",
        **lead_score
    }

@router.get("/dashboard/analytics/{user_id}")
def dashboard_analytics(user_id: str):

    # ----------------------------------------
    # Lead Score Distribution
    # ----------------------------------------

    lead_rows = fetchall_crm("""
        SELECT lead_score, status
        FROM leads
    """)

    hot = 0
    warm = 0
    cold = 0

    status_distribution = {}

    for row in lead_rows:

        score = row["lead_score"] or 0

        if score >= 80:
            hot += 1
        elif score >= 50:
            warm += 1
        else:
            cold += 1

        status = row["status"] or "New"

        status_distribution[status] = (
            status_distribution.get(status, 0) + 1
        )

    lead_distribution = {
        "Hot": hot,
        "Warm": warm,
        "Cold": cold
    }

    # ----------------------------------------
    # Opportunity Pipeline
    # ----------------------------------------

    opportunity_rows = fetchall_crm("""

        SELECT
            status,
            COUNT(*) AS total
        FROM opportunities
        GROUP BY status

    """)

    pipeline = {}

    for row in opportunity_rows:

        pipeline[row["status"]] = row["total"]

    # ----------------------------------------
    # Message Trend (Last 7 Days)
    # ----------------------------------------

    message_rows = fetchall_conversation("""

        SELECT
            DATE(created_at) AS day,
            COUNT(*) AS total
        FROM conversations
        GROUP BY DATE(created_at)
        ORDER BY DATE(created_at)

    """)

    message_trend = []

    for row in message_rows:

        message_trend.append({
            "date": row["day"],
            "count": row["total"]
        })

    return {

        "lead_distribution": lead_distribution,

        "status_distribution": status_distribution,

        "pipeline": pipeline,

        "message_trend": message_trend

    }