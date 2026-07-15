from datetime import datetime
from unread_manager import get_unread
from crm.lead_manager import get_lead
from sales_coach import get_next_best_action
from analytics.customer_health import get_customer_health_dashboard
from analytics.ai_alerts import get_ai_alerts
from analytics.forecast_manager import get_sales_forecast
from business_insights import generate_business_insights
from executive_summary import generate_executive_summary
from daily_briefing import generate_daily_briefing
from crm.customer_mapping import get_business_phone_by_user

CONVERSATION_DB = "conversations.db"
CRM_DB = "data/app.db"
from database.db import (
    get_crm_connection,
    get_conversation_connection
)

def get_stats(user_id):

    business_phone = get_business_phone_by_user(user_id)

    if not business_phone:

        return {
            "customers": 0
        }
    conn = get_crm_connection() 

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
        "customers": customer_count
    }

def get_customer_stats(user_id):

    conv_conn = get_conversation_connection()
    crm_conn = get_crm_connection()

    cursor = conv_conn.execute(
        """
        SELECT
            phone,
            COUNT(*) as message_count,
            MAX(created_at) as last_seen
        FROM conversations
        WHERE phone LIKE ?
        GROUP BY phone
        ORDER BY last_seen DESC
        """,
        (f"{user_id}:%",)
    )

    rows = cursor.fetchall()

    customers = []

    for row in rows:

        conversation_id = row[0]

        customer_phone = (
            conversation_id.split(":")[1]
            if ":" in conversation_id
            else conversation_id
        )

        unread_count = get_unread(conversation_id)

        last_message_cursor = conv_conn.execute(
            """
            SELECT content
            FROM conversations
            WHERE phone = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (conversation_id,)
        )

        last_message_row = last_message_cursor.fetchone()

        last_message = (
            last_message_row[0]
            if last_message_row
            else ""
        )

        lead_cursor = crm_conn.execute(
            """
            SELECT
                lead_score,
                status
            FROM leads
            WHERE customer_phone = ?
            """,
            (customer_phone,)
        )

        lead_row = lead_cursor.fetchone()

        lead_score = lead_row[0] if lead_row else 0
        lead_status = lead_row[1] if lead_row else "New"

        customers.append({
            "phone": customer_phone,
            "message_count": row[1],
            "last_seen": row[2],
            "unread_count": unread_count,
            "last_message": last_message,
            "lead_score": lead_score,
            "status": lead_status
        })

    conv_conn.close()
    crm_conn.close()

    return customers

def get_conversation(
    user_id,
    customer_phone
):

    conversation_id = (
        f"{user_id}:{customer_phone}"
    )

    conn = get_conversation_connection()

    cursor = conn.execute(
        """
        SELECT role,
               content,
               created_at
        FROM conversations
        WHERE phone = ?
        ORDER BY id
        """,
        (conversation_id,)
    )

    rows = cursor.fetchall()

    conn.close()

    return [
        {
            "role": row[0],
            "content": row[1],
            "created_at": row[2]
        }
        for row in rows
    ]

def get_dashboard_metrics(user_id):

    conn = get_conversation_connection()

    customer_count = conn.execute(
        """
        SELECT COUNT(DISTINCT phone)
        FROM conversations
        WHERE phone LIKE ?
        """,
        (f"{user_id}:%",)
    ).fetchone()[0]

    message_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM conversations
        WHERE phone LIKE ?
        """,
        (f"{user_id}:%",)
    ).fetchone()[0]

    today_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM conversations
        WHERE phone LIKE ?
        AND DATE(created_at)=DATE('now')
        """,
        (f"{user_id}:%",)
    ).fetchone()[0]

    conn.close()

    return {
        "customers": customer_count,
        "messages": message_count,
        "today_messages": today_count
    }

def get_customer_profile(user_id, customer_phone):

    conn = get_conversation_connection()

    cursor = conn.execute(
        """
        SELECT
            MIN(created_at),
            MAX(created_at),
            COUNT(*)
        FROM conversations
        WHERE phone = ?
        """,
        (f"{user_id}:{customer_phone}",)
    )

    row = cursor.fetchone()

    conn.close()

    lead = get_lead(customer_phone)

    profile = {
        "customer_phone": customer_phone,
        "first_seen": row[0],
        "last_seen": row[1],
        "message_count": row[2]
    }

    # Merge all lead intelligence automatically
    profile.update(lead)
    profile["next_best_action"] = get_next_best_action(lead)
    return profile

def get_top_customers(
    user_id,
    limit=5
):

    conn = get_conversation_connection()

    cursor = conn.execute(
        """
        SELECT
            phone,
            COUNT(*) as message_count
        FROM conversations
        WHERE phone LIKE ?
        GROUP BY phone
        ORDER BY message_count DESC
        LIMIT ?
        """,
        (
            f"{user_id}:%",
            limit
        )
    )

    rows = cursor.fetchall()

    conn.close()

    customers = []

    for row in rows:

        conversation_id = row[0]

        customer_phone = (
            conversation_id.split(":")[1]
            if ":" in conversation_id
            else conversation_id
        )

        customers.append({
            "phone": customer_phone,
            "message_count": row[1]
        })

    return customers

def get_sales_funnel(user_id):

    business_phone = get_business_phone_by_user(user_id)

    if not business_phone:

        return {
            "total_leads": 0,
            "conversion_rate": 0,
            "funnel": {
                "New": 0,
                "Interested": 0,
                "Qualified": 0,
                "Proposal Sent": 0,
                "Won": 0,
                "Lost": 0
            }
        }

    conn = get_crm_connection()

    cursor = conn.execute(
        """
        SELECT
            l.status,
            COUNT(*)
        FROM leads l
        INNER JOIN customer_mapping cm
            ON l.customer_phone = cm.customer_phone
        WHERE cm.business_phone = ?
        GROUP BY l.status
        """,
        (business_phone,)
    )

    rows = cursor.fetchall()

    conn.close()

    funnel = {
        "New": 0,
        "Interested": 0,
        "Qualified": 0,
        "Proposal Sent": 0,
        "Won": 0,
        "Lost": 0
    }

    for status, count in rows:

        if status in funnel:
            funnel[status] = count

    total = sum(funnel.values())

    won = funnel["Won"]

    conversion_rate = (
        round((won / total) * 100, 1)
        if total
        else 0
    )

    return {
        "total_leads": total,
        "conversion_rate": conversion_rate,
        "funnel": funnel
    }

def get_lead_score_dashboard(user_id):

    business_phone = get_business_phone_by_user(user_id)

    if not business_phone:

        return {
            "hot": 0,
            "warm": 0,
            "cold": 0,
            "average_score": 0
        }

    conn = get_crm_connection()

    cursor = conn.execute(
        """
        SELECT
            l.lead_score
        FROM leads l
        INNER JOIN customer_mapping cm
            ON l.customer_phone = cm.customer_phone
        WHERE cm.business_phone = ?
        """,
        (business_phone,)
    )

    scores = [
        row[0] or 0
        for row in cursor.fetchall()
    ]

    conn.close()

    hot = sum(
        1 for score in scores
        if score >= 80
    )

    warm = sum(
        1 for score in scores
        if 50 <= score < 80
    )

    cold = sum(
        1 for score in scores
        if score < 50
    )

    average = (
        round(sum(scores) / len(scores), 1)
        if scores
        else 0
    )

    return {
        "hot": hot,
        "warm": warm,
        "cold": cold,
        "average_score": average
    }




def get_dashboard(user_id):

    dashboard = {

        "stats": get_stats(user_id),

        "metrics": get_dashboard_metrics(user_id),

        "sales_funnel": get_sales_funnel(user_id),

        "lead_scores": get_lead_score_dashboard(user_id),

        "opportunities": get_opportunity_dashboard(user_id),

        "reminders": get_reminder_dashboard(user_id),

        "top_customers": get_top_customers(user_id),

        #
        # Phase 10
        #

        "customer_health": get_customer_health_dashboard(user_id),

        "ai_alerts": get_ai_alerts(user_id),

        "sales_coach": [],

        "forecast": get_sales_forecast(
            get_business_phone_by_user(user_id)
        ),

        # Temporary placeholder
        "business_insights": []
    }

    #
    # Generate Business Insights
    #
    dashboard["business_insights"] = generate_business_insights(
        dashboard["lead_scores"],
        dashboard["sales_funnel"],
        dashboard["opportunities"],
        dashboard["reminders"]
    )

    #
    # Generate Executive Summary
    #
    dashboard["executive_summary"] = generate_executive_summary(
        user_id,
        dashboard
    )

    #
    # Generate Daily Briefing
    #
    dashboard["daily_briefing"] = generate_daily_briefing(
        dashboard
    )

    return dashboard

def get_opportunity_dashboard(user_id):

    business_phone = get_business_phone_by_user(user_id)

    if not business_phone:

        return {
            "total": 0,
            "open": 0,
            "won": 0,
            "lost": 0,
            "pipeline_value": 0,
            "by_type": {}
        }

    conn = get_crm_connection()

    rows = conn.execute(
        """
        SELECT
            o.opportunity_type,
            o.status,
            o.estimated_value
        FROM opportunities o
        INNER JOIN customer_mapping cm
            ON o.customer_phone = cm.customer_phone
        WHERE cm.business_phone = ?
        """,
        (business_phone,)
    ).fetchall()

    conn.close()

    dashboard = {
        "total": 0,
        "open": 0,
        "won": 0,
        "lost": 0,
        "pipeline_value": 0,
        "by_type": {}
    }

    for opp_type, status, value in rows:

        dashboard["total"] += 1

        status = (status or "Open").title()

        if status == "Open":
            dashboard["open"] += 1
            dashboard["pipeline_value"] += value or 0

        elif status == "Won":
            dashboard["won"] += 1

        elif status == "Lost":
            dashboard["lost"] += 1

        dashboard["by_type"][opp_type] = (
            dashboard["by_type"].get(opp_type, 0) + 1
        )

    return dashboard

def get_reminder_dashboard(user_id):

    business_phone = get_business_phone_by_user(user_id)

    if not business_phone:

        return {
            "total": 0,
            "today": 0,
            "upcoming": 0,
            "overdue": 0,
            "completed": 0
        }

    conn = get_crm_connection()

    rows = conn.execute(
        """
        SELECT
            r.due_date,
            r.completed
        FROM reminders r
        INNER JOIN customer_mapping cm
            ON r.customer_phone = cm.customer_phone
        WHERE cm.business_phone = ?
        """,
        (business_phone,)
    ).fetchall()

    conn.close()

    dashboard = {
        "total": 0,
        "today": 0,
        "upcoming": 0,
        "overdue": 0,
        "completed": 0
    }

    today = datetime.now().date()

    for due_date, completed in rows:

        dashboard["total"] += 1

        if completed:
            dashboard["completed"] += 1
            continue

        try:
            due = datetime.strptime(
                due_date,
                "%Y-%m-%d"
            ).date()

        except Exception:
            continue

        if due == today:
            dashboard["today"] += 1

        elif due > today:
            dashboard["upcoming"] += 1

        else:
            dashboard["overdue"] += 1

    return dashboard