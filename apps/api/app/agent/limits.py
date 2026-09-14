from typing import Any
import json
import os

class BudgetExhaustedError(Exception):
    pass

class CycleDetectedError(Exception):
    pass

class ExecutionBudget:
    def __init__(self, max_tool_calls: int | None = None, max_steps: int | None = None):
        # Allow override via environment or fallback to safe defaults
        self.max_tool_calls = max_tool_calls or int(os.getenv("AGENT_MAX_TOOL_CALLS", "5"))
        self.max_steps = max_steps or int(os.getenv("AGENT_MAX_STEPS", "10"))
        
        # Hard upper bound to prevent extreme configuration vulnerabilities
        self.max_tool_calls = min(self.max_tool_calls, 10)
        self.max_steps = min(self.max_steps, 20)

        self.current_tool_calls = 0
        self.current_steps = 0
        
        # History tracks (tool_name, normalized_args) for cycle detection
        self.call_history: list[tuple[str, str]] = []

    def increment_step(self):
        self.current_steps += 1
        if self.current_steps > self.max_steps:
            raise BudgetExhaustedError(f"Maximum orchestration steps ({self.max_steps}) exceeded.")

    def record_tool_call(self, tool_name: str, args: dict[str, Any]):
        self.current_tool_calls += 1
        if self.current_tool_calls > self.max_tool_calls:
            raise BudgetExhaustedError(f"Maximum tool calls ({self.max_tool_calls}) exceeded.")
            
        normalized_args = json.dumps(args, sort_keys=True)
        call_signature = (tool_name, normalized_args)
        
        # Cycle detection: check if the exact same tool + args was called in the previous step
        # M8 specifies checking if the exact same call was made back-to-back.
        # We can just look at the last call in the history.
        if self.call_history and self.call_history[-1] == call_signature:
            raise CycleDetectedError(f"Duplicate consecutive tool call detected: {tool_name}")
            
        self.call_history.append(call_signature)
