import sqlite3
import json

DB_PATH = "conversations.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_automation_db():
    conn = get_connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS automation_rules (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT NOT NULL,

        description TEXT,

        enabled INTEGER DEFAULT 1,

        trigger_type TEXT NOT NULL,

        condition_json TEXT NOT NULL,

        action_json TEXT NOT NULL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    )
    """)

    conn.commit()
    conn.close()

def get_all_rules():
    """
    Returns all automation rules.
    """

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM automation_rules
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    rules = []

    for row in rows:

        rule = dict(row)

        rule["condition_json"] = json.loads(
            rule["condition_json"]
        )

        rule["action_json"] = json.loads(
            rule["action_json"]
        )

        rules.append(rule)

    return rules

import json


def save_rule(
    name,
    description,
    trigger_type,
    conditions,
    actions,
    enabled=True
):
    """
    Save a new automation rule.
    """

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO automation_rules
        (
            name,
            description,
            enabled,
            trigger_type,
            condition_json,
            action_json
        )
        VALUES
        (?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            description,
            1 if enabled else 0,
            trigger_type,
            json.dumps(conditions),
            json.dumps(actions)
        )
    )

    conn.commit()

    rule_id = cursor.lastrowid

    conn.close()

    return rule_id

def create_rule(rule: dict):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO automation_rules
        (
            name,
            description,
            enabled,
            trigger_type,
            condition_json,
            action_json
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            rule["name"],
            rule.get("description", ""),
            1 if rule.get("enabled", True) else 0,
            rule["trigger_type"],
            json.dumps(rule["condition_json"]),
            json.dumps(rule["action_json"])
        )
    )

    conn.commit()

    rule_id = cursor.lastrowid

    conn.close()

    return rule_id

def update_rule(
    rule_id: int,
    rule: dict
):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE automation_rules
        SET

            name=?,

            description=?,

            enabled=?,

            trigger_type=?,

            condition_json=?,

            action_json=?,

            updated_at=CURRENT_TIMESTAMP

        WHERE id=?
        """,
        (
            rule["name"],
            rule.get("description", ""),
            1 if rule.get("enabled", True) else 0,
            rule["trigger_type"],
            json.dumps(rule["condition_json"]),
            json.dumps(rule["action_json"]),
            rule_id
        )
    )

    conn.commit()

    conn.close()

def delete_rule(
    rule_id: int
):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM automation_rules
        WHERE id=?
        """,
        (rule_id,)
    )

    conn.commit()

    conn.close()