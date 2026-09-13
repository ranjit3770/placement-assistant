"""Tenant-scoped ingestion durability; no execution or vector indexing."""

import datetime
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.rag import RagChunk, RagIngestionRun, RagJob, RagPolicySource
from app.rag.contracts import EvidenceError


class IngestionRepository:
    def __init__(self, session: AsyncSession, institution_id: UUID) -> None:
        self.session = session
        self.institution_id = institution_id

    async def enqueue_run(
        self,
        binding: RagPolicySource,
        schema_version: int,
        parser_version: str,
        chunker_version: str,
        embedding_configuration: str,
        actor_id: UUID,
        request_id: UUID,
    ) -> tuple[RagIngestionRun, RagJob]:
        if binding.institution_id != self.institution_id:
            raise EvidenceError("BINDING_NOT_FOUND")

        # Check existing first to avoid burning IDs if possible
        query = select(RagIngestionRun).where(
            RagIngestionRun.institution_id == self.institution_id,
            RagIngestionRun.binding_id == binding.id,
            RagIngestionRun.schema_version == schema_version,
            RagIngestionRun.parser_version == parser_version,
            RagIngestionRun.chunker_version == chunker_version,
            RagIngestionRun.embedding_configuration == embedding_configuration,
        )
        existing_run = await self.session.scalar(query)
        if existing_run is not None:
            job = await self.session.scalar(
                select(RagJob).where(
                    RagJob.institution_id == self.institution_id,
                    RagJob.run_id == existing_run.id,
                )
            )
            if job is None:
                raise EvidenceError("JOB_NOT_FOUND")
            return existing_run, job

        run = RagIngestionRun(
            institution_id=self.institution_id,
            binding_id=binding.id,
            schema_version=schema_version,
            parser_version=parser_version,
            chunker_version=chunker_version,
            embedding_configuration=embedding_configuration,
            status="RUNNING",
            actor_id=actor_id,
            request_id=request_id,
            source_type="SYSTEM",
            source_reference=f"binding:{binding.id}",
            verification="VERIFIED",
        )
        self.session.add(run)

        try:
            await self.session.flush()
        except IntegrityError as ex:
            if "uq_rag_ingestion_run_idempotency" in str(ex):
                raise EvidenceError("IDEMPOTENCY_CONFLICT") from ex
            raise

        job = RagJob(
            institution_id=self.institution_id,
            run_id=run.id,
            status="QUEUED",
            attempt=0,
            stage="QUEUED",
            actor_id=actor_id,
            request_id=request_id,
            source_type="SYSTEM",
            source_reference=f"run:{run.id}",
            verification="VERIFIED",
        )
        self.session.add(job)
        await self.session.flush()
        return run, job

    async def acquire_job(
        self, lease_seconds: int = 900, max_attempts: int = 3
    ) -> tuple[RagIngestionRun, RagJob] | None:
        """Finds and acquires an available QUEUED or expired RUNNING job.
        
        Uses FOR UPDATE SKIP LOCKED to ensure atomic acquisition by a single worker.
        """
        now = datetime.datetime.now(datetime.UTC)
        
        # We need a subquery to find one eligible job, then lock it and update it.
        # But SQLAlchemy 2.0 with PostgreSQL makes this easy with a returning update.
        # However, to return BOTH the run and job, it's safer to SELECT FOR UPDATE first.
        
        query = (
            select(RagJob)
            .where(
                RagJob.institution_id == self.institution_id,
                RagJob.attempt < max_attempts,
                (RagJob.status == "QUEUED") | 
                ((RagJob.status == "RUNNING") & (RagJob.leased_until <= now))
            )
            .order_by(RagJob.recorded_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        
        job = await self.session.scalar(query)
        if job is None:
            return None
            
        job.status = "RUNNING"
        job.attempt += 1
        job.leased_until = now + datetime.timedelta(seconds=lease_seconds)
        
        await self.session.flush()
        
        run = await self.session.scalar(
            select(RagIngestionRun).where(
                RagIngestionRun.institution_id == self.institution_id,
                RagIngestionRun.id == job.run_id,
            )
        )
        if run is None:
            raise EvidenceError("RUN_NOT_FOUND")
            
        return run, job

    async def update_job(
        self, job_id: UUID, status: str, stage: str, error_code: str | None = None
    ) -> RagJob:
        job = await self.session.scalar(
            select(RagJob).where(
                RagJob.institution_id == self.institution_id,
                RagJob.id == job_id,
            )
        )
        if job is None:
            raise EvidenceError("JOB_NOT_FOUND")
            
        job.status = status
        job.stage = stage
        job.error_code = error_code
        
        if status in {"FAILED", "COMPLETED", "READY", "REVIEW_REQUIRED", "CANCELLED"}:
            job.leased_until = None
            
        await self.session.flush()
        
        # If job fails and exhausts attempts (or is explicitly cancelled), fail the run.
        if status in {"FAILED", "CANCELLED"}:
            run = await self.session.scalar(
                select(RagIngestionRun).where(
                    RagIngestionRun.institution_id == self.institution_id,
                    RagIngestionRun.id == job.run_id,
                )
            )
            if run is not None:
                run.status = "FAILED"
                
        return job

    async def save_chunks(
        self,
        run_id: UUID,
        chunks: Sequence[dict],
        actor_id: UUID,
        request_id: UUID,
    ) -> list[RagChunk]:
        """Saves a batch of chunks.

        chunks is expected to be a sequence of dicts with:
        ordinal, content, page, section, start_offset, end_offset,
        source_hash, artifact_hash, chunk_hash
        """
        result_chunks = []
        for chunk_data in chunks:
            chunk = RagChunk(
                institution_id=self.institution_id,
                run_id=run_id,
                ordinal=chunk_data["ordinal"],
                content=chunk_data["content"],
                page=chunk_data.get("page"),
                section=chunk_data.get("section"),
                start_offset=chunk_data.get("start_offset"),
                end_offset=chunk_data.get("end_offset"),
                source_hash=chunk_data["source_hash"],
                artifact_hash=chunk_data["artifact_hash"],
                chunk_hash=chunk_data["chunk_hash"],
                actor_id=actor_id,
                request_id=request_id,
                source_type="SYSTEM",
                source_reference=f"run:{run_id}",
                verification="VERIFIED",
            )
            self.session.add(chunk)
            result_chunks.append(chunk)
            
        await self.session.flush()
        return result_chunks
