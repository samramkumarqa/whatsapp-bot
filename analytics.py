import sqlite3
from datetime import datetime
from unread_manager import get_unread
from lead_manager import get_lead
DB_FILE = "conversations.db"
CONVERSATION_DB = "conversations.db"
CRM_DB = "data/app.db"


def get_stats(user_id):

    import sqlite3

    conn = sqlite3.connect("data/app.db")

    cursor = conn.execute(
        """
        SELECT whatsapp_number
        FROM customer_numbers
        WHERE user_id = ?
        """,
        (user_id,)
    )

    row = cursor.fetchone()

    customer_count = 0

    if row:

        business_phone = row[0]

        cursor = conn.execute(
            """
            SELECT COUNT(*)
            FROM customer_mapping
            WHERE business_phone = ?
            """,
            (business_phone,)
        )

        customer_count = cursor.fetchone()[0]

    conn.close()

    return {
        "customers": customer_count
    }

def get_customer_stats(user_id):

    conv_conn = sqlite3.connect(CONVERSATION_DB)
    crm_conn = sqlite3.connect(CRM_DB)

    cursor = conv_conn.execute(
        """
        SELECT
            phone,
            COUNT(*) as message_count,
            MAX(created_at) as last_seen
        FROM conversations
        WHERE phone LIKE ?
        GROUP BY phone
        ORDER BY last_seen DESC
        """,
        (f"{user_id}:%",)
    )

    rows = cursor.fetchall()

    customers = []

    for row in rows:

        conversation_id = row[0]

        customer_phone = (
            conversation_id.split(":")[1]
            if ":" in conversation_id
            else conversation_id
        )

        unread_count = get_unread(conversation_id)

        last_message_cursor = conv_conn.execute(
            """
            SELECT content
            FROM conversations
            WHERE phone = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (conversation_id,)
        )

        last_message_row = last_message_cursor.fetchone()

        last_message = (
            last_message_row[0]
            if last_message_row
            else ""
        )

        lead_cursor = crm_conn.execute(
            """
            SELECT
                lead_score,
                status
            FROM leads
            WHERE customer_phone = ?
            """,
            (customer_phone,)
        )

        lead_row = lead_cursor.fetchone()

        lead_score = lead_row[0] if lead_row else 0
        lead_status = lead_row[1] if lead_row else "New"

        customers.append({
            "phone": customer_phone,
            "message_count": row[1],
            "last_seen": row[2],
            "unread_count": unread_count,
            "last_message": last_message,
            "lead_score": lead_score,
            "status": lead_status
        })

    conv_conn.close()
    crm_conn.close()

    return customers

def get_conversation(
    user_id,
    customer_phone
):

    conversation_id = (
        f"{user_id}:{customer_phone}"
    )

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.execute(
        """
        SELECT role,
               content,
               created_at
        FROM conversations
        WHERE phone = ?
        ORDER BY id
        """,
        (conversation_id,)
    )

    rows = cursor.fetchall()

    conn.close()

    return [
        {
            "role": row[0],
            "content": row[1],
            "created_at": row[2]
        }
        for row in rows
    ]

def get_dashboard_metrics(user_id):

    conn = sqlite3.connect(DB_FILE)

    customer_count = conn.execute(
        """
        SELECT COUNT(DISTINCT phone)
        FROM conversations
        WHERE phone LIKE ?
        """,
        (f"{user_id}:%",)
    ).fetchone()[0]

    message_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM conversations
        WHERE phone LIKE ?
        """,
        (f"{user_id}:%",)
    ).fetchone()[0]

    today_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM conversations
        WHERE phone LIKE ?
        AND DATE(created_at)=DATE('now')
        """,
        (f"{user_id}:%",)
    ).fetchone()[0]

    conn.close()

    return {
        "customers": customer_count,
        "messages": message_count,
        "today_messages": today_count
    }

def get_customer_profile(
    user_id,
    customer_phone
):

    import sqlite3

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.execute(
        """
        SELECT
            MIN(created_at),
            MAX(created_at),
            COUNT(*)
        FROM conversations
        WHERE phone = ?
        """,
        (
            f"{user_id}:{customer_phone}",
        )
    )

    row = cursor.fetchone()

    conn.close()

    lead = get_lead(customer_phone)

    return {
        "first_seen": row[0],
        "last_seen": row[1],
        "message_count": row[2],

        "lead_status": lead.get(
            "status",
            "New"
        ),

        "confidence": lead.get(
            "confidence",
            0
        ),

        "reason": lead.get(
            "reason",
            ""
        ),

        "updated_by": lead.get(
            "updated_by",
            "Manual"
        ),

        "notes": lead.get(
            "notes",
            ""
        )
    }

def get_top_customers(
    user_id,
    limit=5
):

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.execute(
        """
        SELECT
            phone,
            COUNT(*) as message_count
        FROM conversations
        WHERE phone LIKE ?
        GROUP BY phone
        ORDER BY message_count DESC
        LIMIT ?
        """,
        (
            f"{user_id}:%",
            limit
        )
    )

    rows = cursor.fetchall()

    conn.close()

    customers = []

    for row in rows:

        conversation_id = row[0]

        customer_phone = (
            conversation_id.split(":")[1]
            if ":" in conversation_id
            else conversation_id
        )

        customers.append({
            "phone": customer_phone,
            "message_count": row[1]
        })

    return customers