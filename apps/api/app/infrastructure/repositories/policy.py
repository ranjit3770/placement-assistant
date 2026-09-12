from app.infrastructure.models.policy import Policy, PolicyVersion, PolicyRule, PolicyActivation
from app.infrastructure.repositories.base import BaseRepository

class PolicyRepository(BaseRepository[Policy]):
    def __init__(self, session):
        super().__init__(session, Policy)

class PolicyVersionRepository(BaseRepository[PolicyVersion]):
    def __init__(self, session):
        super().__init__(session, PolicyVersion)

class PolicyActivationRepository(BaseRepository[PolicyActivation]):
    def __init__(self, session):
        super().__init__(session, PolicyActivation)
