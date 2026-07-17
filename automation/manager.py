import json

from automation.database import get_connection


def create_rule(
    name,
    trigger_type,
    condition,
    action,
    description="",
    enabled=True
):
    conn = get_connection()

    conn.execute(
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
            name,
            description,
            int(enabled),
            trigger_type,
            json.dumps(condition),
            json.dumps(action)
        )
    )

    conn.commit()
    conn.close()


def get_rules(enabled_only=False):

    conn = get_connection()

    if enabled_only:

        rows = conn.execute(
            """
            SELECT *
            FROM automation_rules
            WHERE enabled = 1
            """
        ).fetchall()

    else:

        rows = conn.execute(
            """
            SELECT *
            FROM automation_rules
            """
        ).fetchall()

    conn.close()

    rules = []

    for row in rows:

        rules.append({

            "id": row["id"],

            "name": row["name"],

            "description": row["description"],

            "enabled": bool(row["enabled"]),

            "trigger_type": row["trigger_type"],

            "condition": json.loads(row["condition_json"]),

            "action": json.loads(row["action_json"])
        })

    return rules


def delete_rule(rule_id):

    conn = get_connection()

    conn.execute(
        """
        DELETE FROM automation_rules
        WHERE id = ?
        """,
        (rule_id,)
    )

    conn.commit()
    conn.close()


def set_enabled(
    rule_id,
    enabled
):

    conn = get_connection()

    conn.execute(
        """
        UPDATE automation_rules
        SET enabled = ?
        WHERE id = ?
        """,
        (
            int(enabled),
            rule_id
        )
    )

    conn.commit()
    conn.close()


def update_rule(
    rule_id,
    name,
    description,
    trigger_type,
    condition,
    action,
    enabled
):

    conn = get_connection()

    conn.execute(
        """
        UPDATE automation_rules
        SET

            name = ?,

            description = ?,

            enabled = ?,

            trigger_type = ?,

            condition_json = ?,

            action_json = ?,

            updated_at = CURRENT_TIMESTAMP

        WHERE id = ?
        """,
        (
            name,
            description,
            int(enabled),
            trigger_type,
            json.dumps(condition),
            json.dumps(action),
            rule_id
        )
    )

    conn.commit()
    conn.close()