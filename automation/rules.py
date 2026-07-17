from automation.models import (
    AutomationRule,
    Condition,
    Action
)

RULES = [

    #
    # High Value Lead
    #
    AutomationRule(

        id="rule_high_lead",

        name="High Value Lead",

        description="Create follow-up for high scoring leads.",

        conditions=[

            Condition(
                field="lead_score",
                operator=">",
                value=80
            )

        ],

        actions=[

            Action(
                name="create_followup",
                params={
                    "days": 1,
                    "title": "High Priority Lead",
                    "note": "Lead score exceeded 80."
                }
            ),

            Action(
                name="log_activity",
                params={
                    "category": "Automation",
                    "title": "High Lead Score",
                    "details": "Automation Engine created follow-up."
                }
            )

        ]

    ),

    #
    # Purchase Ready
    #
    AutomationRule(

        id="rule_purchase_ready",

        name="Purchase Ready",

        description="Automatically create opportunity.",

        conditions=[

            Condition(
                field="intent",
                operator="==",
                value="Purchase Ready"
            )

        ],

        actions=[

            Action(
                name="create_opportunity",
                params={
                    "type": "Purchase Ready",
                    "confidence": 95,
                    "reason": "Customer is ready to purchase."
                }
            )

        ]

    ),

    #
    # Negative Sentiment
    #
    AutomationRule(

        id="rule_negative_sentiment",

        name="Negative Sentiment",

        description="Escalate unhappy customers.",

        conditions=[

            Condition(
                field="sentiment",
                operator="==",
                value="Negative"
            )

        ],

        actions=[

            Action(
                name="create_followup",
                params={
                    "days": 0,
                    "title": "Urgent Customer Follow-up",
                    "note": "Customer sentiment is negative."
                }
            ),

            Action(
                name="log_activity",
                params={
                    "category": "Automation",
                    "title": "Negative Sentiment",
                    "details": "Customer requires immediate attention."
                }
            )

        ]

    )

]