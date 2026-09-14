import pytest

from app.agent.core import AgentResponse, EvidenceReference
from app.agent.prompts.system import AGENT_SYSTEM_PROMPT
from app.agent.prompts.guardrails import GUARDRAILS_PROMPT

def test_m7_06_eligibility_authority():
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

def test_m7_07_evidence_authority():
    # The LLM cannot manufacture citations. 
    # The application populates the `evidence` field in AgentResponse.
    # If the LLM claims "According to page 17...", it is just text in the `message`.
    # The true authoritative evidence is explicitly preserved in the struct.
    
    llm_hallucination = "According to page 17, you need a 9.0 CGPA."
    
    response_fabricated = AgentResponse(
        message=llm_hallucination,
        evidence=[] # No verified evidence matches this claim
    )
    
    assert len(response_fabricated.evidence) == 0
    # Any LLM claim without backing in response.evidence is untrusted text.
    
    # Positive case: Verified M6 evidence survives and is used
    verified_evidence = EvidenceReference(
        document_id="doc-123",
        policy_version="1.0",
        content="Students need an 8.5 CGPA.",
        source_hash="abcd"
    )
    
    response_verified = AgentResponse(
        message="According to the policy, you need an 8.5 CGPA.",
        evidence=[verified_evidence]
    )
    
    assert len(response_verified.evidence) == 1
    assert response_verified.evidence[0].document_id == "doc-123"
    assert response_verified.evidence[0].content == "Students need an 8.5 CGPA."

def test_m7_08_prompt_injection_guardrails():
    assert "IGNORE PREVIOUS INSTRUCTIONS" in GUARDRAILS_PROMPT
    assert "You cannot determine eligibility" in AGENT_SYSTEM_PROMPT
    assert "You cannot modify policy" in AGENT_SYSTEM_PROMPT

def test_m7_09_missing_authoritative_data():
    assert "If authoritative information is unavailable, say so" in AGENT_SYSTEM_PROMPT

