"""
One-time data migration: copies rows from the old SQLite files
(data/app.db, conversations.db) into the Postgres database the app now
runs on (see database/db.py). Safe to re-run - every insert uses
ON CONFLICT ... DO NOTHING, so rows already present in Postgres (matched
by primary key) are skipped rather than duplicated or overwritten.

Usage:
    DATABASE_URL=postgresql://user:pass@host/db python migrate_sqlite_to_postgres.py

Optional env vars (default to the repo-relative paths used locally):
    CRM_SQLITE_PATH          (default: data/app.db)
    CONVERSATION_SQLITE_PATH (default: conversations.db)

What this does NOT do: touch the SQLite files (read-only), or delete/
modify anything already in Postgres. It only adds rows that don't
already exist there.
"""

import os
import sqlite3
import sys

# database/db.py refuses to import at all without DATABASE_URL set - fail
# fast with a clear message instead of a buried traceback.
if not os.getenv("DATABASE_URL"):
    print(
        "DATABASE_URL is not set. Point it at your Postgres instance "
        "before running this script, e.g.:\n\n"
        "    DATABASE_URL=postgresql://user:pass@host/db "
        "python migrate_sqlite_to_postgres.py\n"
    )
    sys.exit(1)

CRM_SQLITE_PATH = os.getenv("CRM_SQLITE_PATH", "data/app.db")
CONVERSATION_SQLITE_PATH = os.getenv("CONVERSATION_SQLITE_PATH", "conversations.db")

# Make sure every table this script migrates into actually exists in
# Postgres first - each init_*() is CREATE TABLE IF NOT EXISTS, so this
# is safe to call even if main.py already ran it on boot.
from crm.customer_mapping import init_customer_mapping, init_business_settings
from crm.lead_manager import init_leads
from crm.opportunity_manager import init_opportunities
from crm.tag_manager import init_tags
from crm.activity_manager import init_activity
from crm.followup_manager import init_followups
from reminder_manager import init_reminders
from conversations import init_db as init_conversations
from unread_manager import init_unread
from automation.database import init_automation_db
from automation.rule_stats import init_rule_executions

from database.db import get_crm_connection, get_conversation_connection

# (table, source sqlite file, Postgres connection getter, SERIAL pk column
# to reset the sequence for (None if the table has no SERIAL column), the
# column(s) that make up its real primary/unique key for ON CONFLICT)
TABLES = [
    ("customer_numbers", CRM_SQLITE_PATH, get_crm_connection, None, ("user_id",)),
    ("customer_mapping", CRM_SQLITE_PATH, get_crm_connection, None, ("customer_phone",)),
    ("business_settings", CRM_SQLITE_PATH, get_crm_connection, None, ("user_id",)),
    ("leads", CRM_SQLITE_PATH, get_crm_connection, None, ("customer_phone",)),
    ("lead_history", CRM_SQLITE_PATH, get_crm_connection, "id", ("id",)),
    ("opportunities", CRM_SQLITE_PATH, get_crm_connection, "id", ("id",)),
    ("reminders", CRM_SQLITE_PATH, get_crm_connection, "id", ("id",)),
    ("customer_tags", CRM_SQLITE_PATH, get_crm_connection, None, ("customer_phone", "tag")),
    ("ai_activity", CRM_SQLITE_PATH, get_crm_connection, "id", ("id",)),
    ("ai_followups", CRM_SQLITE_PATH, get_crm_connection, "id", ("id",)),
    ("conversations", CONVERSATION_SQLITE_PATH, get_conversation_connection, "id", ("id",)),
    ("unread_messages", CONVERSATION_SQLITE_PATH, get_conversation_connection, None, ("conversation_id",)),
    ("automation_rules", CONVERSATION_SQLITE_PATH, get_conversation_connection, "id", ("id",)),
    ("automation_rule_executions", CONVERSATION_SQLITE_PATH, get_conversation_connection, "id", ("id",)),
    # automation_history is a dead table (0 rows, unreferenced anywhere in
    # the codebase as of this migration) - deliberately not migrated.
]


def migrate_table(table, sqlite_path, get_pg_conn, serial_pk, conflict_columns):

    if not os.path.exists(sqlite_path):
        print(f"  {table}: skipped ({sqlite_path} not found)")
        return 0

    sconn = sqlite3.connect(sqlite_path)
    sconn.row_factory = sqlite3.Row

    try:
        rows = sconn.execute(f'SELECT * FROM "{table}"').fetchall()
    except sqlite3.OperationalError as e:
        print(f"  {table}: skipped ({e})")
        sconn.close()
        return 0

    sconn.close()

    if not rows:
        print(f"  {table}: 0 rows in source, nothing to migrate")
        return 0

    columns = rows[0].keys()
    col_list = ",".join(f'"{c}"' for c in columns)
    placeholders = ",".join("?" for _ in columns)
    conflict_target = ",".join(f'"{c}"' for c in conflict_columns)

    pg_conn = get_pg_conn()

    inserted = 0
    for row in rows:
        values = tuple(row[c] for c in columns)
        cursor = pg_conn.execute(
            f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) '
            f'ON CONFLICT ({conflict_target}) DO NOTHING',
            values
        )
        if cursor.rowcount:
            inserted += 1

    if serial_pk:
        pg_conn.execute(
            f"SELECT setval(pg_get_serial_sequence('{table}', '{serial_pk}'), "
            f'COALESCE((SELECT MAX("{serial_pk}") FROM "{table}"), 1))'
        )

    pg_conn.commit()
    pg_conn.close()

    print(f"  {table}: {inserted} new row(s) inserted ({len(rows)} in source)")
    return inserted


def main():

    print("Ensuring Postgres schema exists...")
    init_customer_mapping()
    init_business_settings()
    init_leads()
    init_opportunities()
    init_tags()
    init_activity()
    init_followups()
    init_reminders()
    init_conversations()
    init_unread()
    init_automation_db()
    init_rule_executions()

    print(f"\nMigrating from {CRM_SQLITE_PATH} / {CONVERSATION_SQLITE_PATH} ...\n")

    total = 0
    for table, sqlite_path, get_pg_conn, serial_pk, conflict_columns in TABLES:
        total += migrate_table(table, sqlite_path, get_pg_conn, serial_pk, conflict_columns)

    print(f"\nDone. {total} row(s) newly inserted (re-running this script is safe).")


if __name__ == "__main__":
    main()
