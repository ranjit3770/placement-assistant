from uuid import UUID
from app.infrastructure.models.policy import (
    Policy, PolicyVersion, PolicyActivation, PolicyRule, PolicyEvent, Document,
    Requirement, RequirementVersion, Criterion, RequirementMember,
    SourceLocator, RuleSource
)
from app.infrastructure.repositories.base import MutableRepository, DefinitionRepository, EventRepository

class PolicyRepository(MutableRepository[Policy]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, Policy, institution_id)

class PolicyVersionRepository(DefinitionRepository[PolicyVersion]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, PolicyVersion, institution_id)

class PolicyActivationRepository(MutableRepository[PolicyActivation]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, PolicyActivation, institution_id)

class PolicyEventRepository(EventRepository[PolicyEvent]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, PolicyEvent, institution_id)

class PolicyRuleRepository(MutableRepository[PolicyRule]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, PolicyRule, institution_id)

class DocumentRepository(MutableRepository[Document]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, Document, institution_id)

class SourceLocatorRepository(MutableRepository[SourceLocator]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, SourceLocator, institution_id)

class RuleSourceRepository(MutableRepository[RuleSource]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, RuleSource, institution_id)

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
