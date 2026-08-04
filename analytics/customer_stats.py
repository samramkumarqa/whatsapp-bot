"""
Per-customer / per-conversation stats: counts, unread, last message, lead
snapshot, and conversation history. Split out of analytics/analytics.py,
which had grown to mix several unrelated dashboard concerns in one file.
"""

from datetime import datetime

from crm.lead_manager import get_lead
from ai.sales_coach import get_next_best_action
from crm.customer_mapping import (
    get_business_phone_by_user,
    get_business_id,
    get_customer_name,
)
from database.db import get_crm_connection, get_conversation_connection


def get_stats(user_id):

    business_phone = get_business_phone_by_user(user_id)

    if not business_phone:

        return {
            "customers": 0
        }
    conn = get_crm_connection()

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

    conv_conn = get_conversation_connection()
    crm_conn = get_crm_connection()

    business_id = get_business_id(user_id)

    if not business_id:
        conv_conn.close()
        crm_conn.close()
        return []

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
        (f"{business_id}:%",)
    )

    rows = cursor.fetchall()

    # Batch-fetch unread counts for all conversations in one query instead of
    # opening a new sqlite connection per customer (was an N+1 query pattern).
    unread_cursor = conv_conn.execute(
        """
        SELECT conversation_id, unread_count
        FROM unread_messages
        WHERE conversation_id LIKE ?
        """,
        (f"{business_id}:%",)
    )

    unread_by_conversation = {
        r[0]: r[1] for r in unread_cursor.fetchall()
    }

    # Batch-fetch customer names (auto-captured from WhatsApp ProfileName,
    # or manually set) for exactly the customers in this business, instead
    # of one query per customer.
    customer_phones = [
        (
            conv_id.split(":")[1]
            if ":" in conv_id
            else conv_id
        )
        for conv_id in (r[0] for r in rows)
    ]

    name_by_phone = {}

    if customer_phones:

        placeholders = ",".join("?" for _ in customer_phones)

        name_cursor = crm_conn.execute(
            f"""
            SELECT customer_phone, customer_name
            FROM customer_mapping
            WHERE customer_phone IN ({placeholders})
            """,
            customer_phones
        )

        name_by_phone = {
            r[0]: r[1] for r in name_cursor.fetchall()
        }

    customers = []

    for row in rows:

        conversation_id = row[0]

        customer_phone = (
            conversation_id.split(":")[1]
            if ":" in conversation_id
            else conversation_id
        )

        unread_count = unread_by_conversation.get(conversation_id, 0)

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
                status,
                intent,
                buying_stage,
                sentiment,
                priority,
                confidence
            FROM leads
            WHERE customer_phone = ?
            """,
            (customer_phone,)
        )

        lead_row = lead_cursor.fetchone()

        if lead_row:

            lead_score = lead_row[0]
            lead_status = lead_row[1]
            intent = lead_row[2]
            buying_stage = lead_row[3]
            sentiment = lead_row[4]
            priority = lead_row[5]
            confidence = lead_row[6]

        else:

            lead_score = 0
            lead_status = "New"
            intent = ""
            buying_stage = ""
            sentiment = ""
            priority = ""
            confidence = 0

        try:

            last_seen_dt = datetime.strptime(
                row[2],
                "%Y-%m-%d %H:%M:%S"
            )

            last_seen_days = (
                datetime.now() - last_seen_dt
            ).days

        except (TypeError, ValueError):

            last_seen_days = 999

        customers.append({

            "phone": customer_phone,

            "name": name_by_phone.get(customer_phone),

            "message_count": row[1],

            "last_seen": row[2],

            "unread_count": unread_count,

            "last_message": last_message,

            "lead_score": lead_score,

            "status": lead_status,

            "intent": intent,

            "buying_stage": buying_stage,

            "sentiment": sentiment,

            "priority": priority,
            "last_seen_days": last_seen_days,

            "confidence": confidence,

        })

    conv_conn.close()
    crm_conn.close()

    return customers


def search_customers(user_id, query):
    """
    Filter this business's customers by phone number, name, or message
    content - a customer matches if the query appears (case-insensitive)
    in their phone number, their name, or anywhere in their conversation
    history (not just the single most recent message shown in the list).
    """

    customers = get_customer_stats(user_id)

    if not query:
        return customers

    q = query.strip().lower()

    if not q:
        return customers

    # Cheap matches first: phone number and name, both already loaded.
    matched_phones = {
        c["phone"]
        for c in customers
        if q in c["phone"].lower()
        or q in (c["name"] or "").lower()
    }

    # Message-content match: search the actual conversation history, since
    # get_customer_stats() only carries each customer's single latest
    # message, not the full thread.
    business_id = get_business_id(user_id)

    if business_id:

        conn = get_conversation_connection()

        rows = conn.execute(
            """
            SELECT DISTINCT phone
            FROM conversations
            WHERE phone LIKE ?
            AND LOWER(content) LIKE ?
            """,
            (
                f"{business_id}:%",
                f"%{q}%"
            )
        ).fetchall()

        conn.close()

        for row in rows:

            conversation_id = row[0]

            customer_phone = (
                conversation_id.split(":")[1]
                if ":" in conversation_id
                else conversation_id
            )

            matched_phones.add(customer_phone)

    return [
        c for c in customers
        if c["phone"] in matched_phones
    ]


def get_conversation(
    user_id,
    customer_phone
):

    business_id = get_business_id(user_id)

    if not business_id:
        return []

    conversation_id = (
        f"{business_id}:{customer_phone}"
    )

    conn = get_conversation_connection()

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

    business_id = get_business_id(user_id)

    if not business_id:
        return {
            "customers": 0,
            "messages": 0,
            "today_messages": 0
        }

    conn = get_conversation_connection()

    customer_count = conn.execute(
        """
        SELECT COUNT(DISTINCT phone)
        FROM conversations
        WHERE phone LIKE ?
        """,
        (f"{business_id}:%",)
    ).fetchone()[0]

    message_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM conversations
        WHERE phone LIKE ?
        """,
        (f"{business_id}:%",)
    ).fetchone()[0]

    today_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM conversations
        WHERE phone LIKE ?
        AND DATE(created_at)=DATE('now')
        """,
        (f"{business_id}:%",)
    ).fetchone()[0]

    conn.close()

    return {
        "customers": customer_count,
        "messages": message_count,
        "today_messages": today_count
    }


def get_customer_profile(user_id, customer_phone):

    conn = get_conversation_connection()

    business_id = get_business_id(user_id)

    if not business_id:
        return {}

    cursor = conn.execute(
        """
        SELECT
            MIN(created_at),
            MAX(created_at),
            COUNT(*)
        FROM conversations
        WHERE phone = ?
        """,
        (f"{business_id}:{customer_phone}",)
    )

    row = cursor.fetchone()

    conn.close()

    lead = get_lead(customer_phone)

    profile = {
        "customer_phone": customer_phone,
        "name": get_customer_name(customer_phone),
        "first_seen": row[0],
        "last_seen": row[1],
        "message_count": row[2]
    }

    # Merge all lead intelligence automatically
    profile.update(lead)
    profile["next_best_action"] = get_next_best_action(lead)
    return profile


def get_top_customers(
    user_id,
    limit=5
):

    business_id = get_business_id(user_id)

    if not business_id:
        return []
    conn = get_conversation_connection()

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
            f"{business_id}:%",
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
