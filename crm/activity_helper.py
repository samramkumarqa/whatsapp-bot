from crm.activity_manager import add_activity


def log_ai_activity(
    customer_phone,
    title,
    details
):
    add_activity(
        customer_phone,
        "AI",
        title,
        details
    )


def log_tag_activity(
    customer_phone,
    details
):
    add_activity(
        customer_phone,
        "Tags",
        "Customer Tags Updated",
        details
    )


def log_system_activity(
    customer_phone,
    title,
    details
):
    add_activity(
        customer_phone,
        "System",
        title,
        details
    )