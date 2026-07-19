from datetime import datetime
import traceback

from automation.database import get_all_rules
from automation.evaluator import evaluate_rule
from automation.executor import execute_actions


def run_automation():

    print("\n" + "=" * 60)
    print(f"Automation Runner Started : {datetime.now()}")
    print("=" * 60)

    try:

        rules = get_all_rules()

        print(f"Rules found : {len(rules)}")

        if not rules:
            print("No automation rules found.")
            return

        for rule in rules:

            print("\n--------------------------------------")
            print(f"Evaluating Rule : {rule['name']}")
            print("--------------------------------------")

            matched = evaluate_rule(
                rule,
                "+14155238886"      # Temporary (we'll remove this later)
            )

            print(f"Matched Customers : {len(matched)}")

            if matched:

                execute_actions(rule, matched)

                print("\nMatched Customer Details:")

                for customer in matched:

                    print(
                        f"  {customer['phone']} "
                        f"(Lead Score: {customer['lead_score']})"
                    )

            else:

                print("No matching customers.")

    except Exception:

        print("\nERROR INSIDE AUTOMATION RUNNER")
        traceback.print_exc()

    print("\nAutomation Runner Finished")
    print("=" * 60)