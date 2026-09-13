from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.recruitment import CompanyCreate, CompanyUpdate, RoleCreate
from app.core.security import Principal
from app.infrastructure.models.recruitment import Company, CompanyRevision, CompanyRole
from app.infrastructure.repositories.recruitment import CompanyRepository, CompanyRevisionRepository, CompanyRoleRepository


class CompanyService:
    def __init__(self, session: AsyncSession, principal: Principal):
        self.session = session
        self.principal = principal
        self.company_repo = CompanyRepository(session, principal.institution_id)
        self.company_revision_repo = CompanyRevisionRepository(session, principal.institution_id)
        self.role_repo = CompanyRoleRepository(session, principal.institution_id)

    async def create_company(self, data: CompanyCreate) -> CompanyRevision:
        company = Company(
            institution_id=self.principal.institution_id,
            code=data.code,
            source_type="SYSTEM",
            source_reference=f"user:{self.principal.sub}"
        )
        self.session.add(company)
        await self.session.flush()

        revision = CompanyRevision(
            institution_id=self.principal.institution_id,
            company_id=company.id,
            name=data.name,
            version=1,
            effective_at=datetime.now(timezone.utc),
            source_type="SYSTEM",
            source_reference=f"user:{self.principal.sub}"
        )
        self.session.add(revision)
        await self.session.flush()
        
        return revision

    async def update_company(self, company_id: UUID, data: CompanyUpdate) -> CompanyRevision:
        company = await self.company_repo.get_by_id(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # Get the latest revision version
        revisions = await self.session.execute(
            CompanyRevision.__table__.select()
            .where(CompanyRevision.institution_id == self.principal.institution_id)
            .where(CompanyRevision.company_id == company_id)
            .order_by(CompanyRevision.version.desc())
            .limit(1)
        )
        latest_rev = revisions.fetchone()
        next_version = latest_rev.version + 1 if latest_rev else 1

        revision = CompanyRevision(
            institution_id=self.principal.institution_id,
            company_id=company.id,
            name=data.name,
            version=next_version,
            effective_at=datetime.now(timezone.utc),
            source_type="SYSTEM",
            source_reference=f"user:{self.principal.sub}"
        )
        self.session.add(revision)
        await self.session.flush()

        return revision

    async def create_role(self, company_id: UUID, data: RoleCreate) -> CompanyRole:
        company = await self.company_repo.get_by_id(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        role = CompanyRole(
            institution_id=self.principal.institution_id,
            company_id=company.id,
            code=data.code,
            title=data.title,
            source_type="SYSTEM",
            source_reference=f"user:{self.principal.sub}"
        )
        self.session.add(role)
        await self.session.flush()

        return role
