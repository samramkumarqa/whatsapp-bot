from crm.lead_manager import update_lead, get_lead


def execute(customer, action):

    lead = get_lead(customer["phone"])

    update_lead(
        customer_phone=customer["phone"],
        status=action["status"],
        notes=lead.get("notes", ""),
        confidence=lead.get("confidence", 50),
        reason="Automation",
        updated_by="Automation"
    )

    print(f"✓ Lead updated for {customer['phone']}")