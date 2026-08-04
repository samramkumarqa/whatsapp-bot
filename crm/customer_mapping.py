from database.db import get_crm_connection

def init_customer_mapping():

    conn = get_crm_connection()

    # Business registration table
    # NOTE: business_id was missing here - the live production data/app.db
    # has it (added via a manual ALTER TABLE at some point), and
    # save_customer_number() below writes to it unconditionally. A fresh
    # database would fail with "table customer_numbers has no column named
    # business_id" on the very first call.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customer_numbers (
            user_id TEXT PRIMARY KEY,
            whatsapp_number TEXT NOT NULL,
            business_id TEXT
        )
    """)

    # Customer → Business mapping table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customer_mapping (
            customer_phone TEXT PRIMARY KEY,
            business_phone TEXT NOT NULL,
            customer_name TEXT
        )
    """)

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_customer_mapping_business_phone "
        "ON customer_mapping(business_phone)"
    )

    # customer_name existed in a schema created before this column was
    # added - patch it in for any database created by an older version.
    existing_columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(customer_mapping)"
        ).fetchall()
    }

    if "customer_name" not in existing_columns:
        conn.execute(
            "ALTER TABLE customer_mapping ADD COLUMN customer_name TEXT"
        )

    conn.commit()
    conn.close()


# --------------------------------------------------
# BUSINESS REGISTRATION
# user_id -> business whatsapp number
# --------------------------------------------------
def get_customers(user_id):

    conn = get_crm_connection()
    cursor = conn.execute(
        """
        SELECT customer_phone
        FROM customer_mapping
        WHERE business_phone = (
            SELECT whatsapp_number
            FROM customer_numbers
            WHERE user_id = ?
        )
        """,
        (user_id,)
    )

    customers = [
        row[0]
        for row in cursor.fetchall()
    ]
    return customers

    conn.close()
def get_user_id_by_business_id(business_id):

    conn = get_crm_connection()

    cursor = conn.execute(
        """
        SELECT user_id
        FROM customer_numbers
        WHERE business_id = ?
        """,
        (business_id,)
    )

    row = cursor.fetchone()

    conn.close()

    if not row:
        return None

    return row[0]

def get_business_id(user_id):

    conn = get_crm_connection()

    cursor = conn.execute(
        """
        SELECT business_id
        FROM customer_numbers
        WHERE user_id = ?
        """,
        (user_id,)
    )

    row = cursor.fetchone()

    conn.close()

    if not row:
        return None

    return row[0]

def save_customer_number(
    user_id: str,
    whatsapp_number: str,
    business_id: str = None
):

    conn = get_crm_connection()

    conn.execute(
        """
        INSERT OR REPLACE INTO customer_numbers
        (
            user_id,
            whatsapp_number,
            business_id
        )
        VALUES (?, ?, ?)
        """,
        (
            user_id,
            whatsapp_number,
            business_id
        )
    )

    conn.commit()
    conn.close()

def get_customer_by_number(
    whatsapp_number: str
):

    conn = get_crm_connection()
    cursor = conn.execute(
        """
        SELECT user_id
        FROM customer_numbers
        WHERE whatsapp_number = ?
        """,
        (whatsapp_number,)
    )

    row = cursor.fetchone()

    conn.close()

    return row[0] if row else None


def get_business_phone_by_user(
    user_id: str
):

    conn = get_crm_connection()
    cursor = conn.execute(
        """
        SELECT whatsapp_number
        FROM customer_numbers
        WHERE user_id = ?
        """,
        (user_id,)
    )

    row = cursor.fetchone()

    conn.close()

    return row[0] if row else None


# --------------------------------------------------
# CUSTOMER -> BUSINESS ROUTING
# --------------------------------------------------

def save_mapping(
    customer_phone: str,
    business_phone: str,
    customer_name: str = None
):

    conn = get_crm_connection()

    # Upsert rather than INSERT OR REPLACE: the latter replaces the whole
    # row, which would wipe out an already-known customer_name (captured
    # from a previous message's WhatsApp ProfileName, or entered manually)
    # on every subsequent incoming message. Keep whichever name is already
    # on file; only fill it in from `customer_name` when nothing is set
    # yet, so manual edits and previously-captured names both stick.
    conn.execute(
        """
        INSERT INTO customer_mapping
            (customer_phone, business_phone, customer_name)
        VALUES (?, ?, ?)
        ON CONFLICT(customer_phone) DO UPDATE SET
            business_phone = excluded.business_phone,
            customer_name = COALESCE(
                customer_mapping.customer_name,
                excluded.customer_name
            )
        """,
        (
            customer_phone,
            business_phone,
            customer_name
        )
    )

    conn.commit()
    conn.close()


def set_customer_name(
    customer_phone: str,
    customer_name: str
):
    """
    Explicit manual override (e.g. from the Customer Profile panel).
    Unlike the auto-capture in save_mapping(), this always overwrites -
    it's a deliberate user action, not a best-effort default.
    """

    conn = get_crm_connection()

    conn.execute(
        """
        UPDATE customer_mapping
        SET customer_name = ?
        WHERE customer_phone = ?
        """,
        (
            customer_name,
            customer_phone
        )
    )

    conn.commit()
    conn.close()


def get_customer_name(
    customer_phone: str
):

    conn = get_crm_connection()

    cursor = conn.execute(
        """
        SELECT customer_name
        FROM customer_mapping
        WHERE customer_phone = ?
        """,
        (customer_phone,)
    )

    row = cursor.fetchone()

    conn.close()

    return row[0] if row else None


def get_business_phone_by_customer(
    customer_phone: str
):

    conn = get_crm_connection()
    cursor = conn.execute(
        """
        SELECT business_phone
        FROM customer_mapping
        WHERE customer_phone = ?
        """,
        (customer_phone,)
    )

    row = cursor.fetchone()

    conn.close()

    return row[0] if row else None


def delete_mapping(
    customer_phone: str
):

    conn = get_crm_connection()
    conn.execute(
        """
        DELETE FROM customer_mapping
        WHERE customer_phone = ?
        """,
        (customer_phone,)
    )

    conn.commit()
    conn.close()

def init_business_settings():

    conn = get_crm_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS business_settings (

            user_id TEXT PRIMARY KEY,

            business_name TEXT,

            welcome_message TEXT,

            ai_instructions TEXT,

            phone TEXT,

            email TEXT,

            website TEXT
        )
    """)

    conn.commit()
    conn.close()

def save_business_settings(
    user_id,
    business_name,
    welcome_message,
    ai_instructions,
    phone=None,
    email=None,
    website=None
):

    conn = get_crm_connection()

    conn.execute(
        """
        INSERT OR REPLACE INTO business_settings
        (
            user_id,
            business_name,
            welcome_message,
            ai_instructions,
            phone,
            email,
            website
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            business_name,
            welcome_message,
            ai_instructions,
            phone,
            email,
            website
        )
    )

    conn.commit()
    conn.close()

def get_business_settings(
    user_id
):

    conn = get_crm_connection()

    cursor = conn.execute(
        """
        SELECT
            business_name,
            welcome_message,
            ai_instructions,
            phone,
            email,
            website
        FROM business_settings
        WHERE user_id = ?
        """,
        (user_id,)
    )

    row = cursor.fetchone()

    conn.close()

    if not row:
        return None

    return {
        "business_name": row[0],
        "welcome_message": row[1],
        "ai_instructions": row[2],
        "phone": row[3],
        "email": row[4],
        "website": row[5]
    }

