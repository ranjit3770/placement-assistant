from typing import Any


def evaluate_operator(operator: str, expected: Any, actual: Any) -> str:
    """
    Evaluates a deterministic operator.
    Returns "PASS", "FAIL", or "UNKNOWN"
    """
    if actual is None:
        return "UNKNOWN"

    try:
        if operator == "==":
            return "PASS" if actual == expected else "FAIL"
        elif operator == "!=":
            return "PASS" if actual != expected else "FAIL"
        elif operator == ">":
            return "PASS" if actual > expected else "FAIL"
        elif operator == ">=":
            return "PASS" if actual >= expected else "FAIL"
        elif operator == "<":
            return "PASS" if actual < expected else "FAIL"
        elif operator == "<=":
            return "PASS" if actual <= expected else "FAIL"
        elif operator == "IN":
            return "PASS" if actual in expected else "FAIL"
        elif operator == "NOT_IN":
            return "PASS" if actual not in expected else "FAIL"
        else:
            return "UNKNOWN"
    except Exception:
        # e.g. TypeError for unorderable types
        return "UNKNOWN"


def resolve_field_path(snapshot: dict[str, Any], path: str) -> Any:
    """
    Resolves a dot-notated path against the snapshot dictionary.
    Returns None if the path doesn't exist.
    """
    keys = path.split(".")
    current = snapshot
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def evaluate_rule(rule: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    """
    Evaluates a single rule (either a policy rule or a requirement criterion).
    """
    field_path = rule.get("field") or rule.get(
        "code"
    )  # Handle both policy and criterion naming conventions
    operator = rule.get("operator")

    if "value" in rule:
        expected = rule["value"]
    elif "operand" in rule and rule["operand"]:
        # Requirements store operand as a JSON dict e.g. {"value": X}
        expected = rule["operand"].get("value", rule["operand"])
    else:
        expected = None

    actual = resolve_field_path(snapshot, field_path)

    result = evaluate_operator(operator, expected, actual)

    return {"rule_description": field_path, "actual_value": actual, "result": result}


def aggregate_results(domain_results: list[dict[str, Any]]) -> str:
    """
    Aggregates a list of rule results into a domain result.
    FAIL > UNKNOWN > PASS
    """
    has_unknown = False
    for r in domain_results:
        if r["result"] == "FAIL":
            return "FAIL"
        elif r["result"] == "UNKNOWN":
            has_unknown = True

    if has_unknown:
        return "UNKNOWN"
    return "PASS"


def evaluate_snapshot(
    snapshot: dict[str, Any],
    policy_rules: list[dict[str, Any]],
    requirement_criteria: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """
    Evaluates the full snapshot against both domains.
    Returns (final_result, all_reasons)
    """
    reasons = []

    # 1. Opportunity Requirements Domain
    req_results = []
    for crit in requirement_criteria:
        # Skip if not REQUIRED. (Or handle OPTIONAL/NOT_APPLICABLE if needed later)
        if crit.get("applicability") not in ("REQUIRED", "OPTIONAL"):
            continue

        res = evaluate_rule(crit, snapshot)
        res["domain"] = "REQUIREMENT"
        req_results.append(res)
        reasons.append(res)

    req_domain_result = aggregate_results(req_results)

    # 2. Institutional Policy Domain
    pol_results = []
    for rule in policy_rules:
        # Check if mandatory/required. We assume all provided policy rules are mandatory for now,
        # unless rule specifies otherwise.
        res = evaluate_rule(rule, snapshot)
        res["domain"] = "POLICY"
        pol_results.append(res)
        reasons.append(res)

    pol_domain_result = aggregate_results(pol_results)

    # 3. Final Aggregation
    # PASS + PASS = ELIGIBLE
    # Any FAIL = NOT_ELIGIBLE
    # No FAIL + Any UNKNOWN = UNKNOWN

    if req_domain_result == "FAIL" or pol_domain_result == "FAIL":
        final_result = "NOT_ELIGIBLE"
    elif req_domain_result == "UNKNOWN" or pol_domain_result == "UNKNOWN":
        final_result = "UNKNOWN"
    else:
        final_result = "ELIGIBLE"

    return final_result, reasons
