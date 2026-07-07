from activity_manager import get_activity
from opportunity_manager import get_opportunities
from reminder_manager import get_customer_reminders


def get_customer_timeline(customer_phone):

    timeline = []

    # Activities
    for item in get_activity(customer_phone):
        timeline.append({
            "type": "activity",
            "date": item["created_at"],
            "title": item["title"],
            "source": item["source"],
            "details": item["details"]
        })

    # Opportunities
    for item in get_opportunities(customer_phone):
        timeline.append({
            "type": "opportunity",
            "date": item["created_at"],
            "title": f"Opportunity: {item['opportunity_type']}",
            "source": "AI",
            "details": item["reason"]
        })

    # Reminders
    for item in get_customer_reminders(customer_phone):
        timeline.append({
            "type": "reminder",
            "date": item["reminder_date"],
            "title": "Follow-up Reminder",
            "source": "Reminder",
            "details": item["notes"]
        })

    timeline.sort(
        key=lambda x: x.get("date") or "",
        reverse=True
    )

    return timeline