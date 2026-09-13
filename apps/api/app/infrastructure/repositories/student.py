from uuid import UUID
from app.infrastructure.models.students import Student, AcademicRecord, BacklogEvent
from app.infrastructure.repositories.base import MutableRepository, EventRepository


class StudentRepository(MutableRepository[Student]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, Student, institution_id)


class AcademicRecordRepository(MutableRepository[AcademicRecord]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, AcademicRecord, institution_id)


class BacklogEventRepository(EventRepository[BacklogEvent]):
    def __init__(self, session, institution_id: UUID):
        super().__init__(session, BacklogEvent, institution_id)
