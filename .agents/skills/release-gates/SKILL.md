---
name: release-gates
description: Validates R0-R4 release gates and production readiness against the SRS.
---

# Release Gates Skill

Do not declare a release complete because code exists.

Validate:
- requirements
- implementation
- automated tests
- security validation
- evidence
- operational validation
- acceptance report

R1 must cover deterministic decision behavior, policy definitions, offer selection, package rules, dream exceptions, UNKNOWN, audit, replay, API, and security.

R2 adds document ingestion/provenance, retrieval, version filtering, evidence, RAG evaluation, AI explanation validation, and AI outage behavior.

R3 adds tool authorization, agent evaluation, prompt-injection tests, conversation handling, tool traces, grounded responses, and eligibility consistency.

Production readiness includes backups, restore validation, health checks, monitoring, logging, security validation, rate limiting, retention, and incident procedures.
