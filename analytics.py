import sqlite3
from unread_manager import get_unread
from lead_manager import get_lead

CONVERSATION_DB = "conversations.db"
CRM_DB = "data/app.db"


def get_stats(user_id):

    business_phone = get_business_phone(user_id)

    if not business_phone:

        return {
            "customers": 0
        }
    conn = sqlite3.connect(CRM_DB)

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

    conn = sqlite3.connect(CONVERSATION_DB)

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

    conn = sqlite3.connect(CONVERSATION_DB)

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

def get_customer_profile(user_id, customer_phone):

    conn = sqlite3.connect(CONVERSATION_DB)

    cursor = conn.execute(
        """
        SELECT
            MIN(created_at),
            MAX(created_at),
            COUNT(*)
        FROM conversations
        WHERE phone = ?
        """,
        (f"{user_id}:{customer_phone}",)
    )

    row = cursor.fetchone()

    conn.close()

    lead = get_lead(customer_phone)

    profile = {
        "customer_phone": customer_phone,
        "first_seen": row[0],
        "last_seen": row[1],
        "message_count": row[2]
    }

    # Merge all lead intelligence automatically
    profile.update(lead)

    return profile

def get_top_customers(
    user_id,
    limit=5
):

    conn = sqlite3.connect(CONVERSATION_DB)

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

def get_sales_funnel(user_id):

    business_phone = get_business_phone(user_id)

    if not business_phone:

        return {
            "total_leads": 0,
            "conversion_rate": 0,
            "funnel": {
                "New": 0,
                "Interested": 0,
                "Qualified": 0,
                "Proposal Sent": 0,
                "Won": 0,
                "Lost": 0
            }
        }

    conn = sqlite3.connect(CRM_DB)

    cursor = conn.execute(
        """
        SELECT
            l.status,
            COUNT(*)
        FROM leads l
        INNER JOIN customer_mapping cm
            ON l.customer_phone = cm.customer_phone
        WHERE cm.business_phone = ?
        GROUP BY l.status
        """,
        (business_phone,)
    )

    rows = cursor.fetchall()

    conn.close()

    funnel = {
        "New": 0,
        "Interested": 0,
        "Qualified": 0,
        "Proposal Sent": 0,
        "Won": 0,
        "Lost": 0
    }

    for status, count in rows:

        if status in funnel:
            funnel[status] = count

    total = sum(funnel.values())

    won = funnel["Won"]

    conversion_rate = (
        round((won / total) * 100, 1)
        if total
        else 0
    )

    return {
        "total_leads": total,
        "conversion_rate": conversion_rate,
        "funnel": funnel
    }

def get_lead_score_dashboard(user_id):

    business_phone = get_business_phone(user_id)

    if not business_phone:

        return {
            "hot": 0,
            "warm": 0,
            "cold": 0,
            "average_score": 0
        }

    conn = sqlite3.connect(CRM_DB)

    cursor = conn.execute(
        """
        SELECT
            l.lead_score
        FROM leads l
        INNER JOIN customer_mapping cm
            ON l.customer_phone = cm.customer_phone
        WHERE cm.business_phone = ?
        """,
        (business_phone,)
    )

    scores = [
        row[0] or 0
        for row in cursor.fetchall()
    ]

    conn.close()

    hot = sum(
        1 for score in scores
        if score >= 80
    )

    warm = sum(
        1 for score in scores
        if 50 <= score < 80
    )

    cold = sum(
        1 for score in scores
        if score < 50
    )

    average = (
        round(sum(scores) / len(scores), 1)
        if scores
        else 0
    )

    return {
        "hot": hot,
        "warm": warm,
        "cold": cold,
        "average_score": average
    }

def get_business_phone(user_id):

    conn = sqlite3.connect(CRM_DB)

    row = conn.execute(
        """
        SELECT whatsapp_number
        FROM customer_numbers
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

    conn.close()

    if row:
        return row[0]

    return None