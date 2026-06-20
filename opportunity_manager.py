import sqlite3

DB_FILE = "data/app.db"


def init_opportunities():

    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS opportunities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_phone TEXT,
        type TEXT,
        confidence INTEGER,
        reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def add_opportunity(
    customer_phone,
    opportunity_type,
    confidence,
    reason
):

    conn = sqlite3.connect(DB_FILE)

    conn.execute(
        """
        INSERT INTO opportunities
        (
            customer_phone,
            type,
            confidence,
            reason
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            customer_phone,
            opportunity_type,
            confidence,
            reason
        )
    )

    conn.commit()
    conn.close()


def get_opportunities(customer_phone):

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.execute(
        """
        SELECT
            opportunity_type,
            confidence,
            reason,
            created_at
        FROM opportunities
        WHERE customer_phone=?
        ORDER BY id DESC
        """,
        (customer_phone,)
    )

    rows = cursor.fetchall()

    conn.close()

    return [
        {
            "type": r[0],
            "confidence": r[1],
            "reason": r[2],
            "created_at": r[3]
        }
        for r in rows
    ]