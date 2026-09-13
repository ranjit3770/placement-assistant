from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.recruitment import DriveCreate, OpportunityCreate
from app.core.security import Principal
from app.infrastructure.models.recruitment import CompanyRole, Drive, Opportunity
from app.infrastructure.repositories.recruitment import (
    CompanyRepository,
    CompanyRoleRepository,
    DriveRepository,
    OpportunityRepository,
)


class OpportunityService:
    def __init__(self, session: AsyncSession, principal: Principal):
        self.session = session
        self.principal = principal
        self.company_repo = CompanyRepository(session, principal.institution_id)
        self.role_repo = CompanyRoleRepository(session, principal.institution_id)
        self.drive_repo = DriveRepository(session, principal.institution_id)
        self.opp_repo = OpportunityRepository(session, principal.institution_id)

    async def create_drive(self, company_id: UUID, data: DriveCreate) -> Drive:
        company = await self.company_repo.get_by_id(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        drive = Drive(
            institution_id=self.principal.institution_id,
            company_id=company.id,
            academic_year_id=data.academic_year_id,
            announced_at=data.announced_at,
            scheduled_at=data.scheduled_at,
            status=data.status,
            source_type="SYSTEM",
            source_reference=f"user:{self.principal.sub}",
        )
        self.session.add(drive)
        await self.session.flush()

        return drive

    async def create_opportunity(self, company_id: UUID, data: OpportunityCreate) -> Opportunity:
        company = await self.company_repo.get_by_id(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        role = await self.role_repo.get_by_id(data.role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        if role.company_id != company.id:
            raise HTTPException(
                status_code=409, detail="Role does not belong to the specified company"
            )

        drive = await self.drive_repo.get_by_id(data.drive_id)
        if not drive or drive.company_id != company.id:
            raise HTTPException(status_code=404, detail="Drive not found for this company")

        opp = Opportunity(
            institution_id=self.principal.institution_id,
            company_id=company.id,
            role_id=role.id,
            drive_id=drive.id,
            deadline=data.deadline,
            status=data.status,
            source_type="SYSTEM",
            source_reference=f"user:{self.principal.sub}",
        )
        self.session.add(opp)
        await self.session.flush()

        return opp

    async def close_opportunity(self, opportunity_id: UUID) -> Opportunity:
        opp = await self.opp_repo.get_by_id(opportunity_id)
        if not opp:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        if opp.status == "CLOSED":
            return opp

        opp.status = "CLOSED"
        await self.session.flush()

        return opp
