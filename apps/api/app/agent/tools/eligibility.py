from pydantic import BaseModel
from typing import Any
from uuid import UUID

from app.agent.context import ToolContext
from app.agent.registry import agent_tool, ToolEffect

class EvaluateEligibilityInput(BaseModel):
    opportunity_id: str

@agent_tool(
    name="evaluate_eligibility",
    description="Invokes the M5 deterministic eligibility engine for the authenticated student against a specific opportunity.",
    input_schema=EvaluateEligibilityInput,
    effect=ToolEffect.EVALUATION
)
def evaluate_eligibility(args: EvaluateEligibilityInput, context: ToolContext) -> dict[str, Any]:
    # Conceptually:
    # engine = EligibilityService(...)
    # result = engine.evaluate(student_id=context.principal.sub, opportunity_id=args.opportunity_id)
    return {
        "opportunity_id": args.opportunity_id,
        "decision": "ELIGIBLE_STUB",
        "reasons": ["REASON_STUB"],
        "evaluation_key": "EVAL_KEY_STUB"
    }
