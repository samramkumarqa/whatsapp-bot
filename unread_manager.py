from database.db import get_conversation_connection

def increment_unread(conversation_id):

    conn = get_conversation_connection()

    conn.execute(
        """
        INSERT INTO unread_messages
        (
            conversation_id,
            unread_count
        )
        VALUES (?,1)

        ON CONFLICT(conversation_id)

        DO UPDATE SET
        unread_count =
        unread_count + 1
        """,
        (conversation_id,)
    )

    conn.commit()
    conn.close()


def clear_unread(conversation_id):

    conn = get_conversation_connection()

    conn.execute(
        """
        UPDATE unread_messages
        SET unread_count = 0
        WHERE conversation_id = ?
        """,
        (conversation_id,)
    )

    conn.commit()
    conn.close()


def get_unread(conversation_id):

    conn = get_conversation_connection()

    cursor = conn.execute(
        """
        SELECT unread_count
        FROM unread_messages
        WHERE conversation_id = ?
        """,
        (conversation_id,)
    )

    row = cursor.fetchone()

    conn.close()

    return row[0] if row else 0