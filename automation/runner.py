import logging

from automation.database import get_all_rules
from automation.evaluator import evaluate_rule
from automation.executor import execute_actions
from automation.rule_stats import record_rule_execution
from analytics.customer_stats import get_customer_stats
from crm.customer_mapping import get_active_businesses

logger = logging.getLogger(__name__)


def run_automation():
    """
    Runs every minute via APScheduler (see automation/service.py) - this
    used to log via print(), which meant every tick wrote straight to
    stdout with no level, timestamp, or logger name, unlike the rest of
    the app (e.g. automation/jobs.py) which goes through the standard
    `logging` module. Switched to logger.* so this output is consistent
    with everything else and can be filtered/redirected the same way.

    Multi-tenancy: this used to evaluate every rule (regardless of which
    business it belonged to) against one hardcoded business's customers.
    Now it loops over every active business (see
    crm.customer_mapping.get_active_businesses()) and, for each one,
    evaluates only that business's own rules against that business's own
    customers - so Business A's rules never fire against Business B's
    customers and vice versa.
    """

    logger.info("Automation Runner Started")

    try:

        businesses = get_active_businesses()

        logger.info("Active businesses found : %d", len(businesses))

        if not businesses:
            logger.info("No active businesses found.")
            return

        for business in businesses:

            business_id = business["business_id"]
            user_id = business["user_id"]

            rules = get_all_rules(business_id)

            logger.info(
                "Business %s: %d rule(s) found", business_id, len(rules)
            )

            if not rules:
                continue

            # Fetched once per business and reused across every one of
            # that business's rules below, instead of evaluate_rule()
            # re-running the same get_customer_stats(user_id) query (4+
            # queries on its own - see analytics/customer_stats.py) once
            # per rule. With up to MAX_AUTOMATION_RULES (5) rules per
            # business and now potentially many active businesses (see
            # get_active_businesses() above), that turned one redundant
            # fetch into 5x redundant work, every business, every tick.
            customers = get_customer_stats(user_id)

            for rule in rules:

                logger.debug("Evaluating Rule : %s", rule["name"])

                matched = evaluate_rule(rule, user_id, customers)

                logger.debug("Matched Customers : %d", len(matched))

                if matched:

                    execute_actions(rule, matched)

                    for customer in matched:

                        # Logged regardless of whether execute_actions()'s
                        # individual action handlers succeeded - "the rule
                        # fired for this customer" is about the condition
                        # match, not the action outcome. Feeds the Rule
                        # Performance table on the Analytics page (see
                        # automation/rule_stats.py).
                        record_rule_execution(
                            rule["id"],
                            rule["name"],
                            business_id,
                            customer["phone"]
                        )

                        logger.debug(
                            "  %s (Lead Score: %s)",
                            customer["phone"],
                            customer["lead_score"],
                        )

                else:

                    logger.debug(
                        "No matching customers for rule : %s", rule["name"]
                    )

    except Exception:

        logger.exception("Error inside automation runner")

    logger.info("Automation Runner Finished")