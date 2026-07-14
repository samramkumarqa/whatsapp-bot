import sqlite3

CRM_DB = "data/app.db"

CONVERSATION_DB = "conversations.db"


def get_crm_connection():

    conn = sqlite3.connect(CRM_DB)

    conn.row_factory = sqlite3.Row

    return conn


def get_conversation_connection():

    conn = sqlite3.connect(CONVERSATION_DB)

    conn.row_factory = sqlite3.Row

    return conn


def execute_crm(query, params=()):

    conn = get_crm_connection()

    cursor = conn.execute(query, params)

    conn.commit()

    conn.close()

    return cursor


def fetchone_crm(query, params=()):

    conn = get_crm_connection()

    row = conn.execute(
        query,
        params
    ).fetchone()

    conn.close()

    return row


def fetchall_crm(query, params=()):

    conn = get_crm_connection()

    rows = conn.execute(
        query,
        params
    ).fetchall()

    conn.close()

    return rows


def execute_conversation(query, params=()):

    conn = get_conversation_connection()

    cursor = conn.execute(query, params)

    conn.commit()

    conn.close()

    return cursor


def fetchone_conversation(query, params=()):

    conn = get_conversation_connection()

    row = conn.execute(
        query,
        params
    ).fetchone()

    conn.close()

    return row


def fetchall_conversation(query, params=()):

    conn = get_conversation_connection()

    rows = conn.execute(
        query,
        params
    ).fetchall()

    conn.close()

    return rows

def commit_and_close(conn):
    conn.commit()
    conn.close()


def close_connection(conn):
    conn.close()