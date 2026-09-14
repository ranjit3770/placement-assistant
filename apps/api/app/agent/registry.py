from enum import Enum
from typing import Any, Callable, Dict, Type
from pydantic import BaseModel
import inspect

class ToolEffect(Enum):
    READ_ONLY = "READ_ONLY"
    EVALUATION = "EVALUATION"

class RegisteredTool(BaseModel):
    name: str
    description: str
    input_schema: Type[BaseModel]
    effect: ToolEffect
    handler: Callable

_TOOL_REGISTRY: Dict[str, RegisteredTool] = {}

def get_tool_registry() -> Dict[str, RegisteredTool]:
    return _TOOL_REGISTRY

def agent_tool(name: str, description: str, input_schema: Type[BaseModel], effect: ToolEffect = ToolEffect.READ_ONLY):
    def decorator(func: Callable):
        _TOOL_REGISTRY[name] = RegisteredTool(
            name=name,
            description=description,
            input_schema=input_schema,
            effect=effect,
            handler=func
        )
        return func
    return decorator

def generate_openai_tools() -> list[dict]:
    tools = []
    for tool_name, tool in _TOOL_REGISTRY.items():
        schema = tool.input_schema.model_json_schema()
        # Remove title to keep schema clean for OpenAI
        schema.pop("title", None)
        tools.append({
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool.description,
                "parameters": schema
            }
        })
    return tools
