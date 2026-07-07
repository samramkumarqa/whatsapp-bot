import sqlite3

DB_FILE = "data/app.db"


def init_activity():

    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS ai_activity(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        customer_phone TEXT,

        activity_type TEXT,

        title TEXT,

        details TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def add_activity(
    customer_phone,
    activity_type,
    title,
    details
):

    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
    INSERT INTO ai_activity(

        customer_phone,
        activity_type,
        title,
        details

    )

    VALUES(?,?,?,?)
    """,(
        customer_phone,
        activity_type,
        title,
        details
    ))

    conn.commit()
    conn.close()

def get_activity(customer_phone):

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT *
        FROM ai_activity
        WHERE customer_phone = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 100
        """,
        (customer_phone,)
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]

def get_activity_timeline(customer_phone):

    import sqlite3

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            created_at,
            activity_type,
            title,
            details
        FROM customer_activity
        WHERE customer_phone = ?
        ORDER BY created_at DESC
        """,
        (customer_phone,)
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]