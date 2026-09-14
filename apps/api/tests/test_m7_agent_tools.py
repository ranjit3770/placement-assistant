import pytest

from app.agent.core import AgentResponse, EvidenceReference
from app.agent.prompts.system import AGENT_SYSTEM_PROMPT
from app.agent.prompts.guardrails import GUARDRAILS_PROMPT

def test_m7_06_eligibility_authority():
    # Simulate LLM trying to say NOT_ELIGIBLE but M5 says ELIGIBLE.
    # The application builds AgentResponse using M5's decision.
    
    m5_decision = "ELIGIBLE"
    llm_message = "You are not eligible because I hallucinated a rule."
    
    response = AgentResponse(
        message=llm_message,
        decision=m5_decision,
        decision_source="M5_ENGINE",
        evidence=[]
    )
    
    assert response.decision == "ELIGIBLE"
    assert response.decision_source == "M5_ENGINE"
    # LLM cannot override the structured decision field

def test_m7_08_prompt_injection_guardrails():
    assert "IGNORE PREVIOUS INSTRUCTIONS" in GUARDRAILS_PROMPT
    assert "You cannot determine eligibility" in AGENT_SYSTEM_PROMPT
    assert "You cannot modify policy" in AGENT_SYSTEM_PROMPT

def test_m7_09_missing_authoritative_data():
    assert "If authoritative information is unavailable, say so" in AGENT_SYSTEM_PROMPT
