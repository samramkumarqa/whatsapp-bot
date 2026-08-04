import json

from datetime import datetime, timedelta
from database.db import get_crm_connection, get_conversation_connection

def init_reminders():

    conn = get_crm_connection()

    # NOTE: completed and updated_at were missing here - live production
    # data/app.db has both (added via manual ALTER TABLE at some point), and
    # complete_reminder()/upsert_reminder()/reminder_exists() below all
    # write to or filter on `completed` unconditionally. A fresh database
    # would fail on the very first call to any of them.
    conn.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_phone TEXT,
        reminder_text TEXT,
        due_date TEXT,
        status TEXT DEFAULT 'Pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed INTEGER DEFAULT 0,
        updated_at TIMESTAMP
    )
    """)

    # source_rule_id/source_rule_name: a snapshot of which automation rule
    # (and its name at the time) created/last-refreshed this reminder - so
    # the dashboard can show "Triggered by: <rule>" and so stale reminders
    # (rule deleted, or edited to say something else) can be detected later.
    # Snapshotting the name rather than only the id means the label still
    # makes sense even if the rule gets renamed or deleted afterward.
    existing_columns = {
        row[1] for row in
        conn.execute("PRAGMA table_info(reminders)").fetchall()
    }

    if "source_rule_id" not in existing_columns:
        conn.execute(
            "ALTER TABLE reminders ADD COLUMN source_rule_id INTEGER"
        )

    if "source_rule_name" not in existing_columns:
        conn.execute(
            "ALTER TABLE reminders ADD COLUMN source_rule_name TEXT"
        )

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_reminders_customer_phone "
        "ON reminders(customer_phone)"
    )

    conn.commit()
    conn.close()

def complete_reminder(customer_phone):

    conn = get_crm_connection()

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

    conn = get_crm_connection()

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

    conn = get_crm_connection()

    cursor = conn.execute(
        """
        SELECT
            id,
            customer_phone,
            reminder_text,
            due_date,
            status,
            source_rule_id,
            source_rule_name
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
            "status": r[4],
            "source_rule_id": r[5],
            "source_rule_name": r[6]
        }
        for r in rows
    ]

def upsert_reminder(
    customer_phone,
    reminder_text,
    days,
    source_rule_id=None,
    source_rule_name=None
):
    """
    Create or update an active reminder.
    """

    conn = get_crm_connection()

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
                updated_at=CURRENT_TIMESTAMP,
                source_rule_id=?,
                source_rule_name=?

            WHERE id=?
            """,
            (
                reminder_text,
                due_date,
                source_rule_id,
                source_rule_name,
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
                due_date,
                source_rule_id,
                source_rule_name
            )

            VALUES
            (
                ?,?,?,?,?
            )
            """,
            (
                customer_phone,
                reminder_text,
                due_date,
                source_rule_id,
                source_rule_name
            )
        )

    conn.commit()
    conn.close()

def reminder_exists(customer_phone):

    conn = get_crm_connection()
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

    conn = get_crm_connection()

    # NOTE: this previously ordered by "reminder_date", a column that has
    # never existed on this table (it's "due_date") - every call raised
    # sqlite3.OperationalError. This function is live, used by
    # timeline_manager.get_customer_timeline(), which backs the
    # /customer-timeline and /timeline routes in api/customer.py - the
    # customer timeline view was broken every time it was opened.
    rows = conn.execute(
        """
        SELECT *
        FROM reminders
        WHERE customer_phone=?
        ORDER BY due_date DESC
        """,
        (customer_phone,)
    ).fetchall()

    conn.close()

    return [dict(r) for r in rows]


def _current_create_reminder_texts(rule_row):
    """
    Every "create_reminder" action text currently configured on one
    automation rule row (a rule can have more than one action, and older
    rows may store action_json as a single dict rather than a list).
    """

    actions = json.loads(rule_row["action_json"])

    if isinstance(actions, dict):
        actions = [actions]

    return {
        action.get("params", {}).get("text")
        for action in actions
        if action.get("name") == "create_reminder"
    }


def find_stale_reminders():
    """
    A reminder is "stale" once it no longer reflects what its originating
    rule would currently produce:

    - the rule it was created from has since been deleted, or
    - that rule no longer has a Create Reminder action at all, or
    - the rule still has one, but its text has been edited since this
      reminder was last (re)created.

    Reminders with no source_rule_id (created before this tracking existed,
    or otherwise not tied to a rule) are left alone - there's nothing to
    compare them against, so they're never considered stale.

    automation_rules lives in conversations.db while reminders lives in
    data/app.db (see database/db.py), so this pulls both and compares in
    Python rather than a single cross-database SQL query.
    """

    crm_conn = get_crm_connection()

    reminders = crm_conn.execute(
        """
        SELECT id, customer_phone, reminder_text, source_rule_id, source_rule_name
        FROM reminders
        WHERE completed = 0
        AND source_rule_id IS NOT NULL
        """
    ).fetchall()

    crm_conn.close()

    if not reminders:
        return []

    conv_conn = get_conversation_connection()

    rules_by_id = {
        row["id"]: row
        for row in conv_conn.execute(
            "SELECT id, name, action_json FROM automation_rules"
        ).fetchall()
    }

    conv_conn.close()

    stale = []

    for reminder in reminders:

        rule_row = rules_by_id.get(reminder["source_rule_id"])

        if rule_row is None:
            reason = (
                f"Rule \"{reminder['source_rule_name'] or 'Unknown'}\" "
                "no longer exists"
            )

        else:

            current_texts = _current_create_reminder_texts(rule_row)

            if not current_texts:
                reason = (
                    f"Rule \"{rule_row['name']}\" no longer has a "
                    "Create Reminder action"
                )

            elif reminder["reminder_text"] not in current_texts:
                reason = (
                    f"Rule \"{rule_row['name']}\" now says something "
                    "different"
                )

            else:
                continue

        stale.append({
            "id": reminder["id"],
            "customer_phone": reminder["customer_phone"],
            "reminder_text": reminder["reminder_text"],
            "source_rule_name": reminder["source_rule_name"],
            "reason": reason
        })

    return stale


def delete_stale_reminders():
    """
    Deletes every reminder find_stale_reminders() currently flags, and
    returns how many were removed.
    """

    stale = find_stale_reminders()

    if not stale:
        return 0

    conn = get_crm_connection()

    conn.executemany(
        "DELETE FROM reminders WHERE id = ?",
        [(r["id"],) for r in stale]
    )

    conn.commit()
    conn.close()

    return len(stale)