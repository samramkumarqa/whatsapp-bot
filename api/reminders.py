from fastapi import APIRouter

from database.db import get_crm_connection
from reminder_manager import (
    find_stale_reminders,
    delete_stale_reminders,
    complete_reminder,
)

router = APIRouter()

APP_DB = "data/app.db"   # use your existing DB path


def get_connection():
    # Shares the pooled data/app.db connections from database/db.py instead
    # of opening its own unpooled sqlite3 connection to the same file.
    return get_crm_connection()

# NOTE: this file previously also defined GET /reminders here
# (get_all_reminders()). api/misc.py registers the exact same path, and
# since misc_router is included before reminders_router in main.py,
# misc.py's handler always won - this one was dead, unreachable code.
# Removed; misc.py's GET /reminders (backed by reminder_manager.get_reminders())
# is the one that actually serves that path.

# =====================================================
# STALE REMINDERS (preview + cleanup)
#
# These have to be registered before GET /reminders/{customer_phone}
# below - otherwise FastAPI would match "/reminders/stale" against that
# route's {customer_phone} path parameter (literally looking up a
# customer named "stale") instead of reaching these.
# =====================================================

@router.get("/reminders/stale")
def preview_stale_reminders():
    """
    Reminders whose originating rule has since been deleted, no longer
    has a Create Reminder action, or now says something different - i.e.
    the reminder text on screen no longer reflects the rule's real,
    current configuration.
    """

    return {
        "stale": find_stale_reminders()
    }


@router.delete("/reminders/stale")
def clear_stale_reminders():

    deleted = delete_stale_reminders()

    return {
        "status": "success",
        "deleted": deleted
    }

# =====================================================
# MARK A REMINDER DONE
#
# 3 path segments (/reminders/{id}/complete), so this never collides with
# GET /reminders/{customer_phone} below (2 segments) regardless of
# registration order.
# =====================================================

@router.post("/reminders/{reminder_id}/complete")
def mark_reminder_complete(reminder_id: int):

    complete_reminder(reminder_id)

    return {
        "status": "success"
    }

# =====================================================
# GET REMINDERS FOR ONE CUSTOMER
# =====================================================

@router.get("/reminders/{customer_phone}")
def get_customer_reminders(customer_phone: str):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""

        SELECT *

        FROM reminders

        WHERE customer_phone = ?
        AND completed = 0

        ORDER BY due_date ASC

    """, (customer_phone,))

    reminders = [
        dict(row)
        for row in cursor.fetchall()
    ]

    conn.close()

    return {
        "reminders": reminders
    }