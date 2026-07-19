from reminder_manager import upsert_reminder


def execute(customer, params):
    """
    Create a reminder for a matched customer.
    """

    customer_phone = customer["phone"]

    reminder_text = params.get(
        "text",
        "Follow up customer"
    )

    days = int(
        params.get(
            "days",
            1
        )
    )

    upsert_reminder(
        customer_phone,
        reminder_text,
        days
    )

    print(f"✓ Reminder created for {customer_phone}")