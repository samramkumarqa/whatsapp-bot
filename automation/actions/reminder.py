from reminder_manager import upsert_reminder


def execute(customer, action):

    upsert_reminder(
        customer["phone"],
        action.get("message", "Follow up"),
        action.get("days", 1)
    )

    print(f"✓ Reminder created for {customer['phone']}")