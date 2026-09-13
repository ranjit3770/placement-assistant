---
name: policy-lifecycle
description: Implements institutional policy documents, versioning, approval lifecycle, provenance, and policy-to-rule conversion.
---

# Policy Lifecycle Skill

Policy documents are source material, not executable rules.

Lifecycle:
DRAFT -> PROCESSING -> REVIEW -> APPROVED -> ACTIVE -> ARCHIVED

Only approved policies may become active. Active policy definitions are immutable.

Preserve original file, hash, filename, uploader, timestamp, source, version, document type, and processing status.

Every executable rule should retain a source locator where applicable.

LLM extraction may create candidate rules only. Human review/approval is required before a rule becomes executable.
