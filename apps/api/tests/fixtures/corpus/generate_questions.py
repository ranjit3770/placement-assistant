import json
import os
from pathlib import Path

def main():
    questions = []
    
    # 40 answerable
    for i in range(1, 41):
        questions.append({
            "id": f"Q{i:03d}",
            "type": "answerable",
            "query": f"What is the policy for scenario {i}?",
            "expected_tenant": "tenant-a" if i <= 20 else "tenant-b"
        })
        
    # 20 unanswerable/security
    # 4 unanswerable
    for i in range(41, 45):
        questions.append({"id": f"Q{i:03d}", "type": "unanswerable", "query": f"Unknown topic {i}"})
    # 4 cross-tenant
    for i in range(45, 49):
        questions.append({"id": f"Q{i:03d}", "type": "cross-tenant", "query": f"Tenant B policy for Tenant A {i}"})
    # 4 unauthorized
    for i in range(49, 53):
        questions.append({"id": f"Q{i:03d}", "type": "unauthorized", "query": f"Admin endpoint bypass {i}"})
    # 4 revoked/stale
    for i in range(53, 57):
        questions.append({"id": f"Q{i:03d}", "type": "revoked/stale", "query": f"Old 2024 policy {i}"})
    # 4 ambiguous
    for i in range(57, 61):
        questions.append({"id": f"Q{i:03d}", "type": "ambiguous", "query": f"Overlapping policy {i}"})

    out_path = Path(__file__).parent / "question-set.json"
    with open(out_path, "w") as f:
        json.dump({"version": "1.0", "questions": questions}, f, indent=2)

if __name__ == "__main__":
    main()
