# AI-Powered Student Placement Intelligence Platform

The AI-Powered Student Placement Intelligence Platform is an institutional gateway that orchestrates placement eligibility, policy verification, and intelligent student interactions for University campus placements.

## Architecture & Authority Boundaries

The v1.0 architecture is explicitly layered to enforce deterministic authority over AI-generated content.

```text
Student
   │
   ▼
Authentication / JWT Principal
   │
   ▼
M9 Student Copilot
   │
   ▼
M8 Conversational Agent
   │
   ├───────────────┐
   ▼               ▼
M5 Eligibility    M6 Policy RAG
Engine             & Evidence
   │               │
   ▼               ▼
Authoritative     Verified
Decision          Evidence
   └───────┬───────┘
           ▼
      AgentResponse
           │
           ▼
       Student UI
```

### Authority Enforcement

| Component               | Authority                          |
| ----------------------- | ---------------------------------- |
| Student/domain services | Student facts                      |
| M5                      | Eligibility decisions              |
| M6                      | Verified policy evidence           |
| M8                      | AI orchestration                   |
| M9                      | Student-facing copilot             |
| AI/LLM                  | Explanation and orchestration only |

> **Note:** Interview Preparation, Assessments, and Skill Gap functionality are explicitly outside the v1.0 scope.

## Getting Started

Run `make configure` to generate `.env` and development secrets.
Run `docker compose up -d` to boot the application stack.
