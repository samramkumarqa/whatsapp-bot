import json

from automation.database import get_connection


# --------------------------------------------------------
# Create Rule
# --------------------------------------------------------

def create_rule(data):

    conn = get_connection()

    cursor = conn.execute(
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
            data["name"],
            data.get("description", ""),
            int(data.get("enabled", True)),
            data["trigger_type"],
            json.dumps(data["condition_json"]),
            json.dumps(data["action_json"])
        )
    )

    conn.commit()

    rule_id = cursor.lastrowid

    conn.close()

    return rule_id


# --------------------------------------------------------
# Get All Rules
# --------------------------------------------------------

def get_rules(enabled_only=False):

    conn = get_connection()

    if enabled_only:

        rows = conn.execute(
            """
            SELECT *
            FROM automation_rules
            WHERE enabled = 1
            ORDER BY id
            """
        ).fetchall()

    else:

        rows = conn.execute(
            """
            SELECT *
            FROM automation_rules
            ORDER BY id
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

            "condition_json": json.loads(row["condition_json"]),

            "action_json": json.loads(row["action_json"]),

            "created_at": row["created_at"],

            "updated_at": row["updated_at"]

        })

    return rules


# --------------------------------------------------------
# Get Single Rule
# --------------------------------------------------------

def get_rule(rule_id):

    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM automation_rules
        WHERE id = ?
        """,
        (rule_id,)
    ).fetchone()

    conn.close()

    if row is None:
        return None

    return {

        "id": row["id"],

        "name": row["name"],

        "description": row["description"],

        "enabled": bool(row["enabled"]),

        "trigger_type": row["trigger_type"],

        "condition_json": json.loads(row["condition_json"]),

        "action_json": json.loads(row["action_json"]),

        "created_at": row["created_at"],

        "updated_at": row["updated_at"]

    }


# --------------------------------------------------------
# Update Rule
# --------------------------------------------------------

def update_rule(rule_id, data):

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
            data["name"],
            data.get("description", ""),
            int(data.get("enabled", True)),
            data["trigger_type"],
            json.dumps(data["condition_json"]),
            json.dumps(data["action_json"]),
            rule_id
        )
    )

    conn.commit()

    conn.close()


# --------------------------------------------------------
# Delete Rule
# --------------------------------------------------------

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


# --------------------------------------------------------
# Enable / Disable Rule
# --------------------------------------------------------

def set_enabled(rule_id, enabled):

    conn = get_connection()

    conn.execute(
        """
        UPDATE automation_rules

        SET

            enabled = ?,

            updated_at = CURRENT_TIMESTAMP

        WHERE id = ?
        """,
        (
            int(enabled),
            rule_id
        )
    )

    conn.commit()

    conn.close()