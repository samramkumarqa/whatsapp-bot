from automation.actions.registry import ACTION_REGISTRY

def execute_actions(rule, matched_customers):
    """
    Execute all actions configured for one rule.

    Supports both:
    1. New format (list of actions)
    2. Old format (single action)
    """

    actions = rule["action_json"]

    #
    # Backward compatibility
    #
    if isinstance(actions, dict):
        actions = [actions]

    for action in actions:

        #
        # New format
        #
        action_name = action.get("name")

        if not action_name:
            #
            # Legacy format
            #
            action_name = action.get("type")

        print(f"\nExecuting action : {action_name}")

        executor = ACTION_REGISTRY.get(action_name)

        if executor is None:

            print(f"Unknown action : {action_name}")

            continue

        for customer in matched_customers:

            try:

                # rule is passed through so action handlers can snapshot
                # which rule (id + current name) produced whatever they
                # write - e.g. create_reminder uses it to record
                # source_rule_id/source_rule_name for traceability and
                # later stale-reminder detection.
                executor(
                    customer,
                    action.get("params", action),
                    rule
                )

            except Exception as ex:

                print(
                    f"Action failed for "
                    f"{customer['phone']} : {ex}"
                )