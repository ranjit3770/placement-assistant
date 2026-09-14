"""
M8 budget enforcement tests (M8-01, M8-08, M8-10).

Pure unit tests — use a synthetic no-op registry so they test only the
budget/cycle machinery, independent of real tool handlers or database.
"""
import json
import os
from collections import defaultdict
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel

from app.agent.limits import BudgetExhaustedError, CycleDetectedError
from app.agent.orchestrator import AgentOrchestrator
from app.agent.registry import RegisteredTool, ToolEffect


# ---------------------------------------------------------------------------
# Simple no-op tool
# ---------------------------------------------------------------------------

class NoOpInput(BaseModel):
    x: int = 0


def _no_op_handler(args: NoOpInput, context: Any) -> dict:
    return {"ok": True}


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_tool_call(name: str, args: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=f"call_{uuid4().hex[:8]}",
        type="function",
        function=SimpleNamespace(name=name, arguments=json.dumps(args or {})),
    )


def _make_response(content: str | None = None, tool_calls: list | None = None) -> SimpleNamespace:
    msg = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


def _make_openai(responses: list) -> AsyncMock:
    client = AsyncMock()
    client.chat.completions.create.side_effect = responses
    return client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def accumulating_memory():
    """Memory mock whose add_message/get_messages are properly coupled."""
    store: dict[str, list] = defaultdict(list)

    async def _get(conv_id, **_kw):
        return list(store[str(conv_id)])

    async def _add(conv_id, role, content="", **_kw):
        store[str(conv_id)].append({"role": role, "content": content})

    mem = AsyncMock()
    mem.get_messages.side_effect = _get
    mem.add_message.side_effect = _add
    mem.context = MagicMock()
    mem.context.principal = MagicMock()
    return mem


def _make_orchestrator_with_noop(memory: AsyncMock, responses: list):
    """Orchestrator whose registry contains only a synthetic no-op tool."""
    client = _make_openai(responses)
    orch = AgentOrchestrator(memory=memory, openai_client=client)
    orch.registry = {
        "noop": RegisteredTool(
            name="noop",
            description="No-op for budget testing",
            input_schema=NoOpInput,
            handler=_no_op_handler,
            effect=ToolEffect.READ_ONLY,
        )
    }
    return orch, client


# ---------------------------------------------------------------------------
# M8-01 — Step limit terminates the loop
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_m8_01_loop_termination_step_budget(accumulating_memory):
    """MAX_STEPS=2 → orchestrator must stop after 2 LLM completions."""
    with patch.dict(os.environ, {"AGENT_MAX_STEPS": "2", "AGENT_MAX_TOOL_CALLS": "10"}):
        responses = [
            _make_response(tool_calls=[_make_tool_call("noop", {"x": 0})]),
            _make_response(tool_calls=[_make_tool_call("noop", {"x": 1})]),  # different args — no cycle
            _make_response(content="Should not reach here"),
        ]
        orch, client = _make_orchestrator_with_noop(accumulating_memory, responses)

        with pytest.raises(BudgetExhaustedError) as exc:
            await orch.execute(uuid4(), "query")

        assert "Maximum orchestration steps (2) exceeded" in str(exc.value)
        # Exactly 2 LLM calls before step limit fired
        assert client.chat.completions.create.call_count == 2


# ---------------------------------------------------------------------------
# M8-08 — Each parallel tool call consumes one budget unit individually
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_m8_08_parallel_tools_budget(accumulating_memory):
    """3 parallel calls when MAX_TOOL_CALLS=2 — 3rd must be budget-rejected."""
    with patch.dict(os.environ, {"AGENT_MAX_TOOL_CALLS": "2", "AGENT_MAX_STEPS": "10"}):
        call1 = _make_tool_call("noop", {"x": 0})
        call2 = _make_tool_call("noop", {"x": 1})
        call3 = _make_tool_call("noop", {"x": 2})
        resp1 = _make_response(tool_calls=[call1, call2, call3])
        resp2 = _make_response(content="Controlled final")
        orch, client = _make_orchestrator_with_noop(accumulating_memory, [resp1, resp2])

        conv_id = uuid4()
        result = await orch.execute(conv_id, "query")

        # Authority message overrides LLM text (no authoritative decision was produced)
        assert result.decision == "UNKNOWN"
        # Second LLM call received the budget error and gave a text response
        assert client.chat.completions.create.call_count == 2

        history = await accumulating_memory.get_messages(conv_id)
        budget_errors = [
            m for m in history
            if m.get("role") == "tool" and "Maximum tool calls" in m.get("content", "")
        ]
        assert len(budget_errors) == 1, (
            f"Expected 1 budget error in history, got {len(budget_errors)}. "
            f"History: {[m['content'][:60] for m in history if m.get('role') == 'tool']}"
        )


# ---------------------------------------------------------------------------
# M8-10 — Cycle detection terminates on duplicate consecutive call
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_m8_10_repeated_cycle(accumulating_memory):
    """Identical consecutive tool call triggers CycleDetectedError (caught → error in history)."""
    with patch.dict(os.environ, {"AGENT_MAX_TOOL_CALLS": "10", "AGENT_MAX_STEPS": "10"}):
        # Same args both times → cycle
        call = _make_tool_call("noop", {"x": 0})
        resp1 = _make_response(tool_calls=[call])
        resp2 = _make_response(tool_calls=[call])
        resp3 = _make_response(content="Should not reach here")
        orch, client = _make_orchestrator_with_noop(accumulating_memory, [resp1, resp2, resp3])

        conv_id = uuid4()
        result = await orch.execute(conv_id, "query")

        assert result.decision == "UNKNOWN"
        # 3 LLM calls: resp1 (noop ok), resp2 (cycle error injected), resp3 (text)
        assert client.chat.completions.create.call_count == 3

        history = await accumulating_memory.get_messages(conv_id)
        cycle_errors = [
            m for m in history
            if m.get("role") == "tool" and "Duplicate consecutive tool call" in m.get("content", "")
        ]
        assert len(cycle_errors) == 1, (
            f"Expected 1 cycle error in history, got {len(cycle_errors)}. "
            f"History: {[m['content'][:60] for m in history if m.get('role') == 'tool']}"
        )
