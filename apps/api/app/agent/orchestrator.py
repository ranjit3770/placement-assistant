import json
import logging
import inspect
from typing import Any
from uuid import UUID
from openai import AsyncOpenAI
from pydantic import ValidationError

from app.agent.context import ToolContext
from app.agent.registry import get_tool_registry, RegisteredTool, ToolEffect
from app.agent.limits import ExecutionBudget, BudgetExhaustedError, CycleDetectedError
from app.agent.memory import ConversationMemory
from app.agent.core import AgentResponse, EvidenceReference
from app.agent.prompts.system import AGENT_SYSTEM_PROMPT
from app.agent.prompts.guardrails import GUARDRAILS_PROMPT
from app.agent.m8_authority import M8EligibilityInput, M8AgentResponse, evaluate_m5, authority_message
from app.api.schemas.eligibility import EligibilityDecisionResponse

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    def __init__(self, memory: ConversationMemory, openai_client: AsyncOpenAI, model: str = "gpt-4o-mini"):
        self.memory = memory
        self.client = openai_client
        self.model = model
        # Never mutate the frozen M7 registry or execute its conceptual M5 stub.
        self.registry = dict(get_tool_registry())
        self.registry["evaluate_eligibility"] = RegisteredTool(
            name="evaluate_eligibility", description="Evaluate the authenticated student using M5.",
            input_schema=M8EligibilityInput, handler=evaluate_m5, effect=ToolEffect.EVALUATION,
        )

    def _get_openai_tools(self) -> list[dict[str, Any]]:
        tools = []
        for name, tool in self.registry.items():
            schema = tool.input_schema.model_json_schema()
            # Remove pydantic specific fields that might confuse OpenAI if any
            if "$defs" in schema:
                del schema["$defs"]
            tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": schema
                }
            })
        return tools

    async def execute(self, conversation_id: UUID, query: str) -> AgentResponse:
        budget = ExecutionBudget()
        
        # Load messages
        messages = await self.memory.get_messages(conversation_id)
        if not messages:
            # First turn, add system prompt
            await self.memory.add_message(conversation_id, role="system", content=AGENT_SYSTEM_PROMPT + "\n" + GUARDRAILS_PROMPT)
            messages.append({"role": "system", "content": AGENT_SYSTEM_PROMPT + "\n" + GUARDRAILS_PROMPT})
            
        await self.memory.add_message(conversation_id, role="user", content=query)
        messages.append({"role": "user", "content": query})
        
        openai_tools = self._get_openai_tools()
        
        authoritative_decision = None
        verified_evidence: list[EvidenceReference] = []

        while True:
            budget.increment_step()
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=openai_tools,
                tool_choice="auto" if openai_tools else "none"
            )
            
            response_message = response.choices[0].message
            
            if not response_message.tool_calls:
                # No more tools, we have our final text explanation
                # Conservative fallback until grounded explanation validation exists.
                # Never persist or return unchecked model claims as eligibility advice.
                final_content = authority_message(authoritative_decision)
                await self.memory.add_message(conversation_id, role="assistant", content=final_content)
                
                # Construct safe final response overriding LLM textual claims with reality
                return M8AgentResponse(
                    message=final_content,
                    decision=authoritative_decision.result if authoritative_decision else "UNKNOWN",
                    decision_source="M5_ENGINE" if authoritative_decision else None,
                    evidence=[],  # No stub evidence before the real M6 bridge is wired.
                    authoritative_decision=authoritative_decision,
                )
            
            # The model called tools
            # We must record the assistant's tool calls in memory
            # The OpenAI SDK requires tool calls to be serialized back correctly
            tool_calls_data = []
            for tc in response_message.tool_calls:
                tool_calls_data.append({
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                })
            
            await self.memory.add_message(
                conversation_id, 
                role="assistant", 
                metadata={"tool_calls": tool_calls_data}
            )
            
            # OpenAI requires the assistant message with tool calls to be appended before the tool results
            messages.append({
                "role": "assistant",
                "tool_calls": tool_calls_data
            })
            
            for tool_call in response_message.tool_calls:
                tool_name = tool_call.function.name
                if tool_name == "evaluate_eligibility":
                    # Includes malformed arguments and budget-rejected attempts.
                    authoritative_decision = None
                
                # 1. Reject unknown tools
                if tool_name not in self.registry:
                    error_msg = f"Error: Tool '{tool_name}' not found."
                    await self.memory.add_message(conversation_id, role="tool", content=error_msg, tool_call_id=tool_call.id, tool_name=tool_name)
                    messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": tool_name, "content": error_msg})
                    continue
                
                tool = self.registry[tool_name]
                
                # 2. Parse arguments
                try:
                    args_dict = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    error_msg = "Error: Invalid JSON arguments."
                    await self.memory.add_message(conversation_id, role="tool", content=error_msg, tool_call_id=tool_call.id, tool_name=tool_name)
                    messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": tool_name, "content": error_msg})
                    continue
                
                # 3. Budget & Cycle Check
                try:
                    budget.record_tool_call(tool_name, args_dict)
                except (BudgetExhaustedError, CycleDetectedError) as e:
                    # Abort the tool and force termination
                    error_msg = f"System Error: {str(e)} Please formulate a final response."
                    await self.memory.add_message(conversation_id, role="tool", content=error_msg, tool_call_id=tool_call.id, tool_name=tool_name)
                    messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": tool_name, "content": error_msg})
                    continue

                # 4. Pydantic validation & Execution
                try:
                    if tool_name == "evaluate_eligibility":
                        # A failed second evaluation must not reuse an earlier result.
                        authoritative_decision = None
                    parsed_args = tool.input_schema(**args_dict)
                    result = tool.handler(parsed_args, self.memory.context)
                    if inspect.isawaitable(result):
                        result = await result
                    
                    # Intercept authoritative data
                    if tool_name == "evaluate_eligibility" and isinstance(result, dict):
                        # Assuming the tool returns a dict with 'decision'
                        authoritative_decision = EligibilityDecisionResponse.model_validate(result)
                        if authoritative_decision.result not in {"ELIGIBLE", "NOT_ELIGIBLE", "UNKNOWN"}:
                            authoritative_decision = None
                            raise ValueError("Invalid authoritative result")
                    elif tool_name == "get_policy_evidence" and isinstance(result, dict):
                        verified_evidence.append(EvidenceReference(
                            document_id=result.get("document_id", ""),
                            policy_version=result.get("policy_version", "1.0"),
                            content=result.get("content", ""),
                            source_hash=result.get("source_hash")
                        ))
                    elif tool_name == "search_policy" and isinstance(result, dict):
                        # Search policy may also return verified evidence snippets
                        evidence_list = result.get("evidence", [])
                        for ev in evidence_list:
                            if isinstance(ev, dict):
                                verified_evidence.append(EvidenceReference(
                                    document_id=ev.get("document_id", ""),
                                    policy_version=ev.get("policy_version", "1.0"),
                                    content=ev.get("content", ""),
                                    source_hash=ev.get("source_hash")
                                ))
                    
                    result_str = json.dumps(result)
                except ValidationError as e:
                    result_str = f"Error: Validation failed. {e}"
                except PermissionError as e:
                    result_str = f"Error: Authorization denied. {e}"
                except Exception as e:
                    logger.exception(f"Tool execution failed: {e}")
                    result_str = f"Error: Internal tool execution failed."

                await self.memory.add_message(conversation_id, role="tool", content=result_str, tool_call_id=tool_call.id, tool_name=tool_name)
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": tool_name, "content": result_str})
