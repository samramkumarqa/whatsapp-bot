from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from automation.manager import (
    get_rules,
    get_rule,
    create_rule,
    update_rule,
    delete_rule,
    set_enabled,
)

router = APIRouter(tags=["Automation"])


# --------------------------------------------------------
# Request Models
# --------------------------------------------------------

from typing import List, Dict, Any

class AutomationRuleRequest(BaseModel):

    name: str

    description: str = ""

    enabled: bool = True

    trigger_type: str

    condition_json: List[Dict[str, Any]]

    action_json: List[Dict[str, Any]]


class EnableRuleRequest(BaseModel):

    enabled: bool


# --------------------------------------------------------
# List Rules
# --------------------------------------------------------

@router.get("/automation/rules")
async def list_rules():

    return {

        "status": "success",

        "rules": get_rules()

    }


# --------------------------------------------------------
# Get Single Rule
# --------------------------------------------------------

@router.get("/automation/rules/{rule_id}")
async def get_automation_rule(rule_id: int):

    rule = get_rule(rule_id)

    if rule is None:

        raise HTTPException(
            status_code=404,
            detail="Rule not found"
        )

    return {

        "status": "success",

        "rule": rule

    }


# --------------------------------------------------------
# Create Rule
# --------------------------------------------------------

@router.post("/automation/rules")
async def create_automation_rule(request: AutomationRuleRequest):

    rule_id = create_rule(request.model_dump())

    return {

        "status": "success",

        "id": rule_id

    }


# --------------------------------------------------------
# Update Rule
# --------------------------------------------------------

@router.put("/automation/rules/{rule_id}")
async def update_automation_rule(
    rule_id: int,
    request: AutomationRuleRequest
):

    if get_rule(rule_id) is None:

        raise HTTPException(
            status_code=404,
            detail="Rule not found"
        )

    update_rule(
        rule_id,
        request.model_dump()
    )

    return {

        "status": "success"

    }


# --------------------------------------------------------
# Enable / Disable Rule
# --------------------------------------------------------

@router.patch("/automation/rules/{rule_id}/enabled")
async def enable_disable_rule(
    rule_id: int,
    request: EnableRuleRequest
):

    if get_rule(rule_id) is None:

        raise HTTPException(
            status_code=404,
            detail="Rule not found"
        )

    set_enabled(
        rule_id,
        request.enabled
    )

    return {

        "status": "success"

    }


# --------------------------------------------------------
# Delete Rule
# --------------------------------------------------------

@router.delete("/automation/rules/{rule_id}")
async def delete_automation_rule(rule_id: int):

    if get_rule(rule_id) is None:

        raise HTTPException(
            status_code=404,
            detail="Rule not found"
        )

    delete_rule(rule_id)

    return {

        "status": "success"

    }

@router.put("/automation/rules/{rule_id}/enabled")
async def toggle_rule_enabled(
    rule_id: int,
    payload: dict
):

    set_enabled(
        rule_id,
        payload["enabled"]
    )

    return {
        "status": "success"
    }