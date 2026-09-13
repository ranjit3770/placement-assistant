from uuid import UUID
from app.infrastructure.models.policy import Policy, PolicyVersion, PolicyActivation, PolicyRule, Requirement, RequirementVersion, Criterion, RequirementMember
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

class RequirementRepository(MutableRepository[Requirement]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, Requirement, institution_id)

class RequirementVersionRepository(DefinitionRepository[RequirementVersion]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, RequirementVersion, institution_id)

class CriterionRepository(MutableRepository[Criterion]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, Criterion, institution_id)

class RequirementMemberRepository(MutableRepository[RequirementMember]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, RequirementMember, institution_id)
