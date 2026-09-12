from app.infrastructure.models.students import Student, AcademicRecord
from app.infrastructure.repositories.base import BaseRepository

class StudentRepository(BaseRepository[Student]):
    def __init__(self, session):
        super().__init__(session, Student)

class AcademicRecordRepository(BaseRepository[AcademicRecord]):
    def __init__(self, session):
        super().__init__(session, AcademicRecord)
