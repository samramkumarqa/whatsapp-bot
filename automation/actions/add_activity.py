from crm.activity_manager import add_activity


def execute(
    customer,
    params
):
    customer_phone = customer["phone"]

    source = params.get(
        "source",
        "Automation"
    )

    title = params.get(
        "title",
        "Automation Activity"
    )

    description = params.get(
        "description",
        ""
    )

    add_activity(
        customer_phone,
        source,
        title,
        description
    )

    print(
        f"✓ Activity added for {customer_phone}"
    )