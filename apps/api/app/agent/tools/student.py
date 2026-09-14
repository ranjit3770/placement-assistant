from pydantic import BaseModel, ConfigDict
from typing import Any

from app.agent.context import ToolContext
from app.agent.registry import agent_tool, ToolEffect

class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

@agent_tool(
    name="get_student_profile",
    description="Retrieves the verified profile for the currently authenticated student.",
    input_schema=EmptyInput,
    effect=ToolEffect.READ_ONLY
)
def get_student_profile(args: EmptyInput, context: ToolContext) -> dict[str, Any]:
    # In a real implementation, this would call the student service
    # e.g., student_service.get_profile(student_id=context.principal.sub)
    return {
        "student_id": str(context.principal.sub),
        "status": "VERIFIED_PROFILE_STUB"
    }

@agent_tool(
    name="get_student_academics",
    description="Retrieves the verified academic records (e.g., CGPA, backlogs) for the authenticated student.",
    input_schema=EmptyInput,
    effect=ToolEffect.READ_ONLY
)
def get_student_academics(args: EmptyInput, context: ToolContext) -> dict[str, Any]:
    return {
        "student_id": str(context.principal.sub),
        "academics": "VERIFIED_ACADEMICS_STUB"
    }

@agent_tool(
    name="get_student_placement_history",
    description="Retrieves the placement history (offers, previous placements) for the authenticated student.",
    input_schema=EmptyInput,
    effect=ToolEffect.READ_ONLY
)
def get_student_placement_history(args: EmptyInput, context: ToolContext) -> dict[str, Any]:
    return {
        "student_id": str(context.principal.sub),
        "history": "VERIFIED_HISTORY_STUB"
    }
