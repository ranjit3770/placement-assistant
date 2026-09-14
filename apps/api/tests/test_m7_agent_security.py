import pytest
from pydantic import ValidationError
from uuid import uuid4

from app.agent.registry import get_tool_registry, ToolEffect
from app.agent.tools import student, policy, eligibility

def test_m7_01_tool_schema_no_auth_exposure():
    registry = get_tool_registry()
    for name, tool in registry.items():
        schema = tool.input_schema.model_json_schema()
        properties = schema.get("properties", {})
        assert "tenant_id" not in properties
        assert "student_id" not in properties

def test_m7_03_forged_identity_ignored():
    # Attempting to pass student_id into get_student_profile should raise ValidationError or be ignored depending on pydantic config.
    # We will use strict validation (or rely on the fact that student_id is strictly not in EmptyInput).
    registry = get_tool_registry()
    tool = registry["get_student_profile"]
    
    # EmptyInput has no fields, so passing extra fields will either be ignored or raise an error.
    # Let's ensure it doesn't accept and use it.
    try:
        instance = tool.input_schema(**{"student_id": "forged_id"})
        assert not hasattr(instance, "student_id")
    except ValidationError:
        pass # Also acceptable

def test_m7_05_tool_mutation_boundary():
    registry = get_tool_registry()
    for name, tool in registry.items():
        assert tool.effect in [ToolEffect.READ_ONLY, ToolEffect.EVALUATION]
        assert tool.effect.name != "MUTATION"
