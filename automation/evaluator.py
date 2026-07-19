from analytics.analytics import get_customer_stats


def evaluate_condition(customer, condition):
    """
    Evaluate one condition against one customer.
    """

    field = condition.get("field")
    operator = condition.get("operator", "=")
    target = condition.get("value")

    value = customer.get(field)

    if value is None:
        return False

    try:
        # Numeric comparisons
        if operator == ">=":
            return value >= target

        elif operator == ">":
            return value > target

        elif operator == "<=":
            return value <= target

        elif operator == "<":
            return value < target

        # Equality
        elif operator in ["=", "=="]:
            return str(value) == str(target)

        # Not equal
        elif operator == "!=":
            return str(value) != str(target)

        # Contains
        elif operator == "contains":
            return str(target).lower() in str(value).lower()

    except Exception:
        return False

    return False


def evaluate_rule(rule, user_id):
    """
    Evaluate one automation rule and return matching customers.
    """

    customers = get_customer_stats(user_id)

    matched = []

    print("--------------------------------------")
    print(f"Evaluating Rule : {rule['name']}")
    print(f"Customers Loaded : {len(customers)}")

    conditions = rule["condition_json"]

    #
    # ---------------------------------------
    # FORMAT 1
    #
    # [
    #   {...},
    #   {...}
    # ]
    #
    # Default = AND
    # ---------------------------------------
    #
    if isinstance(conditions, list):

        for customer in customers:

            results = [
                evaluate_condition(customer, c)
                for c in conditions
            ]

            if all(results):
                matched.append(customer)

    #
    # ---------------------------------------
    # FORMAT 2
    #
    # {
    #   "logic":"AND",
    #   "conditions":[...]
    # }
    # ---------------------------------------
    #
    elif isinstance(conditions, dict) and "conditions" in conditions:

        logic = conditions.get("logic", "AND").upper()

        for customer in customers:

            results = [
                evaluate_condition(customer, c)
                for c in conditions["conditions"]
            ]

            if logic == "AND":

                if all(results):
                    matched.append(customer)

            elif logic == "OR":

                if any(results):
                    matched.append(customer)

    #
    # ---------------------------------------
    # FORMAT 3 (Legacy)
    #
    # {
    #   "operator":">=",
    #   "value":50
    # }
    # ---------------------------------------
    #
    elif isinstance(conditions, dict):

        operator = conditions.get("operator", ">=")
        target = conditions.get("value", 0)

        for customer in customers:

            if evaluate_condition(
                customer,
                {
                    "field": "lead_score",
                    "operator": operator,
                    "value": target,
                },
            ):
                matched.append(customer)

    print(f"Matched : {len(matched)}")

    return matched