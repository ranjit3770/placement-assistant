import pytest
from app.core.engine.evaluator import evaluate_rule, aggregate_results, evaluate_snapshot

def test_evaluate_rule_pass():
    snapshot = {"academic": {"cgpa": 8.0}}
    rule = {"field": "academic.cgpa", "operator": ">=", "value": 7.5}
    result = evaluate_rule(rule, snapshot)
    assert result["result"] == "PASS"

def test_evaluate_rule_fail():
    snapshot = {"academic": {"cgpa": 6.5}}
    rule = {"field": "academic.cgpa", "operator": ">=", "value": 7.5}
    result = evaluate_rule(rule, snapshot)
    assert result["result"] == "FAIL"

def test_evaluate_rule_unknown():
    snapshot = {"academic": {}}  # cgpa missing
    rule = {"field": "academic.cgpa", "operator": ">=", "value": 7.5}
    result = evaluate_rule(rule, snapshot)
    assert result["result"] == "UNKNOWN"

def test_aggregate_results():
    assert aggregate_results([{"result": "PASS"}, {"result": "PASS"}]) == "PASS"
    assert aggregate_results([{"result": "PASS"}, {"result": "FAIL"}]) == "FAIL"
    assert aggregate_results([{"result": "PASS"}, {"result": "UNKNOWN"}]) == "UNKNOWN"
    assert aggregate_results([{"result": "UNKNOWN"}, {"result": "FAIL"}]) == "FAIL"
    assert aggregate_results([{"result": "UNKNOWN"}, {"result": "UNKNOWN"}]) == "UNKNOWN"

def test_evaluate_snapshot_eligible():
    snapshot = {"cgpa": 8.0, "active_offers": 1}
    pol = [{"field": "active_offers", "operator": "<", "value": 2}]
    req = [{"field": "cgpa", "operator": ">=", "operand": {"value": 7.0}, "applicability": "REQUIRED"}]
    
    result, _ = evaluate_snapshot(snapshot, pol, req)
    assert result == "ELIGIBLE"

def test_evaluate_snapshot_not_eligible_due_to_policy():
    snapshot = {"cgpa": 8.0, "active_offers": 2}
    pol = [{"field": "active_offers", "operator": "<", "value": 2}]
    req = [{"field": "cgpa", "operator": ">=", "operand": {"value": 7.0}, "applicability": "REQUIRED"}]
    
    result, _ = evaluate_snapshot(snapshot, pol, req)
    assert result == "NOT_ELIGIBLE"

def test_evaluate_snapshot_not_eligible_due_to_req():
    snapshot = {"cgpa": 6.5, "active_offers": 1}
    pol = [{"field": "active_offers", "operator": "<", "value": 2}]
    req = [{"field": "cgpa", "operator": ">=", "operand": {"value": 7.0}, "applicability": "REQUIRED"}]
    
    result, _ = evaluate_snapshot(snapshot, pol, req)
    assert result == "NOT_ELIGIBLE"

def test_evaluate_snapshot_unknown():
    snapshot = {"active_offers": 1} # cgpa missing
    pol = [{"field": "active_offers", "operator": "<", "value": 2}]
    req = [{"field": "cgpa", "operator": ">=", "operand": {"value": 7.0}, "applicability": "REQUIRED"}]
    
    result, _ = evaluate_snapshot(snapshot, pol, req)
    assert result == "UNKNOWN"
