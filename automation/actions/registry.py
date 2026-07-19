from automation.actions.create_reminder import execute as create_reminder
from automation.actions.add_activity import execute as add_activity


ACTION_REGISTRY = {

    "create_reminder": create_reminder,

    "add_activity": add_activity,

}