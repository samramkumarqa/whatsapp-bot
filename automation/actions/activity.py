from crm.activity_manager import add_activity


def execute(customer, action):

    add_activity(
        customer["phone"],
        "Automation",
        action.get("title", "Automation Rule"),
        action.get("message", "")
    )

    print(f"✓ Activity created for {customer['phone']}")