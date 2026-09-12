from app.infrastructure.models.recruitment import Company, Drive, Opportunity, Offer
from app.infrastructure.repositories.base import BaseRepository

class CompanyRepository(BaseRepository[Company]):
    def __init__(self, session):
        super().__init__(session, Company)

class DriveRepository(BaseRepository[Drive]):
    def __init__(self, session):
        super().__init__(session, Drive)

class OpportunityRepository(BaseRepository[Opportunity]):
    def __init__(self, session):
        super().__init__(session, Opportunity)

class OfferRepository(BaseRepository[Offer]):
    def __init__(self, session):
        super().__init__(session, Offer)
