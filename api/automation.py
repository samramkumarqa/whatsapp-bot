from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

from automation.database import (
    get_all_rules,
    create_rule,
    update_rule,
    delete_rule,
)

router = APIRouter(tags=["Automation"])


class AutomationRuleRequest(BaseModel):

    name: str

    description: str = ""

    enabled: bool = True

    trigger_type: str

    condition_json: Dict[str, Any]

    action_json: Dict[str, Any]


@router.get("/automation/rules")
async def list_rules():

    return {
        "status": "success",
        "rules": get_all_rules()
    }


@router.post("/automation/rules")
async def create_automation_rule(
    request: AutomationRuleRequest
):

    rule_id = create_rule(request.dict())

    return {
        "status": "success",
        "id": rule_id
    }


@router.put("/automation/rules/{rule_id}")
async def update_automation_rule(
    rule_id: int,
    request: AutomationRuleRequest
):

    update_rule(
        rule_id,
        request.dict()
    )

    return {
        "status": "success"
    }


@router.delete("/automation/rules/{rule_id}")
async def delete_automation_rule(
    rule_id: int
):

    delete_rule(rule_id)

    return {
        "status": "success"
    }