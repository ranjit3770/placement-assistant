from uuid import UUID
from app.infrastructure.models.recruitment import Company, Drive, Opportunity, Offer, OfferEvent, DreamEvent, CompanyRevision, CompanyRole, Compensation
from app.infrastructure.repositories.base import MutableRepository, EventRepository

class CompanyRepository(MutableRepository[Company]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, Company, institution_id)

class DriveRepository(MutableRepository[Drive]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, Drive, institution_id)

class OpportunityRepository(MutableRepository[Opportunity]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, Opportunity, institution_id)

class OfferRepository(MutableRepository[Offer]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, Offer, institution_id)

class OfferEventRepository(EventRepository[OfferEvent]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, OfferEvent, institution_id)

class DreamEventRepository(EventRepository[DreamEvent]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, DreamEvent, institution_id)

class CompanyRevisionRepository(MutableRepository[CompanyRevision]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, CompanyRevision, institution_id)

class CompanyRoleRepository(MutableRepository[CompanyRole]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, CompanyRole, institution_id)

class CompensationRepository(MutableRepository[Compensation]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, Compensation, institution_id)
