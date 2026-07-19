from fastapi import APIRouter
import sqlite3

router = APIRouter()

APP_DB = "data/app.db"   # use your existing DB path
def get_connection():
    conn = sqlite3.connect(APP_DB)
    conn.row_factory = sqlite3.Row
    return conn

# =====================================================
# GET ALL REMINDERS
# =====================================================

@router.get("/reminders")
def get_all_reminders():
    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM reminders
        ORDER BY due_date ASC
    """)

    reminders = [
        dict(row)
        for row in cursor.fetchall()
    ]

    conn.close()

    return {
        "reminders": reminders
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