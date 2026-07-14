import sqlite3

DB_FILE = "data/app.db"


def init_followups():

    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS ai_followups(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        customer_phone TEXT,

        message TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        approved INTEGER DEFAULT 0,

        sent INTEGER DEFAULT 0

    )
    """)

    conn.commit()

    conn.close()


def save_followup(customer_phone, message):

    conn = sqlite3.connect(DB_FILE)

    conn.execute(
        """
        INSERT INTO ai_followups(
            customer_phone,
            message
        )
        VALUES(?,?)
        """,
        (
            customer_phone,
            message
        )
    )

    conn.commit()

    conn.close()


def get_followups(customer_phone):

    conn = sqlite3.connect(DB_FILE)

    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT *
        FROM ai_followups
        WHERE customer_phone=?
        ORDER BY id DESC
        """,
        (customer_phone,)
    ).fetchall()

    conn.close()

    return [dict(r) for r in rows]