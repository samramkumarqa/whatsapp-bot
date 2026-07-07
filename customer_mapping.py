import sqlite3

DB_FILE = "data/app.db"


def init_customer_mapping():

    conn = sqlite3.connect(DB_FILE)

    # Business registration table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customer_numbers (
            user_id TEXT PRIMARY KEY,
            whatsapp_number TEXT NOT NULL
        )
    """)

    # Customer → Business mapping table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customer_mapping (
            customer_phone TEXT PRIMARY KEY,
            business_phone TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# --------------------------------------------------
# BUSINESS REGISTRATION
# user_id -> business whatsapp number
# --------------------------------------------------
def get_customers(user_id):

    import sqlite3

    conn = sqlite3.connect("data/app.db")

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

    conn.close()


def save_customer_number(
    user_id: str,
    whatsapp_number: str
):

    conn = sqlite3.connect(DB_FILE)

    conn.execute(
        """
        INSERT OR REPLACE INTO customer_numbers
        (user_id, whatsapp_number)
        VALUES (?, ?)
        """,
        (
            user_id,
            whatsapp_number
        )
    )

    conn.commit()
    conn.close()


def get_customer_by_number(
    whatsapp_number: str
):

    conn = sqlite3.connect(DB_FILE)

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


def get_number_by_customer(
    user_id: str
):

    conn = sqlite3.connect(DB_FILE)

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
    business_phone: str
):

    conn = sqlite3.connect(DB_FILE)

    conn.execute(
        """
        INSERT OR REPLACE INTO customer_mapping
        (customer_phone, business_phone)
        VALUES (?, ?)
        """,
        (
            customer_phone,
            business_phone
        )
    )

    conn.commit()
    conn.close()


def get_business_phone(
    customer_phone: str
):

    conn = sqlite3.connect(DB_FILE)

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

    conn = sqlite3.connect(DB_FILE)

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

    conn = sqlite3.connect(DB_FILE)

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

    conn = sqlite3.connect(DB_FILE)

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

    conn = sqlite3.connect(DB_FILE)

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

