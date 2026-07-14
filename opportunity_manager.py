from database.db import get_crm_connection

def init_opportunities():

    conn = get_crm_connection()
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
    reason,
    estimated_value=0
):

    conn = get_crm_connection()

    row = conn.execute(
        """
        SELECT id
        FROM opportunities
        WHERE customer_phone = ?
        AND opportunity_type = ?
        AND status = 'Open'
        """,
        (
            customer_phone,
            opportunity_type
        )
    ).fetchone()

    if row:

        conn.execute(
            """
            UPDATE opportunities
            SET
                confidence = ?,
                reason = ?,
                estimated_value = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                confidence,
                reason,
                estimated_value,
                row[0]
            )
        )

    else:

        conn.execute(
            """
            INSERT INTO opportunities
            (
                customer_phone,
                opportunity_type,
                confidence,
                reason,
                estimated_value,
                status
            )
            VALUES (?, ?, ?, ?, 'Open')
            """,
            (
                customer_phone,
                opportunity_type,
                confidence,
                reason,
                estimated_value
            )
        )

    conn.commit()
    conn.close()


def get_opportunities(customer_phone):

    conn = get_crm_connection()

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