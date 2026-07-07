import sqlite3
from datetime import datetime, timedelta

DB_FILE = "data/app.db"


def init_reminders():

    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_phone TEXT,
        reminder_text TEXT,
        due_date TEXT,
        status TEXT DEFAULT 'Pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def complete_reminder(customer_phone):

    conn = sqlite3.connect(DB_FILE)

    conn.execute(
        """
        UPDATE reminders

        SET completed=1

        WHERE customer_phone=?
        AND completed=0
        """,
        (customer_phone,)
    )

    conn.commit()
    conn.close()

def create_reminder(
    customer_phone,
    reminder_text,
    due_in_days
):

    due_date = (
        datetime.now()
        +
        timedelta(days=due_in_days)
    ).strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_FILE)

    conn.execute(
        """
        INSERT INTO reminders
        (
            customer_phone,
            reminder_text,
            due_date
        )
        VALUES (?, ?, ?)
        """,
        (
            customer_phone,
            reminder_text,
            due_date
        )
    )

    conn.commit()
    conn.close()


def get_reminders():

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.execute(
        """
        SELECT
            id,
            customer_phone,
            reminder_text,
            due_date,
            status
        FROM reminders
        ORDER BY due_date ASC
        """
    )

    rows = cursor.fetchall()

    conn.close()

    return [
        {
            "id": r[0],
            "customer_phone": r[1],
            "reminder_text": r[2],
            "due_date": r[3],
            "status": r[4]
        }
        for r in rows
    ]

def upsert_reminder(
    customer_phone,
    reminder_text,
    days
):
    """
    Create or update an active reminder.
    """

    conn = sqlite3.connect(DB_FILE)

    due_date = (
        datetime.now() +
        timedelta(days=days)
    ).strftime("%Y-%m-%d")

    cursor = conn.execute(
        """
        SELECT id
        FROM reminders
        WHERE customer_phone=?
        AND completed=0
        """,
        (customer_phone,)
    )

    row = cursor.fetchone()

    if row:

        conn.execute(
            """
            UPDATE reminders

            SET

                reminder_text=?,
                due_date=?,
                updated_at=CURRENT_TIMESTAMP

            WHERE id=?
            """,
            (
                reminder_text,
                due_date,
                row[0]
            )
        )

    else:

        conn.execute(
            """
            INSERT INTO reminders
            (
                customer_phone,
                reminder_text,
                due_date
            )

            VALUES
            (
                ?,?,?
            )
            """,
            (
                customer_phone,
                reminder_text,
                due_date
            )
        )

    conn.commit()
    conn.close()

def reminder_exists(customer_phone):

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.execute(
        """
        SELECT id
        FROM reminders
        WHERE customer_phone=?
        AND completed=0
        LIMIT 1
        """,
        (customer_phone,)
    )

    exists = cursor.fetchone() is not None

    conn.close()

    return exists

def get_customer_reminders(customer_phone):

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT *
        FROM reminders
        WHERE customer_phone=?
        ORDER BY reminder_date DESC
        """,
        (customer_phone,)
    ).fetchall()

    conn.close()

    return [dict(r) for r in rows]