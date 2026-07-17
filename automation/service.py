from automation.scheduler import (
    add_job,
    start_scheduler,
)

from automation.jobs import (
    send_due_reminders,
    follow_up_leads,
    generate_daily_sales_summary,
)


def initialize_scheduler():
    """
    Register all scheduled automation jobs.
    """

    #
    # Every day at 9:00 AM
    #
    add_job(
        send_due_reminders,
        hour=9,
        minute=0,
        job_id="daily_reminders"
    )

    #
    # Every 30 minutes
    #
    add_job(
        follow_up_leads,
        interval_minutes=30,
        job_id="lead_followups"
    )

    #
    # Every day at 6:00 PM
    #
    add_job(
        generate_daily_sales_summary,
        hour=18,
        minute=0,
        job_id="daily_sales_summary"
    )

    start_scheduler()