from uuid import UUID
from app.infrastructure.models.policy import Policy, PolicyVersion, PolicyActivation, PolicyRule
from app.infrastructure.repositories.base import MutableRepository, DefinitionRepository

class PolicyRepository(MutableRepository[Policy]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, Policy, institution_id)

class PolicyVersionRepository(DefinitionRepository[PolicyVersion]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, PolicyVersion, institution_id)

class PolicyActivationRepository(MutableRepository[PolicyActivation]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, PolicyActivation, institution_id)
