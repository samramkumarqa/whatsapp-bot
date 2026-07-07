from lead_ai import calculate_lead_score
import sqlite3

DB_FILE = "data/app.db"

DEFAULT_LEAD = {
    "customer_phone": "",
    "status": "New",
    "notes": "",
    "confidence": 0,
    "reason": "",
    "updated_by": "Manual",

    "lead_score": 0,
    "intent": "",
    "buying_stage": "",
    "sentiment": "",
    "objection": "",

    "probability": 0,
    "priority": "Medium",

    "next_action": "",
    "follow_up_days": 1,

    "summary": "",
    "ai_summary": "",

    "tags": ""
}

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
    conn.row_factory = sqlite3.Row

    row = conn.execute(
        """
        SELECT *
        FROM leads
        WHERE customer_phone = ?
        """,
        (customer_phone,)
    ).fetchone()

    conn.close()

    if row:
        return dict(row)

    lead = DEFAULT_LEAD.copy()
    lead["customer_phone"] = customer_phone

    return lead


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

def get_lead_categories():

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.execute("""
        SELECT
            customer_phone,
            status,
            lead_score
        FROM leads
    """)

    rows = cursor.fetchall()

    conn.close()

    hot = []
    warm = []
    cold = []

    for phone, status, score in rows:

        lead = {
            "customer_phone": phone,
            "status": status,
            "lead_score": score
        }

        if score >= 80:
            hot.append(lead)
        elif score >= 50:
            warm.append(lead)
        else:
            cold.append(lead)

    return {
        "hot": hot,
        "warm": warm,
        "cold": cold
    }

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

def update_lead_intelligence(
    customer_phone,
    analysis
):
    """
    Save AI Lead Intelligence into CRM.
    """

    conn = sqlite3.connect(DB_FILE)

    conn.execute(
        """
        INSERT INTO leads
        (
            customer_phone,
            status,
            confidence,
            reason,
            updated_by,
            lead_score,

            intent,
            buying_stage,
            sentiment,
            objection,
            priority,
            probability,
            next_action,
            follow_up_days,
            summary,
            tags
        )

        VALUES
        (
            ?,?,?,?,?,?,
            ?,?,?,?,?,?,
            ?,?,?,?
        )

        ON CONFLICT(customer_phone)
        DO UPDATE SET

            status=excluded.status,
            confidence=excluded.confidence,
            reason=excluded.reason,
            updated_by='AI',
            lead_score=excluded.lead_score,

            intent=excluded.intent,
            buying_stage=excluded.buying_stage,
            sentiment=excluded.sentiment,
            objection=excluded.objection,
            priority=excluded.priority,
            probability=excluded.probability,
            next_action=excluded.next_action,
            follow_up_days=excluded.follow_up_days,
            summary=excluded.summary,
            tags=excluded.tags
        """,
        (
            customer_phone,

            analysis["buying_stage"],

            analysis["confidence"],

            analysis["summary"],

            "AI",

            analysis["lead_score"],

            analysis["intent"],

            analysis["buying_stage"],

            analysis["sentiment"],

            analysis["objection"],

            analysis["priority"],

            analysis["probability"],

            analysis["next_action"],

            analysis["follow_up_days"],

            analysis["summary"],

            ",".join(analysis["tags"])
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

        VALUES
        (
            ?,?,?,?,?
        )
        """,
        (
            customer_phone,

            analysis["buying_stage"],

            analysis["confidence"],

            analysis["summary"],

            "AI"
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