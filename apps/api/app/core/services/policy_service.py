import hashlib
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.schemas.policy import (
    DocumentCreate, PolicyCreate, PolicyVersionCreate, PolicyRuleCreate,
    PolicyTransitionRequest, PolicyActivationRequest
)
from app.core.security import Principal
from app.infrastructure.models.policy import (
    Document, Policy, PolicyVersion, PolicyRule, PolicyEvent, PolicyActivation
)
from app.infrastructure.repositories.policy import (
    DocumentRepository, PolicyRepository, PolicyVersionRepository,
    PolicyRuleRepository, PolicyEventRepository, PolicyActivationRepository
)


class PolicyService:
    def __init__(self, session: AsyncSession, principal: Principal):
        self.session = session
        self.principal = principal
        self.doc_repo = DocumentRepository(session, principal.institution_id)
        self.policy_repo = PolicyRepository(session, principal.institution_id)
        self.version_repo = PolicyVersionRepository(session, principal.institution_id)
        self.rule_repo = PolicyRuleRepository(session, principal.institution_id)
        self.event_repo = PolicyEventRepository(session, principal.institution_id)
        self.activation_repo = PolicyActivationRepository(session, principal.institution_id)

    async def create_document(self, data: DocumentCreate) -> Document:
        # Simulate document upload metadata calculation
        content_bytes = data.content.encode("utf-8")
        content_hash = hashlib.sha256(content_bytes).hexdigest()
        
        # In a real system, we'd upload content_bytes to S3. Here we simulate storage key.
        storage_key = f"policies/{self.principal.institution_id}/{uuid4()}.{data.media_type.split('/')[-1] if '/' in data.media_type else 'bin'}"
        
        return await self.doc_repo.create(
            filename=data.filename,
            media_type=data.media_type,
            content_hash=content_hash,
            storage_key=storage_key,
            source_version="v1",
            actor_id=self.principal.sub,
            source_type="SYSTEM",
            source_reference="simulated_upload",
        )

    async def create_policy(self, data: PolicyCreate) -> Policy:
        return await self.policy_repo.create(
            code=data.code,
            name=data.name,
            actor_id=self.principal.sub,
            source_type="SYSTEM",
            source_reference="api_creation",
        )

    async def create_policy_version(self, policy_id: UUID, data: PolicyVersionCreate) -> PolicyVersion:
        # Check if policy exists
        if not await self.policy_repo.exists(policy_id):
            raise HTTPException(404, {"code": "NOT_FOUND", "message": "Policy not found"})

        # Get latest version for this policy to determine next version number
        result = await self.session.execute(
            select(PolicyVersion.version)
            .where(
                PolicyVersion.institution_id == self.principal.institution_id,
                PolicyVersion.policy_id == policy_id
            )
            .order_by(PolicyVersion.version.desc())
            .limit(1)
        )
        latest_version = result.scalar_one_or_none()
        next_version = (latest_version or 0) + 1

        version = await self.version_repo.create_version(
            policy_id=policy_id,
            version=next_version,
            academic_year_id=data.academic_year_id,
            scope=data.scope,
            status="DRAFT",
            schema_version=data.schema_version,
            definition=data.definition,
            effective_at=datetime.now(timezone.utc),
            actor_id=self.principal.sub,
            source_type="SYSTEM",
            source_reference="api_creation",
        )

        await self._record_event(version.id, "CREATED", "DRAFT", "Initial draft created")
        return version

    async def add_policy_rule(self, version_id: UUID, data: PolicyRuleCreate) -> PolicyRule:
        version = await self.version_repo.get_by_id(version_id)
        if not version:
            raise HTTPException(404, {"code": "NOT_FOUND", "message": "Policy version not found"})

        # Enforce immutability
        if version.status in ("APPROVED", "ACTIVE", "ARCHIVED"):
            raise HTTPException(400, {"code": "INVALID_OPERATION", "message": f"Cannot modify rule in {version.status} state"})
        # REVIEW is frozen in M4 context unless specific controlled endpoints exist
        if version.status == "REVIEW":
            raise HTTPException(400, {"code": "INVALID_OPERATION", "message": "Cannot modify rule in REVIEW state"})

        return await self.rule_repo.create(
            policy_version_id=version_id,
            code=data.code,
            definition=data.definition,
            actor_id=self.principal.sub,
            source_type="SYSTEM",
            source_reference="api_creation",
        )

    async def transition_status(self, version_id: UUID, req: PolicyTransitionRequest, target_status: str) -> PolicyVersion:
        version = await self.version_repo.get_by_id(version_id)
        if not version:
            raise HTTPException(404, {"code": "NOT_FOUND"})

        valid_transitions = {
            "DRAFT": ["PROCESSING"],
            "PROCESSING": ["REVIEW"],
            "REVIEW": ["APPROVED"],
            "APPROVED": ["ACTIVE"],
            "ACTIVE": ["ARCHIVED"],
        }

        allowed_targets = valid_transitions.get(version.status, [])
        if target_status not in allowed_targets:
            raise HTTPException(400, {"code": "INVALID_OPERATION", "message": f"Cannot transition from {version.status} to {target_status}"})

        # Check authorization for APPROVE and ACTIVATE
        if target_status in ("APPROVED", "ACTIVE") and self.principal.role not in ("COORDINATOR", "ADMIN"):
            raise HTTPException(403, {"code": "FORBIDDEN", "message": f"Not authorized to transition to {target_status}"})

        from_status = version.status
        version = await self.version_repo.transition_lifecycle(version, target_status)
        await self._record_event(version_id, from_status, target_status, req.reason)
        return version

    async def approve_policy(self, version_id: UUID, req: PolicyTransitionRequest) -> PolicyVersion:
        return await self.transition_status(version_id, req, "APPROVED")

    async def activate_policy(self, version_id: UUID, req: PolicyActivationRequest) -> PolicyActivation:
        version = await self.transition_status(version_id, req, "ACTIVE")
        
        activation = await self.activation_repo.create(
            policy_version_id=version_id,
            academic_year_id=version.academic_year_id,
            scope=version.scope,
            starts_at=req.starts_at,
            ends_at=req.ends_at,
            actor_id=self.principal.sub,
            source_type="SYSTEM",
            source_reference="api_activation",
        )
        return activation

    async def archive_policy(self, version_id: UUID, req: PolicyTransitionRequest) -> PolicyVersion:
        version = await self.transition_status(version_id, req, "ARCHIVED")

        # Close the active activation record
        result = await self.session.execute(
            select(PolicyActivation)
            .where(
                PolicyActivation.institution_id == self.principal.institution_id,
                PolicyActivation.policy_version_id == version_id,
                PolicyActivation.ends_at.is_(None)
            )
        )
        activation = result.scalar_one_or_none()
        if activation:
            await self.activation_repo.update(activation, ends_at=datetime.now(timezone.utc))

        return version

    async def _record_event(self, version_id: UUID, from_status: str, to_status: str, reason: str):
        result = await self.session.execute(
            select(PolicyEvent.version)
            .where(
                PolicyEvent.institution_id == self.principal.institution_id,
                PolicyEvent.policy_version_id == version_id
            )
            .order_by(PolicyEvent.version.desc())
            .limit(1)
        )
        latest_event_version = result.scalar_one_or_none() or 0
        
        await self.event_repo.append(
            policy_version_id=version_id,
            version=latest_event_version + 1,
            effective_at=datetime.now(timezone.utc),
            status=to_status,
            reason=f"{from_status} -> {to_status}: {reason}",
            actor_id=self.principal.sub,
            source_type="SYSTEM",
            source_reference="lifecycle_transition",
        )
