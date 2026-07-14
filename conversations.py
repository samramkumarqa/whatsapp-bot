from database.db import get_conversation_connection


def get_connection():
    return get_conversation_connection()


def init_db():

    conn = get_connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT,
        role TEXT,
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def add_message(phone, role, content):

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO conversations
        (phone, role, content)
        VALUES (?, ?, ?)
        """,
        (phone, role, content)
    )

    conn.commit()
    conn.close()


def get_history(phone, limit=10):

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT role, content
        FROM conversations
        WHERE phone = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (phone, limit)
    ).fetchall()

    conn.close()

    rows.reverse()

    return [
        {
            "role": row[0],
            "content": row[1]
        }
        for row in rows
    ]


def clear_history(phone):

    conn = get_connection()

    conn.execute(
        """
        DELETE FROM conversations
        WHERE phone = ?
        """,
        (phone,)
    )

    conn.commit()
    conn.close()

def get_last_customer_update(user_id):
    conn = get_conversation_connection()

    row = conn.execute(
        """
        SELECT MAX(created_at)
        FROM conversations
        WHERE phone LIKE ?
        """,
        (f"{user_id}:%",)
    ).fetchone()

    conn.close()