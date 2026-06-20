from lead_ai import calculate_lead_score
print(calculate_lead_score("Qualified", 100))
print(calculate_lead_score("Interested", 100))
import sqlite3

DB_FILE = "data/app.db"

def init_leads():

    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS leads (
    customer_phone TEXT PRIMARY KEY,
    status TEXT DEFAULT 'New',
    notes TEXT DEFAULT '',
    confidence INTEGER DEFAULT 0,
    reason TEXT DEFAULT '',
    updated_by TEXT DEFAULT 'Manual'
)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS opportunities (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            customer_phone TEXT,

            opportunity_type TEXT,

            confidence INTEGER,

            reason TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS lead_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_phone TEXT,
        status TEXT,
        confidence INTEGER,
        reason TEXT,
        updated_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def get_lead(customer_phone):

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.execute(
        """
        SELECT
            status,
            notes,
            confidence,
            reason,
            updated_by,
            lead_score
        FROM leads
        WHERE customer_phone=?
        """,
        (customer_phone,)
    )

    row = cursor.fetchone()

    conn.close()

    if row:
        return {
            "status": row[0],
            "notes": row[1],
            "confidence": row[2],
            "reason": row[3],
            "updated_by": row[4],
            "lead_score": row[5]
        }

    return {
        "status": "New",
        "notes": "",
        "confidence": 0,
        "reason": "",
        "updated_by": "Manual",
        "lead_score": 0
    }



def update_lead(
    customer_phone,
    status,
    notes,
    confidence=0,
    reason="",
    updated_by="Manual"
):

    lead_score = calculate_lead_score(
        status,
        confidence
    )

    conn = sqlite3.connect(DB_FILE)

    conn.execute(
        """
        INSERT OR REPLACE INTO leads
        (
            customer_phone,
            status,
            notes,
            confidence,
            reason,
            updated_by,
            lead_score
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            customer_phone,
            status,
            notes,
            confidence,
            reason,
            updated_by,
            lead_score
        )
    )

    conn.execute(
        """
        INSERT INTO lead_history
        (
            customer_phone,
            status,
            confidence,
            reason,
            updated_by
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            customer_phone,
            status,
            confidence,
            reason,
            updated_by
        )
    )

    conn.commit()
    conn.close()

def get_lead_timeline(customer_phone):

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.execute(
        """
        SELECT
            status,
            confidence,
            reason,
            updated_by,
            created_at
        FROM lead_history
        WHERE customer_phone = ?
        ORDER BY created_at DESC
        """,
        (customer_phone,)
    )

    rows = cursor.fetchall()

    conn.close()

    return [
        {
            "status": row[0],
            "confidence": row[1],
            "reason": row[2],
            "updated_by": row[3],
            "created_at": row[4]
        }
        for row in rows
    ]


def save_opportunity(
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
            opportunity_type,
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

def auto_update_lead(
    customer_phone,
    ai_status,
    confidence=0,
    reason=""
):

    current = get_lead(customer_phone)

    current_status = current["status"]

    locked_statuses = [
        "Proposal Sent",
        "Closed Won",
        "Closed Lost"
    ]

    if current_status in locked_statuses:
        return

    update_lead(
        customer_phone,
        ai_status,
        current["notes"],
        confidence,
        reason,
        "AI"
    )