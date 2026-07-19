import logging

from automation.models import (
    AutomationRule,
    Condition,
    Action,
)

# NEW registry
from automation.actions.registry import ACTION_REGISTRY

from automation.manager import get_rules
from crm.activity_manager import add_activity

logger = logging.getLogger(__name__)


class AutomationEngine:

    def __init__(self):
        pass

    def evaluate_condition(
        self,
        analysis,
        condition
    ):
        """
        Evaluate a single condition.
        """

        current_value = analysis.get(condition.field)

        operator = condition.operator
        expected = condition.value

        try:

            if operator == "==":
                return current_value == expected

            if operator == "!=":
                return current_value != expected

            if operator == ">":
                return current_value > expected

            if operator == "<":
                return current_value < expected

            if operator == ">=":
                return current_value >= expected

            if operator == "<=":
                return current_value <= expected

            if operator == "contains":

                if current_value is None:
                    return False

                return (
                    str(expected).lower()
                    in str(current_value).lower()
                )

            logger.warning(
                f"Unknown operator: {operator}"
            )

            return False

        except Exception:

            logger.exception(
                f"Condition evaluation failed: {condition.field}"
            )

            return False

    async def execute_rule(
        self,
        customer_phone,
        rule
    ):

        logger.info(
            f"Executing rule: {rule.name}"
        )

        add_activity(
            customer_phone,
            "Automation",
            rule.name,
            f"Automation rule executed: {rule.name}"
        )

        for action in rule.actions:

            action_fn = ACTION_REGISTRY.get(
                action.name
            )

            if action_fn is None:

                logger.warning(
                    f"Unknown action: {action.name}"
                )

                continue

            logger.info(
                f"Executing action plugin: {action.name}"
            )

            await action_fn(
                customer_phone,
                action.params
            )

    async def run(
        self,
        customer_phone,
        analysis
    ):

        logger.info(
            "Automation Engine started."
        )

        rules_data = get_rules(
            enabled_only=True
        )

        for rule_data in rules_data:

            #
            # Build Conditions
            #

            conditions = []

            for c in rule_data["conditions"]:

                conditions.append(

                    Condition(

                        field=c["field"],

                        operator=c["operator"],

                        value=c["value"]

                    )
                )

            #
            # Build Actions
            #

            actions = []

            for a in rule_data["actions"]:

                actions.append(

                    Action(

                        name=a["name"],

                        params=a.get(
                            "params",
                            {}
                        )

                    )
                )

            #
            # Build Rule
            #

            rule = AutomationRule(

                id=rule_data["id"],

                name=rule_data["name"],

                description=rule_data.get(
                    "description",
                    ""
                ),

                conditions=conditions,

                actions=actions,

                enabled=rule_data["enabled"],

                stop_after_match=rule_data.get(
                    "stop_after_match",
                    True
                )

            )

            #
            # Evaluate Conditions
            #

            matched = True

            for condition in rule.conditions:

                if not self.evaluate_condition(
                    analysis,
                    condition
                ):
                    matched = False
                    break

            if not matched:
                continue

            logger.info(
                f"Rule matched: {rule.name}"
            )

            await self.execute_rule(
                customer_phone,
                rule
            )

            if rule.stop_after_match:
                break


automation_engine = AutomationEngine()