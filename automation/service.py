from automation.scheduler import (
    add_job,
    start_scheduler,
)

from automation.jobs import (
    send_due_reminders,
    follow_up_leads,
    generate_daily_sales_summary,
)

from automation.runner import run_automation


def initialize_scheduler():

    add_job(
        send_due_reminders,
        hour=9,
        minute=0,
        job_id="daily_reminders"
    )

    add_job(
        follow_up_leads,
        interval_minutes=30,
        job_id="lead_followups"
    )

    add_job(
        generate_daily_sales_summary,
        hour=18,
        minute=0,
        job_id="daily_sales_summary"
    )

    # ⭐ Automation Engine
    add_job(
        run_automation,
        interval_minutes=1,
        job_id="automation_runner"
    )
    print("Automation Runner job registered")
    start_scheduler()